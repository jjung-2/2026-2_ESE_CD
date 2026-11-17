"""
여러 데이터셋을 하나의 YOLO 데이터셋으로 합친다.

클래스 번호 (docs/api.md 기준, detect/config.py의 HAZARD_CLASSES와 같은 순서)
    0 pothole   1 crack   2 puddle

지원하는 입력
  - rdd  : RDD2022 나라별 압축을 푼 폴더 (Pascal VOC XML 라벨)
           D40 → pothole, D20 → crack (옵션으로 D00·D10도 crack)
  - yolo : YOLO 형식 폴더 (이미지 + 같은 이름의 .txt). data.yaml이 있으면 클래스 이름으로 매핑
           Roboflow RDD2022처럼 이름이 D00·D10·D20·D40이면 위 RDD 규칙대로 매핑
           폴리곤(세그멘테이션) 라벨이면 박스로 바꾼다

사용 예 (Colab):
  python prepare_dataset.py --out /content/data \
     --yolo /content/raw/pothole:pothole \
     --yolo /content/raw/puddle:puddle \
     --yolo /content/raw/rdd_rf:auto \
     --max-per-source 3000 --val 0.15
"""
import argparse
import random
import re
import shutil
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

CLASSES = ["pothole", "crack", "puddle"]
CID = {n: i for i, n in enumerate(CLASSES)}
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# 이름으로 클래스를 정할 때 쓰는 규칙 (소문자 비교)
NAME_RULES = [
    (re.compile(r"pot\s*-?hole"), "pothole"),
    (re.compile(r"crack|alligator|damage"), "crack"),
    (re.compile(r"puddle|water|ponding|wet"), "puddle"),
]


# RDD2022 손상 코드 (Roboflow 등 YOLO 형식 RDD에서 클래스 이름이 코드일 때)
RDD_CODES = {"d40": "pothole", "d20": "crack"}
THIN_CRACK_CODES = {"d00": "crack", "d10": "crack"}  # --rdd-thin-cracks 일 때만 사용
USE_THIN_CRACKS = False


def name_to_class(name: str):
    n = name.strip().lower()
    if n in CID:
        return n
    if n in RDD_CODES:
        return RDD_CODES[n]
    if USE_THIN_CRACKS and n in THIN_CRACK_CODES:
        return THIN_CRACK_CODES[n]
    if re.fullmatch(r"d\d\d", n):  # 그 밖의 RDD 코드(D43 횡단보도 흐림, D44 차선 흐림 등)는 제외
        return None
    for pat, cls in NAME_RULES:
        if pat.search(n):
            return cls
    return None


def read_data_yaml_names(root: Path):
    """data.yaml의 names를 {번호: 이름}으로 읽는다. 가장 얕은 위치의 data.yaml을 쓴다."""
    for y in sorted(root.rglob("data.yaml"), key=lambda p: len(p.parts)):
        text = y.read_text(encoding="utf-8", errors="ignore")
        try:
            import yaml  # Colab에는 기본 설치돼 있음
            names = (yaml.safe_load(text) or {}).get("names")
            if isinstance(names, list):
                return {i: str(n) for i, n in enumerate(names)}
            if isinstance(names, dict):
                return {int(k): str(v) for k, v in names.items()}
        except ImportError:
            pass
        # PyYAML이 없을 때: [a, b] / "- a" 목록 / "0: a" 사전 세 가지 형식
        m = re.search(r"^names\s*:\s*\[(.*?)\]", text, re.S | re.M)
        if m:
            items = [s.strip().strip("'\"") for s in m.group(1).split(",") if s.strip()]
            return dict(enumerate(items))
        m = re.search(r"^names\s*:[ \t]*\n((?:[ \t]*(?:-|\d+\s*:).*(?:\n|$))+)", text, re.M)
        if m:
            out = {}
            for line in m.group(1).splitlines():
                line = line.strip()
                if line.startswith("-"):
                    out[len(out)] = line[1:].strip().strip("'\"")
                elif ":" in line:
                    k, v = line.split(":", 1)
                    out[int(k.strip())] = v.strip().strip("'\"")
            if out:
                return out
    return None


