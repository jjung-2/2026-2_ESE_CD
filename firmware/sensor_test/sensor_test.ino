/*
 * sensor_test.ino
 * ESP32-S3-DevKitC-1 + MPU6050(GY-521) + NEO-7M 동작 확인용
 *
 * 하는 일
 *  - MPU6050: ±16g / ±500dps, 내부 저역필터 약 94Hz, 100Hz로 읽기, 시작 시 자이로 영점 보정
 *  - NEO-7M : 38400bps + 5Hz로 설정, 필요 없는 NMEA 문장 끄기, GPS UTC 시간을 한국 시간으로 변환
 *  - 시리얼로 CSV 한 줄씩 출력 (시리얼 모니터 / 시리얼 플로터 / 파일 저장용)
 *
 * 배선
 *  MPU6050  VCC→3V3, GND→GND, SDA→GPIO9, SCL→GPIO8
 *  NEO-7M   VCC→5V(또는 3V3), GND→GND, TX→GPIO18(ESP RX), RX→GPIO17(ESP TX)
 *
 * 필요 라이브러리: TinyGPSPlus (Mikal Hart) — 라이브러리 매니저에서 설치
 * 시리얼 모니터 속도: 921600 (115200이면 100Hz 출력을 다 못 보냄)
 */

#include <Wire.h>
#include <TinyGPSPlus.h>

// ---------------- 핀·설정 ----------------
#define SDA_PIN 9
#define SCL_PIN 8
#define GPS_RX_PIN 18   // ESP32가 받는 핀 = GPS의 TX
#define GPS_TX_PIN 17   // ESP32가 보내는 핀 = GPS의 RX

#define MPU_ADDR 0x68
#define SAMPLE_HZ 100
#define SERIAL_BAUD 921600
#define GPS_BAUD_DEFAULT 9600
#define GPS_BAUD 38400

// MPU6050 레지스터
#define REG_SMPLRT_DIV   0x19
#define REG_CONFIG       0x1A
#define REG_GYRO_CONFIG  0x1B
#define REG_ACCEL_CONFIG 0x1C
#define REG_ACCEL_XOUT_H 0x3B
#define REG_PWR_MGMT_1   0x6B
#define REG_WHO_AM_I     0x75

// ±16g → 2048 LSB/g, ±500dps → 65.5 LSB/(deg/s)
const float ACC_LSB = 2048.0f;
const float GYR_LSB = 65.5f;

TinyGPSPlus gps;
HardwareSerial GPSSerial(1);

float gyroBias[3] = {0, 0, 0};

// ---------------- MPU6050 ----------------
bool writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readRegisters(uint8_t reg, uint8_t *data, uint8_t len) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)len) != len) return false;
  for (uint8_t i = 0; i < len; i++) data[i] = Wire.read();
  return true;
}

int16_t read16(const uint8_t *d, int i) {
  return (int16_t)((d[i] << 8) | d[i + 1]);
}

bool readImu(float acc[3], float gyr[3]) {
  uint8_t d[14];
  if (!readRegisters(REG_ACCEL_XOUT_H, d, 14)) return false;
  for (int k = 0; k < 3; k++) {
    acc[k] = read16(d, k * 2) / ACC_LSB;
    gyr[k] = read16(d, 8 + k * 2) / GYR_LSB - gyroBias[k];
  }
  return true;
}

bool setupMpu() {
  if (!writeRegister(REG_PWR_MGMT_1, 0x01)) return false;  // 잠 깨우기 + 자이로 X축 PLL 클럭(내부 8MHz보다 안정)
  delay(100);

  uint8_t id = 0;
  if (!readRegisters(REG_WHO_AM_I, &id, 1)) return false;
  Serial.printf("# WHO_AM_I: 0x%02X", id);
  if (id == 0x68) Serial.println(" (MPU6050 정품 응답)");
  else Serial.println(" (0x68이 아님: 호환/복제 칩일 수 있음. 값은 나오지만 성능이 다를 수 있음)");

  writeRegister(REG_CONFIG, 0x02);        // 저역필터: 가속도 약 94Hz, 자이로 약 98Hz
  writeRegister(REG_SMPLRT_DIV, 9);       // 1kHz / (1+9) = 100Hz
  writeRegister(REG_GYRO_CONFIG, 0x08);   // ±500 deg/s
  writeRegister(REG_ACCEL_CONFIG, 0x18);  // ±16g (포트홀 충격이 8g를 넘을 수 있음)
  return true;
}

