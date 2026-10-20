import 'package:flutter/foundation.dart';

class ApiConfig {
  static const String defaultEmulatorUrl = 'http://10.0.2.2:8000';
  static const String defaultLocalhostUrl = 'http://localhost:8000';

  static String? _customUrl;

  static String _detectDefaultUrl() {
    // 1. Check dart-define environment variable
    const envUrl = String.fromEnvironment('API_URL');
    if (envUrl.isNotEmpty) {
      return envUrl;
    }

    // 2. Platform-aware auto-detection
    if (kIsWeb) {
      return defaultLocalhostUrl;
    }

    if (defaultTargetPlatform == TargetPlatform.android) {
      return defaultEmulatorUrl;
    }

    return defaultLocalhostUrl;
  }

  static String get baseUrl {
    return _customUrl ?? _detectDefaultUrl();
  }

  static String get platformName {
    if (kIsWeb) {
      return 'Flutter Web / Chrome';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'Android Device / Emulator';
    }
    if (defaultTargetPlatform == TargetPlatform.iOS) {
      return 'iOS Simulator / Device';
    }
    return 'Desktop / Host';
  }

  static bool get isCustomUrlSet => _customUrl != null;

  static void setBaseUrl(String url) {
    String cleanUrl = url.trim();
    if (cleanUrl.endsWith('/')) {
      cleanUrl = cleanUrl.substring(0, cleanUrl.length - 1);
    }
    _customUrl = cleanUrl;
    if (kDebugMode) {
      print('[ApiConfig] Base URL updated to: $_customUrl ($platformName)');
    }
  }

  static void resetToDefault() {
    _customUrl = null;
  }

  // Endpoints
  static String get health => '$baseUrl/api/health';
  static String get availableRecords => '$baseUrl/api/multimodal/records';
  static String get patientsOverview => '$baseUrl/api/multimodal/patients';
  static String recordDetail(String recordId) =>
      '$baseUrl/api/multimodal/records/$recordId';
  static String get analyze => '$baseUrl/api/multimodal/analyze';
  static String replayTimeline(String recordId) =>
      '$baseUrl/api/multimodal/replay/$recordId';
  static String get activeAlerts => '$baseUrl/api/alerts';
  static String patientAlerts(String patientId) =>
      '$baseUrl/api/alerts/$patientId';
  static String get simulationState => '$baseUrl/api/simulation/state';
  static String get simulationStart => '$baseUrl/api/simulation/start';
  static String get simulationPause => '$baseUrl/api/simulation/pause';
  static String get simulationReset => '$baseUrl/api/simulation/reset';
  static String get simulationStep => '$baseUrl/api/simulation/step';
  static String get registerPatient => '$baseUrl/api/patients/register';
  static String get registeredPatients => '$baseUrl/api/patients/registered';
  static String get addCohortPatient => '$baseUrl/api/multimodal/patients/add';
  static String get availableCohortRecords =>
      '$baseUrl/api/multimodal/records/available';
  static String get removePatient => '$baseUrl/api/multimodal/patients/remove';
}
