import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiConfig {
  static const int defaultPort = 8000;
  static const String defaultEmulatorUrl = 'http://10.0.2.2:8000';
  static const String defaultLocalhostUrl = 'http://localhost:8000';
  static const String prefKey = 'caremind_backend_url';

  static String? _customUrl;
  static bool _isInitialized = false;

  /// Detect platform-aware fallback URL
  static String _detectDefaultUrl() {
    // 1. Check dart-define environment variable
    const envUrl = String.fromEnvironment('API_URL');
    if (envUrl.isNotEmpty) {
      try {
        return normalizeUrl(envUrl);
      } catch (_) {
        return envUrl;
      }
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

  /// Normalize and validate a user-supplied backend URL.
  /// Ensures valid scheme (http/https), host, default port (8000 for http when omitted),
  /// and strips trailing slashes or duplicate '/api' paths.
  static String normalizeUrl(String input, {int defaultPort = defaultPort}) {
    String clean = input.trim();
    if (clean.isEmpty) {
      throw const FormatException('Backend URL cannot be empty');
    }

    // Prepend http:// scheme if neither http:// nor https:// is specified
    if (!clean.startsWith('http://') && !clean.startsWith('https://')) {
      clean = 'http://$clean';
    }

    final Uri parsed;
    try {
      parsed = Uri.parse(clean);
    } catch (e) {
      throw FormatException('Invalid URL format: $input');
    }

    if (parsed.host.isEmpty) {
      throw FormatException('Invalid URL host in: $input');
    }

    // When no port is explicitly specified and scheme is http, default to defaultPort (8000)
    final int? effectivePort;
    if (parsed.hasPort) {
      effectivePort = parsed.port;
    } else if (parsed.scheme == 'http') {
      effectivePort = defaultPort;
    } else {
      effectivePort = null;
    }

    // Clean path: strip trailing slashes and redundant '/api'
    String cleanPath = parsed.path;
    while (cleanPath.endsWith('/')) {
      cleanPath = cleanPath.substring(0, cleanPath.length - 1);
    }
    if (cleanPath.endsWith('/api')) {
      cleanPath = cleanPath.substring(0, cleanPath.length - 4);
    }
    while (cleanPath.endsWith('/')) {
      cleanPath = cleanPath.substring(0, cleanPath.length - 1);
    }

    final normalizedUri = Uri(
      scheme: parsed.scheme,
      userInfo: parsed.userInfo.isNotEmpty ? parsed.userInfo : null,
      host: parsed.host,
      port: effectivePort,
      path: cleanPath.isNotEmpty ? cleanPath : null,
    );

    String normalizedStr = normalizedUri.toString();
    if (normalizedStr.endsWith('/')) {
      normalizedStr = normalizedStr.substring(0, normalizedStr.length - 1);
    }
    return normalizedStr;
  }

  /// Initialize and load saved backend URL from persistent storage.
  static Future<void> init() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedUrl = prefs.getString(prefKey);
      if (savedUrl != null && savedUrl.trim().isNotEmpty) {
        _customUrl = normalizeUrl(savedUrl);
        if (kDebugMode) {
          debugPrint('[ApiConfig] Loaded persisted backend URL: $_customUrl');
        }
      }
    } catch (e) {
      if (kDebugMode) {
        debugPrint('[ApiConfig] Warning initializing SharedPreferences: $e');
      }
    } finally {
      _isInitialized = true;
    }
  }

  static bool get isInitialized => _isInitialized;

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

  /// Update backend base URL and persist it to device storage.
  static Future<void> setBaseUrl(String url) async {
    final cleanUrl = normalizeUrl(url);
    _customUrl = cleanUrl;
    if (kDebugMode) {
      debugPrint(
        '[ApiConfig] Base URL updated to: $_customUrl ($platformName)',
      );
    }
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(prefKey, cleanUrl);
    } catch (e) {
      if (kDebugMode) {
        debugPrint('[ApiConfig] Warning saving URL to SharedPreferences: $e');
      }
    }
  }

  /// Reset to platform auto-detected default and remove persistent override.
  static Future<void> resetToDefault() async {
    _customUrl = null;
    if (kDebugMode) {
      debugPrint(
        '[ApiConfig] Base URL reset to auto-detected default: $baseUrl',
      );
    }
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(prefKey);
    } catch (e) {
      if (kDebugMode) {
        debugPrint(
          '[ApiConfig] Warning clearing URL from SharedPreferences: $e',
        );
      }
    }
  }

  // Endpoints
  static String get health => '$baseUrl/api/health';
  static String get availableRecords => '$baseUrl/api/multimodal/records';
  static String get patientsOverview => '$baseUrl/api/multimodal/patients';
  static String recordDetail(String recordId) =>
      '$baseUrl/api/multimodal/records/$recordId';
  static String get analyze => '$baseUrl/api/multimodal/analyze';
  static String individualPredictions(String recordId) =>
      '$baseUrl/api/multimodal/predictions/$recordId';
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
