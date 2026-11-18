
import 'package:latlong2/latlong.dart';
import '../models/hazard.dart';

const List<Hazard> dummyHazards = [
  Hazard(
    id: 'H001',
    type: '포트홀',
    description: '도로가 움푹 파인 위험 후보 구간',
    position: LatLng(37.5665, 126.9780),
    status: '미확인',
  ),

  Hazard(
    id: 'H002',
    type: '노면 단차',
    description: '노면에 높이 차이가 발생한 구간',
    position: LatLng(37.5672, 126.9797),
    status: '미확인',
  ),

  Hazard(
    id: 'H003',
    type: '장애물',
    description: '자전거 진행 경로에 장애물이 있는 구간',
    position: LatLng(37.5651, 126.9768),
    status: '미확인',
  ),
]; // 가짜 위험 3개 -> 앞으로 위험 지점 추가하고 싶으면 이 파일에 hazard 객체 추가하면 됨.