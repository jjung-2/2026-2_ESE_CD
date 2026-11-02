# 🛣️ Road Hazard Detection System

카메라와 센서를 활용하여 도로 위 포트홀 및 위험 요소를 탐지하고, 위치 정보를 기반으로 위험 지역을 관리하는 프로젝트입니다.

현재 YOLO 기반 일반 객체 탐지와 자체 학습한 포트홀 탐지 모델을 구현했으며, FastAPI 기반 위험 요소 수신 및 검증 서버를 개발하고 있습니다.

---

## ✨ 주요 기능

### 1. YOLO 기반 객체 탐지

- YOLOv8n 사전 학습 모델을 이용한 일반 객체 탐지
- 자체 학습한 YOLO 모델(`best.pt`)을 이용한 포트홀 탐지
- 두 모델의 탐지 결과를 하나의 화면에 표시
- Bounding Box 및 클래스별 탐지 결과 표시
- 웹캠을 이용한 실시간 탐지

### 2. 포트홀 탐지 모델 학습

- 포트홀 이미지 데이터셋을 이용한 모델 학습
- 학습 데이터와 검증 데이터 80:20 분리
- Google Colab GPU 환경에서 학습
- YOLOv8n 기반 모델 사용
- 학습된 최적 가중치 `best.pt` 저장

### 3. FastAPI 기반 도로 위험 요소 관리 서버

- 도로 위험 요소 데이터 수신
- 카메라 및 IMU 센서 데이터 구분
- GPS 좌표 및 진행 방향을 이용한 위험 위치 계산
- 동일 위치의 중복 제보 통합
- 다중 센서 기반 위험 요소 신뢰도 산출
- 위험 지역 조회 API 제공

---

## 🛠️ 기술 스택

| 구분 | 기술 |
|---|---|
| Language | Python |
| Object Detection | YOLOv8 |
| Computer Vision | OpenCV |
| Deep Learning | Ultralytics |
| Model Training | Google Colab |
| Backend | FastAPI |
| Server | Uvicorn |
| Data Validation | Pydantic |

---

## 📁 프로젝트 구조

```text
2026-2_ESE_CD/
│
├── detect/
│   ├── best.pt
│   ├── webcam_test.py
│   └── yolov8n.pt
│
├── server/
│   ├── main.py
│   └── requirements.txt
│
├── docs/
│
├── map-alert/
│
├── .gitignore
└── README.md
```

---

## 🚀 실행 방법

### 1. 개발 환경 구성

Python 3.10 이상 환경을 권장합니다.

```bash
# 가상환경 생성
py -m venv venv

# Windows 가상환경 활성화
.\venv\Scripts\Activate.ps1

# 패키지 설치
python -m pip install ultralytics opencv-python
```

### 2. 객체 및 포트홀 탐지 실행

`detect` 폴더로 이동합니다.

```bash
cd detect
```

웹캠 탐지 프로그램을 실행합니다.

```bash
python webcam_test.py
```

실행 시 다음 두 모델이 동시에 동작합니다.

- `yolov8n.pt`: 일반 객체 탐지
- `best.pt`: 포트홀 탐지

웹캠 화면에 두 모델의 탐지 결과가 Bounding Box 형태로 표시됩니다.

프로그램 종료는 `Q` 키를 사용합니다.

※ `yolov8n.pt`가 없는 경우 Ultralytics가 사전 학습 가중치를 다운로드할 수 있습니다.

### 3. FastAPI 서버 실행

`server` 폴더로 이동합니다.

```bash
cd server
```

필요한 패키지를 설치합니다.

```bash
python -m pip install -r requirements.txt
```

서버를 실행합니다.

```bash
uvicorn main:app --reload
```

서버 실행 후 아래 주소에서 API 문서를 확인할 수 있습니다.

```text
http://127.0.0.1:8000/docs
```

---

## 🧠 모델 학습 정보

| 항목 | 설정 |
|---|---|
| Model | YOLOv8n |
| Dataset | Pothole Dataset |
| Training Environment | Google Colab |
| Epochs | 50 |
| Image Size | 640 |
| Batch Size | 16 |
| Train / Validation | 80:20 |
| Output Weight | best.pt |

학습된 모델은 `detect/best.pt`에 저장되어 있습니다.

---

## 🖥️ FastAPI 서버 주요 API

| Method | Endpoint | Description |
|---|---|---|
| POST | `/events` | 도로 위험 요소 데이터 수신 |
| GET | `/hazards` | 지정한 위치 주변 위험 요소 조회 |

### 위험 요소 데이터 처리

- GPS 위도 및 경도 수신
- 차량 진행 방향과 오프셋을 이용한 위치 보정
- 15m 이내 동일 유형의 위험 요소 중복 통합
- 카메라와 IMU 데이터의 교차 검증
- 누적 점수에 따른 위험 요소 상태 구분

---

## 📌 개발 진행 현황

- [x] Python 개발 환경 구성
- [x] YOLO 일반 객체 탐지 구현
- [x] 포트홀 데이터셋 준비
- [x] 포트홀 탐지 모델 학습
- [x] 학습 모델 웹캠 테스트
- [x] 일반 객체 및 포트홀 동시 탐지
- [x] 학습 모델 GitHub 반영
- [x] FastAPI 위험 요소 관리 서버 기본 구현
- [ ] YOLO 탐지 결과와 FastAPI 서버 연동
- [ ] GPS 기반 포트홀 위치 추출
- [ ] 지도에 위험 요소 표시
- [ ] 위험 요소 알림 기능 구현
- [ ] 전체 시스템 통합 테스트

---

## 🎯 향후 개발 계획

1. 포트홀 탐지 정확도 개선
2. YOLO 탐지 결과의 FastAPI 서버 연동
3. GPS 정보를 이용한 포트홀 위치 기록
4. 지도 기반 도로 위험 요소 시각화
5. 사용자에게 위험 지역 알림 제공
6. 전체 시스템 통합 및 테스트
