
import 'package:latlong2/latlong.dart';

class Hazard {
  final String id;
  final String type;
  final String description;
  final LatLng position;
  final String status;

  const Hazard({
    required this.id,
    required this.type,
    required this.description,
    required this.position,
    required this.status,
  });
}