def yolo_line_to_box(parts):
    """YOLO 박스(5개 값) 또는 폴리곤(홀수 개, 7개 이상)을 (cx, cy, w, h)로."""
    vals = [float(v) for v in parts[1:]]
    if len(vals) == 4:
        return vals
    if len(vals) >= 6 and len(vals) % 2 == 0:
        xs, ys = vals[0::2], vals[1::2]
        x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
        return [(x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1]
    return None


def collect_yolo(root: Path, fixed_class: str):
    """(이미지 경로, [(cls, cx, cy, w, h)]) 목록. fixed_class='auto'면 data.yaml 이름으로 매핑."""
    names = read_data_yaml_names(root) if fixed_class == "auto" else None
    if fixed_class == "auto":
        if not names:
            raise SystemExit(f"[오류] {root}: data.yaml의 names를 찾지 못했습니다. ':클래스이름'으로 지정하세요.")
        mapping = {i: name_to_class(n) for i, n in names.items()}
        print(f"  {root.name} 클래스 매핑: " + ", ".join(f"{names[i]}→{mapping[i]}" for i in names))
    items = []
    for img in root.rglob("*"):
        if img.suffix.lower() not in IMG_EXT:
            continue
        cand = [img.with_suffix(".txt")]
        if "images" in img.parts:  # .../images/x.jpg → .../labels/x.txt
            p = list(img.parts)
            p[len(p) - 1 - p[::-1].index("images")] = "labels"
            cand.append(Path(*p).with_suffix(".txt"))
        lbl = next((c for c in cand if c.exists()), None)
        boxes = []
        if lbl:
            for line in lbl.read_text(errors="ignore").splitlines():
                parts = line.split()
                if len(parts) < 5:
                    continue
                cls = fixed_class if fixed_class != "auto" else mapping.get(int(float(parts[0])))
                if cls not in CID:
                    continue
                b = yolo_line_to_box(parts)
                if b and b[2] > 0 and b[3] > 0:
                    boxes.append((CID[cls], *b))
        items.append((img, boxes))
    return items


def collect_rdd(root: Path, crack_codes):
    """RDD2022 폴더: annotations/xmls/*.xml + images/*.jpg"""
    code_map = {"D40": "pothole"}
    for c in crack_codes:
        code_map[c] = "crack"
    images = {p.stem: p for p in root.rglob("*") if p.suffix.lower() in IMG_EXT}
    items, skipped = [], Counter()
    for xml in root.rglob("*.xml"):
        img = images.get(xml.stem)
        if img is None:
            continue
        r = ET.parse(xml).getroot()
        size = r.find("size")
        try:
            W, H = float(size.find("width").text), float(size.find("height").text)
        except Exception:
            W = H = 0
        if not W or not H:
            from PIL import Image
            with Image.open(img) as im:
                W, H = im.size
        boxes = []
        for obj in r.findall("object"):
            code = (obj.findtext("name") or "").strip()
            cls = code_map.get(code)
            if cls is None:
                skipped[code] += 1
                continue
            bb = obj.find("bndbox")
            x1, y1, x2, y2 = (float(bb.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax"))
            x1, x2 = max(0, min(x1, x2)), min(W, max(x1, x2))
            y1, y2 = max(0, min(y1, y2)), min(H, max(y1, y2))
            if x2 - x1 < 2 or y2 - y1 < 2:
                continue
            boxes.append((CID[cls], (x1 + x2) / 2 / W, (y1 + y2) / 2 / H, (x2 - x1) / W, (y2 - y1) / H))
        items.append((img, boxes))
    if skipped:
        print(f"  {root.name} 제외한 라벨: " + ", ".join(f"{k}×{v}" for k, v in skipped.most_common()))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--yolo", action="append", default=[], help="경로:클래스이름 또는 경로:auto")
    ap.add_argument("--rdd", action="append", default=[], help="RDD2022 나라 폴더")
    ap.add_argument("--rdd-thin-cracks", action="store_true", help="D00·D10(가는 균열)도 crack에 포함")
    ap.add_argument("--max-per-source", type=int, default=3000, help="출처별 최대 이미지 수 (한쪽 쏠림 방지)")
    ap.add_argument("--background", type=float, default=0.10, help="라벨 없는 이미지 비율 상한 (오탐 줄이기)")
    ap.add_argument("--val", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    global USE_THIN_CRACKS
    USE_THIN_CRACKS = a.rdd_thin_cracks

    rng = random.Random(a.seed)
    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    for s in ("train", "val"):
        (out / "images" / s).mkdir(parents=True)
        (out / "labels" / s).mkdir(parents=True)

    sources = []
    for spec in a.yolo:
        path, _, cls = spec.rpartition(":")
        if not path:  # 윈도 경로 등 ':'가 없을 때
            path, cls = spec, "auto"
        if cls != "auto" and cls not in CID:
            raise SystemExit(f"[오류] 클래스 이름은 {CLASSES} 또는 auto: {spec}")
        sources.append((Path(path).name, collect_yolo(Path(path), cls)))
    crack_codes = ["D20"] + (["D00", "D10"] if a.rdd_thin_cracks else [])
    for path in a.rdd:
        sources.append(("rdd_" + Path(path).name, collect_rdd(Path(path), crack_codes)))

    stats = defaultdict(Counter)
    for src, items in sources:
        pos = [it for it in items if it[1]]
        neg = [it for it in items if not it[1]]
        rng.shuffle(pos)
        rng.shuffle(neg)
        pos = pos[: a.max_per_source]
        n_bg = min(len(neg), int(len(pos) * a.background / max(1e-6, 1 - a.background)))
        chosen = pos + neg[:n_bg]
        rng.shuffle(chosen)
        n_val = max(1, int(len(chosen) * a.val)) if len(chosen) > 1 else 0
        for k, (img, boxes) in enumerate(chosen):
            split = "val" if k < n_val else "train"
            stem = f"{src}__{img.stem}"
            shutil.copy2(img, out / "images" / split / (stem + img.suffix.lower()))
            (out / "labels" / split / (stem + ".txt")).write_text(
                "".join(f"{c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n" for c, x, y, w, h in boxes))
            stats[src][f"{split}_images"] += 1
            for c, *_ in boxes:
                stats[src][f"{split}_{CLASSES[c]}"] += 1
        print(f"  {src}: 라벨 있는 이미지 {len(pos)}장, 배경 이미지 {n_bg}장 사용 (전체 {len(items)}장)")

    (out / "data.yaml").write_text(
        f"path: {out.resolve()}\ntrain: images/train\nval: images/val\nnames:\n"
        + "".join(f"  {i}: {n}\n" for i, n in enumerate(CLASSES)))

    print("\n출처별 개수")
    cols = ["train_images", "val_images"] + [f"train_{c}" for c in CLASSES]
    print("source".ljust(26) + "".join(c.rjust(15) for c in cols))
    total = Counter()
    for src, c in stats.items():
        total.update(c)
        print(src[:25].ljust(26) + "".join(str(c[k]).rjust(15) for k in cols))
    print("TOTAL".ljust(26) + "".join(str(total[k]).rjust(15) for k in cols))
    missing = [c for c in CLASSES if total[f"train_{c}"] == 0]
    if missing:
        print(f"\n[주의] 학습 데이터에 없는 클래스: {missing}")
    print(f"\n완료: {out / 'data.yaml'}")


if __name__ == "__main__":
    main()
