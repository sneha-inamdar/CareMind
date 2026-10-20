import 'dart:convert';
import 'dart:async';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../models/patient.dart';
import '../models/alert.dart';
import '../models/simulation_state.dart';
import '../models/record_detail.dart';

class ApiResult<T> {
  final T? data;
  final String? errorMessage;
  final bool isSuccess;

  ApiResult.success(this.data) : errorMessage = null, isSuccess = true;

  ApiResult.failure(this.errorMessage) : data = null, isSuccess = false;
}

class ApiService {
  static const Duration timeoutDuration = Duration(seconds: 8);

  static Future<ApiResult<bool>> checkHealth() async {
    try {
      final response = await http
          .get(Uri.parse(ApiConfig.health))
          .timeout(timeoutDuration);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['status'] == 'online') {
          return ApiResult.success(true);
        }
      }
      return ApiResult.failure(
        'Backend returned status code ${response.statusCode}',
      );
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static Future<ApiResult<List<PatientOverview>>> getPatientsOverview({
    int windowIndex = 0,
  }) async {
    try {
      final uri = Uri.parse(
        '${ApiConfig.patientsOverview}?window_index=$windowIndex',
      );
      final response = await http.get(uri).timeout(timeoutDuration);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map && data['patients'] is List) {
          final List rawList = data['patients'];
          final patients = rawList
              .map(
                (p) => PatientOverview.fromJson(Map<String, dynamic>.from(p)),
              )
              .toList();
          if (data['registered_patients'] is List) {
            final List rawReg = data['registered_patients'];
            patients.addAll(
              rawReg.map(
                (p) => PatientOverview.fromJson(Map<String, dynamic>.from(p)),
              ),
            );
          }
          return ApiResult.success(patients);
        }
        return ApiResult.failure('Unexpected response format from backend');
      }
      return ApiResult.failure(
        'HTTP Error ${response.statusCode}: ${response.reasonPhrase}',
      );
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static Future<ApiResult<List<ActiveAlert>>> getActiveAlerts() async {
    try {
      final response = await http
          .get(Uri.parse(ApiConfig.activeAlerts))
          .timeout(timeoutDuration);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map && data['alerts'] is List) {
          final List rawList = data['alerts'];
          final alerts = rawList
              .map((a) => ActiveAlert.fromJson(Map<String, dynamic>.from(a)))
              .toList();
          return ApiResult.success(alerts);
        }
        return ApiResult.failure('Unexpected alert payload from backend');
      }
      return ApiResult.failure('HTTP Error ${response.statusCode}');
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static Future<ApiResult<SimulationState>> getSimulationState() async {
    try {
      final response = await http
          .get(Uri.parse(ApiConfig.simulationState))
          .timeout(timeoutDuration);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return ApiResult.success(
            SimulationState.fromJson(Map<String, dynamic>.from(data)),
          );
        }
        return ApiResult.failure('Invalid simulation state response');
      }
      return ApiResult.failure('HTTP Error ${response.statusCode}');
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static Future<ApiResult<SimulationState>> startSimulation() async {
    try {
      final response = await http
          .post(Uri.parse(ApiConfig.simulationStart))
          .timeout(timeoutDuration);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return ApiResult.success(
            SimulationState.fromJson(Map<String, dynamic>.from(data)),
          );
        }
      }
      return ApiResult.failure(
        'Failed to start simulation (${response.statusCode})',
      );
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static Future<ApiResult<SimulationState>> stepSimulation() async {
    try {
      final response = await http
          .post(Uri.parse(ApiConfig.simulationStep))
          .timeout(timeoutDuration);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return ApiResult.success(
            SimulationState.fromJson(Map<String, dynamic>.from(data)),
          );
        }
      }
      return ApiResult.failure(
        'Failed to step simulation (${response.statusCode})',
      );
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static Future<ApiResult<SimulationState>> pauseSimulation() async {
    try {
      final response = await http
          .post(Uri.parse(ApiConfig.simulationPause))
          .timeout(timeoutDuration);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return ApiResult.success(
            SimulationState.fromJson(Map<String, dynamic>.from(data)),
          );
        }
      }
      return ApiResult.failure(
        'Failed to pause simulation (${response.statusCode})',
      );
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static Future<ApiResult<SimulationState>> resetSimulation() async {
    try {
      final response = await http
          .post(Uri.parse(ApiConfig.simulationReset))
          .timeout(timeoutDuration);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return ApiResult.success(
            SimulationState.fromJson(Map<String, dynamic>.from(data)),
          );
        }
      }
      return ApiResult.failure(
        'Failed to reset simulation (${response.statusCode})',
      );
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static Future<ApiResult<Map<String, dynamic>>> registerPatient(
    Map<String, dynamic> patientData,
  ) async {
    try {
      final response = await http
          .post(
            Uri.parse(ApiConfig.registerPatient),
            headers: {'Content-Type': 'application/json'},
            body: json.encode(patientData),
          )
          .timeout(timeoutDuration);

      final data = json.decode(response.body);
      if (response.statusCode == 200 || response.statusCode == 201) {
        if (data is Map) {
          return ApiResult.success(Map<String, dynamic>.from(data));
        }
      }
      final errMsg = (data is Map && data['detail'] != null)
          ? data['detail'].toString()
          : 'Registration failed (${response.statusCode})';
      return ApiResult.failure(errMsg);
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static Future<ApiResult<Map<String, dynamic>>> addCohortPatient(
    String recordId,
  ) async {
    try {
      final response = await http
          .post(
            Uri.parse(ApiConfig.addCohortPatient),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'record_id': recordId}),
          )
          .timeout(timeoutDuration);

      final data = json.decode(response.body);
      if (response.statusCode == 200 || response.statusCode == 201) {
        if (data is Map) {
          return ApiResult.success(Map<String, dynamic>.from(data));
        }
      }
      final errMsg = (data is Map && data['detail'] != null)
          ? data['detail'].toString()
          : 'Failed to add cohort patient (${response.statusCode})';
      return ApiResult.failure(errMsg);
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static Future<ApiResult<List<Map<String, dynamic>>>>
  getAvailableCohortRecords() async {
    try {
      final response = await http
          .get(Uri.parse(ApiConfig.availableCohortRecords))
          .timeout(timeoutDuration);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map && data['records'] is List) {
          final List raw = data['records'];
          final list = raw.map((r) => Map<String, dynamic>.from(r)).toList();
          return ApiResult.success(list);
        }
      }
      return ApiResult.failure(
        'Failed to load available records (${response.statusCode})',
      );
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static Future<ApiResult<Map<String, dynamic>>> removePatient(
    String recordId,
  ) async {
    try {
      final response = await http
          .post(
            Uri.parse(ApiConfig.removePatient),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'record_id': recordId}),
          )
          .timeout(timeoutDuration);

      final data = json.decode(response.body);
      if (response.statusCode == 200) {
        if (data is Map) {
          return ApiResult.success(Map<String, dynamic>.from(data));
        }
      }
      final errMsg = (data is Map && data['detail'] != null)
          ? data['detail'].toString()
          : 'Failed to remove patient (${response.statusCode})';
      return ApiResult.failure(errMsg);
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static Future<ApiResult<RecordReplayTimeline>> getReplayTimeline(
    String recordId,
  ) async {
    try {
      final uri = Uri.parse(ApiConfig.replayTimeline(recordId));
      final response = await http.get(uri).timeout(timeoutDuration);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return ApiResult.success(
            RecordReplayTimeline.fromJson(Map<String, dynamic>.from(data)),
          );
        }
        return ApiResult.failure('Invalid timeline response structure');
      }
      return ApiResult.failure('HTTP Error ${response.statusCode}');
    } catch (e) {
      return ApiResult.failure(_formatError(e));
    }
  }

  static String _formatError(dynamic e) {
    if (e is TimeoutException) {
      return 'Connection timed out. Verify backend URL: ${ApiConfig.baseUrl}';
    }
    final msg = e.toString();
    if (msg.contains('SocketException') ||
        msg.contains('Failed host lookup') ||
        msg.contains('Connection refused')) {
      return 'Unable to connect to CareMind backend at ${ApiConfig.baseUrl}. Please check server status or IP.';
    }
    return 'Network Error: $msg';
  }
}