// 전원 켠 직후 1초 동안 움직이지 않게 두고 자이로 영점을 잡는다
void calibrateGyro() {
  const int N = 200;
  float sum[3] = {0, 0, 0};
  float a[3], g[3];
  int ok = 0;
  for (int i = 0; i < N; i++) {
    if (readImu(a, g)) {
      for (int k = 0; k < 3; k++) sum[k] += g[k];
      ok++;
    }
    delay(5);
  }
  if (ok > 0) for (int k = 0; k < 3; k++) gyroBias[k] = sum[k] / ok;
  Serial.printf("# gyro bias: %.2f %.2f %.2f deg/s (%d samples)\n", gyroBias[0], gyroBias[1], gyroBias[2], ok);
}

// ---------------- NEO-7M (UBX 설정) ----------------
void sendUbx(uint8_t cls, uint8_t id, const uint8_t *payload, uint16_t len) {
  uint8_t ckA = 0, ckB = 0;
  auto add = [&](uint8_t b) { ckA += b; ckB += ckA; };
  uint8_t head[4] = {cls, id, (uint8_t)(len & 0xFF), (uint8_t)(len >> 8)};
  GPSSerial.write(0xB5);
  GPSSerial.write(0x62);
  for (int i = 0; i < 4; i++) { GPSSerial.write(head[i]); add(head[i]); }
  for (uint16_t i = 0; i < len; i++) { GPSSerial.write(payload[i]); add(payload[i]); }
  GPSSerial.write(ckA);
  GPSSerial.write(ckB);
  GPSSerial.flush();
}

