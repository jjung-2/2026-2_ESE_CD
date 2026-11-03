# API 명세 (초안)

## 위험 유형 (type)
영문 소문자로 통일합니다. YOLO 클래스 이름과 서버의 type이 같아야 합니다.

| type | 의미 | YOLO 클래스 |
|---|---|---|
| `pothole` | 포트홀 | pothole |
| `damage` | 크랙, 노면 파손 | crack |
| `puddle` | 물웅덩이 | puddle |
| `step` | 경로상 단차(턱) | step (추가 예정) |
| `obstacle` | 장애물, 공사 | (추후) |
| `bump` | 요철, 과속방지턱 | (추후, IMU 위주) |
| `etc` | 기타 | - |

※ `step` 추가는 팀 합의 후 확정합니다.