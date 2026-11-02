from ultralytics import YOLO
import cv2

# 기존 YOLO 모델: 일반 객체 인식
general_model = YOLO("yolov8n.pt")

# 학습한 YOLO 모델: 포트홀 인식
pothole_model = YOLO("best.pt")

# 웹캠 실행
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("웹캠을 열 수 없습니다.")

while True:
    ret, frame = cap.read()

    if not ret:
        break

    # 1. 일반 객체 인식
    general_results = general_model(
        frame,
        conf=0.35,
        verbose=False
    )

    # 2. 포트홀 인식
    pothole_results = pothole_model(
        frame,
        conf=0.25,
        verbose=False
    )

    # 3. 일반 객체 바운딩 박스 표시
    annotated_frame = general_results[0].plot()

    # 4. 포트홀 바운딩 박스 표시
    annotated_frame = pothole_results[0].plot(
        img=annotated_frame
    )

    # 화면 출력
    cv2.imshow("YOLO + Pothole Detection", annotated_frame)

    # Q 키를 누르면 종료
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()