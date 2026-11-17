# 도로 위험 3클래스 학습

| 번호 | 클래스 (= 서버 type) |
|---|---|
| 0 | `pothole` |
| 1 | `crack` |
| 2 | `puddle` |

순서는 `detect/config.py`의 `HAZARD_CLASSES`, `docs/api.md` 2장과 같아야 합니다.

## 파일
- `train_hazard3.ipynb`: Colab 노트북. 데이터 내려받기 → 합치기 → 학습 → 결과 확인 → Drive 저장
- `prepare_dataset.py`: 여러 데이터셋의 클래스 번호를 맞춰 하나로 합치는 스크립트 (노트북 안에도 같은 코드가 들어 있음)

## 데이터
| 데이터 | 쓰는 클래스 | 규모 | 라이선스 |
|---|---|---|---|
| [jaygala24/pothole-detection](https://github.com/jaygala24/pothole-detection) | pothole | 1,243장 | 저장소 MIT (데이터 라이선스 별도 명시 없음) |
| [Roboflow RDD (bowee-vision-company/rdd-oxhpg) v8](https://universe.roboflow.com/bowee-vision-company/rdd-oxhpg/dataset/8) | crack(거북등·가로·세로 균열), pothole | 8,594장 중 3,000장 | 페이지에서 확인 필요 |
| [Roboflow RDD (road-damage-detection-wgjj4/rdd-6706t) v12](https://universe.roboflow.com/road-damage-detection-wgjj4/rdd-6706t/dataset/12) | crack, pothole | 2,421장 | 페이지에서 확인 필요 |
| [Roboflow 한양대 Puddle Detection](https://universe.roboflow.com/hanyang-university-bd2kb/puddle-detection/dataset/9) | puddle | 1,400장 | CC BY 4.0 |

공식 RDD2022 S3 주소는 Colab에서 0바이트로 내려와 Roboflow 데이터셋을 씁니다. (datasyn-yolov8/yolov8-rdd2022는 274장, 크랙 12개뿐이라 제외)

발표 자료와 보고서에 출처를 꼭 적습니다.

## 학습 결과 기록
| 버전 | 날짜 | 데이터 | epochs | pothole P/R | crack P/R | puddle P/R | 메모 |
|---|---|---|---|---|---|---|---|
| hazard3_v1 | 2026-11-17 | 위 4종 | 60 | 0.732 / 0.542 (mAP50 0.637) | 0.825 / 0.400 (mAP50 0.582) | 0.727 / 0.832 (mAP50 0.827) | 정밀도는 높고 재현율이 낮음(놓치는 쪽). conf 0.40 |
