"""
웹캠(또는 영상 파일)으로 도로 위험 + 인파 인식 확인

- 도로 위험: 직접 학습한 모델(best.pt)의 pothole / crack / puddle
- 인파: 사전학습 모델(yolov8n.pt)에서 person만 세어 crowd 판정
- 그 외 클래스(자동차, 컵 등)는 표시하지 않는다
- 화면에 표시하는 이름은 서버 type 이름(docs/api.md)과 같다

실행:  python webcam_test.py              (웹캠 0번)
       python webcam_test.py road.mp4     (영상 파일)
종료:  q
"""
import sys
import time

import cv2
from ultralytics import YOLO

import config as C

COLORS = {"pothole": (0, 0, 255), "crack": (0, 165, 255), "puddle": (255, 128, 0), "person": (180, 180, 180)}


def type_name(raw: str) -> str:
    """모델의 클래스 이름을 서버 type 이름으로 바꾼다."""
    name = raw.strip().lower()
    return C.LEGACY_NAMES.get(name, name)


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else 0
    hazard_model = YOLO(C.HAZARD_MODEL)
    person_model = YOLO(C.PERSON_MODEL)

    unknown = [n for n in hazard_model.names.values() if type_name(n) not in C.HAZARD_CLASSES]
    if unknown:
        print(f"[주의] best.pt에 type 목록에 없는 클래스가 있습니다: {unknown} (config.py 확인)")

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"영상을 열 수 없습니다: {source}")

    streak = {}  # type -> 연속으로 보인 프레임 수

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        roi_top = int(h * C.ROI_TOP_RATIO)
        t0 = time.time()

        # 1) 도로 위험
        seen = set()
        r = hazard_model(frame, conf=C.HAZARD_CONF, imgsz=C.IMGSZ, verbose=False)[0]
        for box, cls, conf in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist()):
            t = type_name(hazard_model.names[int(cls)])
            if t not in C.HAZARD_CLASSES:
                continue
            x1, y1, x2, y2 = map(int, box)
            if (y1 + y2) / 2 < roi_top:          # 관심 영역 밖 (위쪽)
                continue
            seen.add(t)
            cv2.rectangle(frame, (x1, y1), (x2, y2), COLORS[t], 2)
            cv2.putText(frame, f"{t} {conf:.2f}", (x1, max(y1 - 6, 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS[t], 2)

        # 2) 인파: person만
        people = 0
        r = person_model(frame, classes=[C.PERSON_CLASS_ID], conf=C.PERSON_CONF, imgsz=C.IMGSZ, verbose=False)[0]
        for box in r.boxes.xyxy.tolist():
            x1, y1, x2, y2 = map(int, box)
            if y2 < roi_top:                      # 발끝이 관심 영역 밖이면 제외
                continue
            people += 1
            cv2.rectangle(frame, (x1, y1), (x2, y2), COLORS["person"], 1)
        if people >= C.CROWD_MIN_PEOPLE:
            seen.add("crowd")

        # 3) 연속 프레임 확인 → 이벤트
        for t in list(streak):
            if t not in seen:
                streak[t] = 0
        for t in seen:
            streak[t] = streak.get(t, 0) + 1
            if streak[t] == C.MIN_FRAMES:
                print(f"{time.strftime('%H:%M:%S')} 이벤트: {t}" + (f" (사람 {people}명)" if t == "crowd" else ""))

        # 화면 정보
        fps = 1.0 / max(time.time() - t0, 1e-6)
        cv2.line(frame, (0, roi_top), (w, roi_top), (0, 255, 0), 1)
        cv2.putText(frame, f"{fps:.1f} FPS  people:{people}", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        if streak.get("crowd", 0) >= C.MIN_FRAMES:
            cv2.putText(frame, "CROWD", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

        cv2.imshow("Road hazard + crowd", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
