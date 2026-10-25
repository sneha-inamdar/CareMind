import 'dart:convert';
import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
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

  /// Performs diagnostic health check on FastAPI backend (/api/health).
  /// Allows testing a candidate customBaseUrl before saving configuration.
  static Future<ApiResult<Map<String, dynamic>>> checkHealth({
    String? customBaseUrl,
  }) async {
    String healthUrl;
    try {
      healthUrl = customBaseUrl != null
          ? '${ApiConfig.normalizeUrl(customBaseUrl)}/api/health'
          : ApiConfig.health;
    } catch (e) {
      return ApiResult.failure('Invalid URL format: ${e.toString()}');
    }

    try {
      if (kDebugMode) {
        debugPrint('[ApiService] Checking health at: $healthUrl');
      }
      final uri = Uri.parse(healthUrl);
      final response = await http.get(uri).timeout(timeoutDuration);

      if (kDebugMode) {
        debugPrint(
          '[ApiService] Health response status: ${response.statusCode} from $healthUrl',
        );
      }

      if (response.statusCode == 200) {
        try {
          final data = json.decode(response.body);
          if (data is Map && data['status'] == 'online') {
            return ApiResult.success(Map<String, dynamic>.from(data));
          }
          return ApiResult.failure(
            'Backend responded, but reported status: "${data is Map ? data['status'] : 'unknown'}" (expected "online")',
          );
        } catch (e) {
          return ApiResult.failure(
            'Malformed response from health endpoint at $healthUrl',
          );
        }
      }

      return ApiResult.failure(
        'Backend returned HTTP ${response.statusCode} (${response.reasonPhrase}) from $healthUrl',
      );
    } catch (e) {
      if (kDebugMode) {
        debugPrint(
          '[ApiService] Health check failed for $healthUrl: ${e.runtimeType} -> $e',
        );
      }
      return ApiResult.failure(_formatError(e, healthUrl));
    }
  }

  static Future<ApiResult<List<PatientOverview>>> getPatientsOverview({
    int windowIndex = 0,
  }) async {
    final targetUrl = '${ApiConfig.patientsOverview}?window_index=$windowIndex';
    try {
      final uri = Uri.parse(targetUrl);
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
      _logError(targetUrl, e);
      return ApiResult.failure(_formatError(e, targetUrl));
    }
  }

  static Future<ApiResult<List<ActiveAlert>>> getActiveAlerts() async {
    final targetUrl = ApiConfig.activeAlerts;
    try {
      final response = await http
          .get(Uri.parse(targetUrl))
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
      _logError(targetUrl, e);
      return ApiResult.failure(_formatError(e, targetUrl));
    }
  }

  static Future<ApiResult<SimulationState>> getSimulationState() async {
    final targetUrl = ApiConfig.simulationState;
    try {
      final response = await http
          .get(Uri.parse(targetUrl))
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
      return ApiResult.failure(
        'HTTP Error ${response.statusCode}: ${response.reasonPhrase}',
      );
    } catch (e) {
      _logError(targetUrl, e);
      return ApiResult.failure(_formatError(e, targetUrl));
    }
  }

  static Future<ApiResult<SimulationState>> startSimulation() async {
    final targetUrl = ApiConfig.simulationStart;
    try {
      final response = await http
          .post(Uri.parse(targetUrl))
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
      _logError(targetUrl, e);
      return ApiResult.failure(_formatError(e, targetUrl));
    }
  }

  static Future<ApiResult<SimulationState>> stepSimulation() async {
    final targetUrl = ApiConfig.simulationStep;
    try {
      final response = await http
          .post(Uri.parse(targetUrl))
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
      _logError(targetUrl, e);
      return ApiResult.failure(_formatError(e, targetUrl));
    }
  }

  static Future<ApiResult<SimulationState>> pauseSimulation() async {
    final targetUrl = ApiConfig.simulationPause;
    try {
      final response = await http
          .post(Uri.parse(targetUrl))
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
      _logError(targetUrl, e);
      return ApiResult.failure(_formatError(e, targetUrl));
    }
  }

  static Future<ApiResult<SimulationState>> resetSimulation() async {
    final targetUrl = ApiConfig.simulationReset;
    try {
      final response = await http
          .post(Uri.parse(targetUrl))
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
      _logError(targetUrl, e);
      return ApiResult.failure(_formatError(e, targetUrl));
    }
  }

  static Future<ApiResult<Map<String, dynamic>>> registerPatient(
    Map<String, dynamic> patientData,
  ) async {
    final targetUrl = ApiConfig.registerPatient;
    try {
      final response = await http
          .post(
            Uri.parse(targetUrl),
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
      _logError(targetUrl, e);
      return ApiResult.failure(_formatError(e, targetUrl));
    }
  }

  static Future<ApiResult<Map<String, dynamic>>> addCohortPatient(
    String recordId,
  ) async {
    final targetUrl = ApiConfig.addCohortPatient;
    try {
      final response = await http
          .post(
            Uri.parse(targetUrl),
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
      _logError(targetUrl, e);
      return ApiResult.failure(_formatError(e, targetUrl));
    }
  }

  static Future<ApiResult<List<Map<String, dynamic>>>>
  getAvailableCohortRecords() async {
    final targetUrl = ApiConfig.availableCohortRecords;
    try {
      final response = await http
          .get(Uri.parse(targetUrl))
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
      _logError(targetUrl, e);
      return ApiResult.failure(_formatError(e, targetUrl));
    }
  }

  static Future<ApiResult<Map<String, dynamic>>> removePatient(
    String recordId,
  ) async {
    final targetUrl = ApiConfig.removePatient;
    try {
      final response = await http
          .post(
            Uri.parse(targetUrl),
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
      _logError(targetUrl, e);
      return ApiResult.failure(_formatError(e, targetUrl));
    }
  }

  static Future<ApiResult<RecordReplayTimeline>> getReplayTimeline(
    String recordId,
  ) async {
    final targetUrl = ApiConfig.replayTimeline(recordId);
    try {
      final uri = Uri.parse(targetUrl);
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
      return ApiResult.failure(
        'HTTP Error ${response.statusCode}: ${response.reasonPhrase}',
      );
    } catch (e) {
      _logError(targetUrl, e);
      return ApiResult.failure(_formatError(e, targetUrl));
    }
  }

  @visibleForTesting
  static String formatError(dynamic e, [String? targetUrl]) =>
      _formatError(e, targetUrl);

  static void _logError(String url, dynamic e) {
    if (kDebugMode) {
      debugPrint(
        '[ApiService] Request to "$url" failed with: ${e.runtimeType} -> $e',
      );
    }
  }

  static String _formatError(dynamic e, [String? targetUrl]) {
    final url = targetUrl ?? ApiConfig.baseUrl;
    Uri? parsed;
    try {
      parsed = Uri.parse(url);
    } catch (_) {}

    final host = (parsed?.host.isNotEmpty == true) ? parsed!.host : url;
    final port = (parsed != null && parsed.hasPort)
        ? parsed.port.toString()
        : '8000';

    if (e is TimeoutException) {
      return 'Connection timed out connecting to $url. Verify backend is running and phone is on the same Wi-Fi.';
    }

    if (e is FormatException) {
      return 'Malformed response from CareMind backend at $url (invalid JSON).';
    }

    if (e is SocketException) {
      final msg = e.message.toLowerCase();
      final osMsg = e.osError?.message.toLowerCase() ?? '';

      if (msg.contains('refused') || osMsg.contains('refused')) {
        return 'Connection refused at $url. Laptop is reachable, but CareMind backend is not running on port $port.';
      }
      if (msg.contains('failed host lookup') ||
          msg.contains('no address associated')) {
        return 'Unable to resolve host "$host". Verify your laptop IP address.';
      }
      if (msg.contains('no route to host') ||
          msg.contains('network is unreachable') ||
          osMsg.contains('no route') ||
          osMsg.contains('unreachable')) {
        return 'Network route unreachable to $host. Ensure phone and laptop are connected to the same Wi-Fi network.';
      }
      return 'Unable to connect to CareMind backend at $url (${e.message}).';
    }

    final errStr = e.toString();
    if (errStr.contains('Connection refused')) {
      return 'Connection refused at $url. Laptop is reachable, but CareMind backend is not running on port $port.';
    }
    if (errStr.contains('Failed host lookup')) {
      return 'Unable to resolve host "$host". Verify your laptop IP address.';
    }
    if (errStr.contains('Cleartext HTTP traffic')) {
      return 'Cleartext HTTP traffic to $host is blocked by Android security policy.';
    }

    return 'Network Error: $errStr';
  }
}
