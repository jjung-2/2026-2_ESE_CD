from datetime import datetime
from math import radians, degrees, sin, cos, asin, sqrt, atan2
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Road Hazard API")

class Event(BaseModel):
    event_id: str
    source: str                    # imu | camera
    type: str                      # pothole | damage | puddle | obstacle | bump | etc
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    time: datetime
    speed_kmh: float = 0
    heading_deg: float = 0
    severity: float = 0
    confidence: Optional[float] = None
    offset_m: float = 0
    image_url: Optional[str] = None
    device_id: str

seen = {}      # event_id -> hazard_id (중복 방지)
hazards = []

def distance_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = radians(lat1), radians(lat2)
    dp, dl = p2 - p1, radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * R * asin(sqrt(a))

def move(lat, lon, heading_deg, dist_m):
    R, d, th = 6371000, dist_m / 6371000, radians(heading_deg)
    p1, l1 = radians(lat), radians(lon)
    p2 = asin(sin(p1) * cos(d) + cos(p1) * sin(d) * cos(th))
    l2 = l1 + atan2(sin(th) * sin(d) * cos(p1), cos(d) - sin(p1) * sin(p2))
    return degrees(p2), degrees(l2)

@app.post("/events")
def post_event(e: Event):
    if e.event_id in seen:
        return {"event_id": e.event_id, "hazard_id": seen[e.event_id]}
    lat, lon = (move(e.lat, e.lon, e.heading_deg, e.offset_m)
                if e.offset_m else (e.lat, e.lon))
    for h in hazards:
        if h["type"] == e.type and distance_m(lat, lon, h["lat"], h["lon"]) <= 15:
            if e.source not in h["sources"]:
                h["sources"].add(e.source)
                h["score"] += 1
                if len(h["sources"]) == 2:
                    h["score"] += 1        # 카메라와 충격이 함께 나옴
            h["last_seen"] = e.time
            seen[e.event_id] = h["id"]
            return {"event_id": e.event_id, "hazard_id": h["id"]}
    h = {"id": len(hazards) + 1, "type": e.type, "lat": lat, "lon": lon,
         "score": 1, "sources": {e.source}, "last_seen": e.time}
    hazards.append(h)
    seen[e.event_id] = h["id"]
    return {"event_id": e.event_id, "hazard_id": h["id"]}

@app.get("/hazards")
def get_hazards(lat: float, lon: float, radius: int = 1000):
    return {"hazards": [
        {"id": h["id"], "type": h["type"], "lat": h["lat"], "lon": h["lon"],
         "score": h["score"],
         "status": "confirmed" if h["score"] >= 3 else "unconfirmed",
         "last_seen": h["last_seen"].isoformat()}
        for h in hazards if distance_m(lat, lon, h["lat"], h["lon"]) <= radius
    ]}