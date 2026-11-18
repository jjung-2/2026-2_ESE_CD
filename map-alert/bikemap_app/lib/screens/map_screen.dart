
import 'package:material_ui/material_ui.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../models/hazard.dart';
import '../data/dummy_hazards.dart';

class MapScreen extends StatelessWidget {
  const MapScreen({super.key});

  // 위험 종류에 따라 마커 색상 결정
  Color getMarkerColor(String type) {
    switch (type) {
      case '포트홀':
        return Colors.red;
      case '노면 단차':
        return Colors.orange;
      case '장애물':
        return Colors.purple;
      default:
        return Colors.grey;
    }
  }

  // 마커 클릭 시 상세 정보창 표시
  void showHazardDetail(BuildContext context, Hazard hazard) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                hazard.type,
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),

              const SizedBox(height: 16),

              Text('위험 ID: ${hazard.id}'),

              const SizedBox(height: 8),

              Text('설명: ${hazard.description}'),

              const SizedBox(height: 8),

              Text('상태: ${hazard.status}'),

              const SizedBox(height: 8),

              Text(
                '위도: ${hazard.position.latitude.toStringAsFixed(6)}',
              ),

              Text(
                '경도: ${hazard.position.longitude.toStringAsFixed(6)}',
              ),
            ],
          ),
        );
      },
    );
  }

  // 위험 지점 하나를 마커로 변환
  Marker makeMarker(BuildContext context, Hazard hazard) {
    return Marker(
      point: hazard.position,
      width: 50,
      height: 50,
      child: GestureDetector(
        onTap: () {
          showHazardDetail(context, hazard);
        },
        child: Icon(
          Icons.location_on,
          color: getMarkerColor(hazard.type),
          size: 45,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('BikeMap - 위험 지도'),
        backgroundColor: Colors.green,
        foregroundColor: Colors.white,
      ),

      body: FlutterMap(
        options: const MapOptions(
          initialCenter: LatLng(37.5665, 126.9780),
          initialZoom: 16,
        ),

        children: [
          TileLayer(
            urlTemplate:
                'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'com.example.bikemap_app',
          ),

          MarkerLayer(
            markers: dummyHazards.map((hazard) {
              return makeMarker(context, hazard);
            }).toList(),
          ),

          const SimpleAttributionWidget(
            source: Text('© OpenStreetMap contributors'),
          ),
        ],
      ),
    );
  }
}
