# API 명세 (기준 문서)

이 문서가 팀의 **유일한 기준**입니다. 서버 코드(`server/main.py`), 단말 펌웨어(`firmware/`), 객체 인식(`detect/`)은 모두 이 문서를 따릅니다. 바꿀 때는 이 문서를 먼저 고치고 팀에 알립니다.

- 기준: 현재 서버 코드의 필드 이름 (`lon`, `time`, `event_id`)
- 최종 수정: 2026-11-17

---

## 1. 공통 규칙

| 항목 | 규칙 | 예 |
|---|---|---|
| 위도·경도 | `lat`, `lon` (WGS84, 소수점 도) | `37.3891`, `126.6432` |
| 시간 | `time`, ISO 8601, 한국 시간 `+09:00` 포함. 단말은 GPS의 UTC 시간을 변환해서 넣는다 | `2026-11-20T14:03:11.200+09:00` |
| 이벤트 ID | `event_id`, 이벤트마다 고유. **재전송해도 같은 값**을 쓴다 | `bike-01-0007-000123` |
| 기기 ID | `device_id`, 단말마다 고정 | `bike-01` |
| 문자 인코딩 | UTF-8 JSON | |

### event_id 만드는 법
- 단말: `{device_id}-{부팅 번호 4자리}-{부팅 후 순번 6자리}` → `bike-01-0007-000123`
  - 부팅 번호는 ESP32 NVS(Preferences)에 저장해 켤 때마다 1씩 올린다.
- 카메라(PC 스크립트): `cam-{영상 파일명}-{프레임 번호}` → `cam-ride1107-004512`
- 서버는 이미 받은 `event_id`가 다시 오면 저장하지 않고 같은 `hazard_id`를 돌려준다. 그래서 전송 실패 시 마음 놓고 다시 보내도 된다.

### 보내지 않는 경우
- GPS 위치나 GPS 시간이 아직 없는 이벤트는 서버로 보내지 않는다. 단말 microSD에는 기록해 둔다.

---

## 2. 위험 유형 (type)

**규칙: YOLO 클래스 이름 = 서버 type 이름.** 영문 소문자로 쓰고, 다른 이름(별칭)은 쓰지 않는다.

| type | 의미 | 만드는 곳 | 만료 | 상태 |
|---|---|---|---|---|
| `pothole` | 포트홀 | YOLO 클래스 `pothole` | 해결 투표 전까지 | 사용 |
| `crack` | 균열, 노면 파손 (거북등 균열 위주) | YOLO 클래스 `crack` | 해결 투표 전까지 | 사용 |
| `puddle` | 물웅덩이 | YOLO 클래스 `puddle` | 24시간 | 사용 |
| `crowd` | 인파 (사람 무리) | YOLO `person` 수로 판정 (아래 규칙) | **10분** | 사용 |
| `bump` | 충격 지점 (원인 미상 요철) | 단말 IMU | 해결 투표 전까지 | 사용 |
| `step` | 경로상 단차(턱) | YOLO 클래스 `step` | 해결 투표 전까지 | **보류** (데이터 부족) |
| `obstacle` | 장애물, 공사 | 추후 | 추후 | 보류 |
| `etc` | 기타 | - | - | 사용 |

- `crowd`는 학습한 클래스가 아니라 **판정 결과**다. 사전학습 모델의 `person`을 세어서, 화면 아래쪽 60% 영역 안에 사람이 3명 이상(신뢰도 0.4 이상)이면 `crowd` 이벤트를 만든다. 기준값은 `detect/config.py`에 둔다.
- `crowd`, `puddle`처럼 금방 사라지는 위험의 만료 처리는 서버 담당이 구현한다. 위 만료 시간은 제안값이다.
- 이전 초안의 `damage`는 `crack`으로 바꾼다.

---

## 3. 서버 API

### 3-1. `POST /events` — 이벤트 1건 보내기 (구현됨)
보내는 쪽: 단말(ESP32), 카메라 인식 스크립트

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `event_id` | string | O | 1장 규칙 |
| `source` | string | O | `imu` 또는 `camera` |
| `type` | string | O | 2장 type |
| `lat`, `lon` | float | O | 이벤트가 일어난 위치 (카메라는 촬영 위치) |
| `time` | string | O | 1장 규칙 |
| `speed_kmh` | float | | 이벤트 시점 속도 |
| `heading_deg` | float | | 진행 방향 (북쪽 0°, 시계 방향) |
| `severity` | float | | IMU: 중력을 뺀 최대 가속도 크기(g). 카메라: 0 |
| `confidence` | float | | 카메라: YOLO 신뢰도 0~1. IMU: 생략 |
| `offset_m` | float | | 카메라: 촬영 위치에서 위험까지 앞쪽 거리(m). 서버가 이 값과 `heading_deg`로 위험 위치를 보정한다 |
| `image_url` | string | | 카메라: 위험 부분 이미지 주소 (추후) |
| `device_id` | string | O | 1장 규칙 |

