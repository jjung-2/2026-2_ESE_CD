# 🛣️ Road Hazard Detection Server

FastAPI 기반의 도로 위험 요소(포트홀, 도로 균열, 장애물 등) 실시간 수신 및 검증 백엔드 서버입니다.  
카메라(YOLO)와 IMU 센서(충격 감지) 제보를 교차 검증하여 위험 요소의 신뢰도를 계산하고 확정(`confirmed`) 처리합니다.

---

## 🛠️ 기술 스택 (Tech Stack)

* **Framework:** FastAPI
* **Server:** Uvicorn
* **Data Validation:** Pydantic
* **Language:** Python 3.10+

---

## ✨ 핵심 기능 (Key Features)

1. **위치 계산 알고리즘 (Haversine & Bearing)**
   * 제보 장비의 위도, 경도, 헤딩(방향각), 오프셋 거리를 기반으로 실제 도로 위험 위치 좌표 재계산
2. **다중 센서 기반 신뢰도 산출 (Scoring System)**
   * 동일 반경(15m 이내) 중복 제보 통합
   * 카메라(Camera) 데이터와 IMU(충격) 센서 데이터가 함께 수집될 경우 추가 가산점 부여
   * 누적 점수(`score`)가 3점 이상일 경우 `"confirmed"`(확정된 위험 지역) 상태로 자동 변경
3. **위치 기반 위험 지역 검색**
   * 특정 위도·경도 좌표 기준 지정한 반경(`radius`, 기본 1km) 내 도로 위험 데이터 조회

---

## 🚀 시작하기 (Quick Start)

### 1. 패키지 설치
```bash
pip install -r requirements.txt
# 또는
pip install fastapi uvicorn pydantic
#
py -m pip install -r requirements.txt
