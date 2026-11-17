"""객체 인식 설정. 위험 유형 이름은 docs/api.md 2장과 같아야 한다."""

# 학습 모델(best.pt)이 인식할 클래스. 학습 데이터의 클래스 번호도 이 순서를 따른다.
# 규칙: YOLO 클래스 이름 = 서버 type 이름 (docs/api.md)
HAZARD_CLASSES = ["pothole", "crack", "puddle"]

# 지금 best.pt처럼 이전에 다른 이름으로 학습된 모델을 쓸 때만 쓰는 이름 변환표
LEGACY_NAMES = {
    "potholes": "pothole",
    "pothole": "pothole",
    "damage": "crack",
    "cracks": "crack",
    "water": "puddle",
    "puddles": "puddle",
}

HAZARD_MODEL = "best.pt"        # 직접 학습한 도로 위험 모델
HAZARD_CONF = 0.40              # 이 값보다 낮은 박스는 버린다

# 인파(crowd): 사전학습 모델의 person 수로 판정한다 (학습 클래스 아님)
PERSON_MODEL = "yolov8n.pt"
PERSON_CLASS_ID = 0             # COCO의 person
PERSON_CONF = 0.40
CROWD_MIN_PEOPLE = 3            # 관심 영역 안에 이 수 이상이면 crowd
ROI_TOP_RATIO = 0.40            # 화면 위쪽 40%는 무시 (하늘·건물). 아래쪽 60%만 본다

# 같은 위험이 연속 몇 프레임 보여야 이벤트로 인정할지
MIN_FRAMES = 3

IMGSZ = 640                     # 노트북 확인용. 폰 탑재 시 320