단말이 보내는 예:
```json
{
  "event_id": "bike-01-0007-000123",
  "source": "imu",
  "type": "bump",
  "lat": 37.3891,
  "lon": 126.6432,
  "time": "2026-11-20T14:03:11.200+09:00",
  "speed_kmh": 17.6,
  "heading_deg": 92,
  "severity": 2.4,
  "device_id": "bike-01"
}
```

카메라 스크립트가 보내는 예:
```json
{
  "event_id": "cam-ride1107-004512",
  "source": "camera",
  "type": "pothole",
  "lat": 37.3889,
  "lon": 126.6425,
  "time": "2026-11-20T14:02:58.400+09:00",
  "speed_kmh": 18.0,
  "heading_deg": 90,
  "severity": 0,
  "confidence": 0.74,
  "offset_m": 6.5,
  "device_id": "cam-01"
}
```

응답:
```json
{ "event_id": "bike-01-0007-000123", "hazard_id": 12 }
```

> **서버 담당 확인 요청**: 지금 서버는 type이 같을 때만 15m 안의 이벤트를 합친다. IMU는 원인을 모르니 항상 `bump`로 보내므로, 카메라의 `pothole`과 IMU의 `bump`가 같은 자리여도 합쳐지지 않아 **카메라·충격 교차 확인 점수(+1)가 생기지 않는다.** `bump`는 15m 안의 `pothole`·`crack`·`step` 위험과 합치도록 바꿔 주세요.

### 3-2. `GET /hazards?lat=..&lon=..&radius=1000` — 주변 위험 목록 (구현됨)
응답:
```json
{
  "hazards": [
    { "id": 12, "type": "pothole", "lat": 37.3893, "lon": 126.6447,
      "score": 3, "status": "confirmed", "last_seen": "2026-11-20T14:05:00+09:00" }
  ]
}
```
- `status`: `score` 3 이상이면 `confirmed`, 아니면 `unconfirmed` (서버 코드 기준).

### 3-3. 앱이 쓰는 API
`POST /reports`(사용자 제보), `POST /hazards/{id}/votes`(“아직 있어요 / 없어졌어요”)는 앱·서버 담당이 정한다. 형식은 이 문서의 공통 규칙(`lon`, `time`, `event_id`)을 따른다.

---

## 4. 단말 ↔ 앱 통신 (BLE, 초안)

이번 학기에는 단말이 와이파이로 `POST /events`를 직접 보낸다. 방학에 BLE로 바꾸며, 그때 쓸 규격 초안이다. **앱 쪽 구현은 하지 않고**, 단말 펌웨어와 이 규격, Flutter에서 바로 쓸 수 있는 BLE 연결 예제까지를 하드웨어 담당이 제공한다.

- 단말 이름: `RHD-{device_id}` (예: `RHD-bike-01`)
- 메시지는 UTF-8 JSON 한 줄. 필드 이름은 3장과 같다. 연결 후 MTU 247 요청.

| 특성(Characteristic) | 방향 | 방식 | 내용 |
|---|---|---|---|
| `event` | 단말 → 앱 | Notify | 충격(`bump`), 낙차(`fall`), 후방 차량(`rear_vehicle`) |
| `status` | 단말 → 앱 | Notify, Read | 배터리, GPS 수신, 기록 상태 (5초마다) |
| `command` | 앱 → 단말 | Write | 진동·LED 명령 |

UUID는 펌웨어 작성 시 확정해 여기에 적는다.

메시지 예:
```json
{"kind":"bump","event_id":"bike-01-0007-000123","lat":37.3891,"lon":126.6432,"time":"2026-11-20T14:03:11.200+09:00","speed_kmh":17.6,"heading_deg":92,"severity":2.4}
{"kind":"fall","event_id":"bike-01-0007-000124","lat":37.3891,"lon":126.6432,"time":"2026-11-20T14:05:40.000+09:00"}
{"kind":"rear_vehicle","distance_m":42,"speed_kmh":38}
{"kind":"status","battery_v":3.92,"sats":9,"fix":true,"logging":true}
{"kind":"vibrate","pattern":"left"}
```
- 앱은 `bump` 메시지를 받으면 그대로 `POST /events`(`source: imu`, `type: bump`, `device_id` 추가)로 서버에 보낸다.
- `fall`, `rear_vehicle`은 위험 지점이 아니므로 `/events`로 보내지 않는다. 어떻게 보여 줄지는 앱 담당이 정한다.
- `vibrate`의 `pattern`: `left`, `right`, `alert`