void setupGps() {
  // 1) 기본 9600bps로 열고, UART1 속도를 38400으로 바꾸라고 명령
  GPSSerial.begin(GPS_BAUD_DEFAULT, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  delay(200);
  const uint32_t baud = GPS_BAUD;
  uint8_t prt[20] = {
    0x01, 0x00, 0x00, 0x00,                 // portID=UART1, reserved, txReady
    0xD0, 0x08, 0x00, 0x00,                 // mode: 8N1
    (uint8_t)(baud), (uint8_t)(baud >> 8), (uint8_t)(baud >> 16), (uint8_t)(baud >> 24),
    0x07, 0x00,                             // 입력: UBX+NMEA+RTCM
    0x03, 0x00,                             // 출력: UBX+NMEA
    0x00, 0x00, 0x00, 0x00
  };
  sendUbx(0x06, 0x00, prt, sizeof(prt));     // CFG-PRT
  delay(150);

  // 2) 38400bps로 다시 열기 (이미 38400으로 저장된 모듈이어도 여기서부터는 정상)
  GPSSerial.end();
  GPSSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  delay(150);

  // 3) 5Hz (200ms 간격)
  uint8_t rate[6] = {0xC8, 0x00, 0x01, 0x00, 0x01, 0x00};
  sendUbx(0x06, 0x08, rate, sizeof(rate));   // CFG-RATE
  delay(100);

  // 4) 필요 없는 NMEA 끄기: GLL, GSA, GSV, VTG (RMC·GGA만 남김)
  const uint8_t offIds[] = {0x01, 0x02, 0x03, 0x05};
  for (uint8_t mid : offIds) {
    uint8_t msg[3] = {0xF0, mid, 0x00};
    sendUbx(0x06, 0x01, msg, sizeof(msg));   // CFG-MSG
    delay(50);
  }
  // 설정은 전원을 끄면 초기화된다(매번 부팅 때 다시 보냄). 저장이 필요하면 CFG-CFG를 추가.
}

// ---------------- 시간: GPS UTC → 한국 시간 ISO 8601 ----------------
// 1970-01-01부터의 날짜 수 (윤년 계산 포함)
int64_t daysFromCivil(int y, unsigned m, unsigned d) {
  y -= m <= 2;
  const int era = (y >= 0 ? y : y - 399) / 400;
  const unsigned yoe = (unsigned)(y - era * 400);
  const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
  const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  return (int64_t)era * 146097 + (int64_t)doe - 719468;
}

void civilFromDays(int64_t z, int &y, unsigned &m, unsigned &d) {
  z += 719468;
  const int64_t era = (z >= 0 ? z : z - 146096) / 146097;
  const unsigned doe = (unsigned)(z - era * 146097);
  const unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
  const unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
  const unsigned mp = (5 * doy + 2) / 153;
  d = doy - (153 * mp + 2) / 5 + 1;
  m = mp + (mp < 10 ? 3 : -9);
  y = (int)(yoe + era * 400) + (m <= 2);
}

// GPS 시간이 유효하면 true, out에 "2026-11-20T14:03:11.200+09:00"
bool gpsTimeKst(char *out, size_t n) {
  if (!gps.date.isValid() || !gps.time.isValid() || gps.date.year() < 2024) return false;
  int64_t secs = daysFromCivil(gps.date.year(), gps.date.month(), gps.date.day()) * 86400LL
                 + gps.time.hour() * 3600 + gps.time.minute() * 60 + gps.time.second()
                 + 9 * 3600;  // +09:00
  int64_t days = secs / 86400;
  int rem = (int)(secs % 86400);
  int y; unsigned mo, d;
  civilFromDays(days, y, mo, d);
  snprintf(out, n, "%04d-%02u-%02uT%02d:%02d:%02d.%03d+09:00",
           y, mo, d, rem / 3600, (rem % 3600) / 60, rem % 60, gps.time.centisecond() * 10);
  return true;
}

// ---------------- 메인 ----------------
void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(1500);
  Serial.println("# sensor_test start");

  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);  // 100Hz 이상 읽으려면 400kHz

  if (!setupMpu()) {
    Serial.println("# MPU6050 응답 없음: 배선(SDA=9, SCL=8)과 전원을 확인하세요");
    while (true) delay(1000);
  }
  calibrateGyro();
  setupGps();

  Serial.println("ms,time_kst,fix,lat,lon,sats,hdop,speed_kmh,course_deg,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps");
}

void loop() {
  // GPS 문자는 오는 대로 계속 읽어야 한다
  while (GPSSerial.available()) gps.encode(GPSSerial.read());

  static uint32_t next = micros();
  const uint32_t period = 1000000UL / SAMPLE_HZ;
  if ((int32_t)(micros() - next) < 0) return;
  next += period;

  float a[3], g[3];
  if (!readImu(a, g)) {
    Serial.println("# IMU read failed");
    return;
  }

  char t[40] = "";
  bool timeOk = gpsTimeKst(t, sizeof(t));
  bool fix = gps.location.isValid() && gps.location.age() < 2000;

  Serial.printf("%lu,%s,%d,%.6f,%.6f,%u,%.1f,%.1f,%.0f,%.3f,%.3f,%.3f,%.2f,%.2f,%.2f\n",
                (unsigned long)millis(), timeOk ? t : "",
                fix ? 1 : 0,
                fix ? gps.location.lat() : 0.0, fix ? gps.location.lng() : 0.0,
                gps.satellites.isValid() ? (unsigned)gps.satellites.value() : 0u,
                gps.hdop.isValid() ? gps.hdop.hdop() : 99.9,
                gps.speed.isValid() ? gps.speed.kmph() : 0.0,
                gps.course.isValid() ? gps.course.deg() : 0.0,
                a[0], a[1], a[2], g[0], g[1], g[2]);
}
