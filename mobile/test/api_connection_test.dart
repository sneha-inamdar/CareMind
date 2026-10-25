import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:provider/provider.dart';

import 'package:mobile/config/api_config.dart';
import 'package:mobile/services/api_service.dart';
import 'package:mobile/providers/app_state.dart';
import 'package:mobile/screens/main_shell.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    ApiConfig.resetToDefault();
  });

  group('ApiConfig URL Normalization & Validation Tests', () {
    test('Normalizes IP without scheme or port to port 8000', () {
      final normalized = ApiConfig.normalizeUrl('192.168.227.150');
      expect(normalized, equals('http://192.168.227.150:8000'));
    });

    test('Normalizes http IP without port to port 8000', () {
      final normalized = ApiConfig.normalizeUrl('http://192.168.227.150');
      expect(normalized, equals('http://192.168.227.150:8000'));
    });

    test('Preserves full URL with port 8000', () {
      final normalized = ApiConfig.normalizeUrl('http://192.168.227.150:8000');
      expect(normalized, equals('http://192.168.227.150:8000'));
    });

    test('Preserves custom port if specified', () {
      final normalized = ApiConfig.normalizeUrl('http://192.168.227.150:8080');
      expect(normalized, equals('http://192.168.227.150:8080'));
    });

    test('Trims trailing slash from URL', () {
      final normalized = ApiConfig.normalizeUrl('http://192.168.227.150:8000/');
      expect(normalized, equals('http://192.168.227.150:8000'));
    });

    test('Strips redundant trailing /api from base URL', () {
      final normalized = ApiConfig.normalizeUrl(
        'http://192.168.227.150:8000/api',
      );
      expect(normalized, equals('http://192.168.227.150:8000'));

      final normalizedSlash = ApiConfig.normalizeUrl(
        'http://192.168.227.150:8000/api/',
      );
      expect(normalizedSlash, equals('http://192.168.227.150:8000'));
    });

    test('Handles localhost and emulator presets properly', () {
      expect(
        ApiConfig.normalizeUrl('localhost'),
        equals('http://localhost:8000'),
      );
      expect(
        ApiConfig.normalizeUrl('http://10.0.2.2:8000'),
        equals('http://10.0.2.2:8000'),
      );
    });

    test('Preserves HTTPS schemes and ports', () {
      expect(
        ApiConfig.normalizeUrl('https://caremind.org'),
        equals('https://caremind.org'),
      );
      expect(
        ApiConfig.normalizeUrl('https://caremind.org:8443'),
        equals('https://caremind.org:8443'),
      );
    });

    test('Throws FormatException on empty or invalid inputs', () {
      expect(() => ApiConfig.normalizeUrl(''), throwsA(isA<FormatException>()));
      expect(
        () => ApiConfig.normalizeUrl('   '),
        throwsA(isA<FormatException>()),
      );
    });
  });

  group('ApiConfig Persistence Tests', () {
    test('Persists and reloads URL from SharedPreferences', () async {
      SharedPreferences.setMockInitialValues({});
      await ApiConfig.setBaseUrl('192.168.227.150');
      expect(ApiConfig.baseUrl, equals('http://192.168.227.150:8000'));

      // Simulate app restart: re-initialize from storage
      await ApiConfig.init();
      expect(ApiConfig.baseUrl, equals('http://192.168.227.150:8000'));
    });

    test(
      'Reset clears persisted URL and reverts to platform default',
      () async {
        SharedPreferences.setMockInitialValues({
          ApiConfig.prefKey: 'http://192.168.227.150:8000',
        });
        await ApiConfig.init();
        expect(ApiConfig.isCustomUrlSet, isTrue);

        await ApiConfig.resetToDefault();
        expect(ApiConfig.isCustomUrlSet, isFalse);
      },
    );
  });

  group('Endpoint Consistency Tests', () {
    test('All endpoints use the configured base URL', () async {
      await ApiConfig.setBaseUrl('http://192.168.227.150:8000');

      expect(
        ApiConfig.health,
        equals('http://192.168.227.150:8000/api/health'),
      );
      expect(
        ApiConfig.simulationState,
        equals('http://192.168.227.150:8000/api/simulation/state'),
      );
      expect(
        ApiConfig.patientsOverview,
        equals('http://192.168.227.150:8000/api/multimodal/patients'),
      );
      expect(
        ApiConfig.activeAlerts,
        equals('http://192.168.227.150:8000/api/alerts'),
      );
      expect(
        ApiConfig.replayTimeline('REC-001'),
        equals('http://192.168.227.150:8000/api/multimodal/replay/REC-001'),
      );
      expect(
        ApiConfig.recordDetail('REC-001'),
        equals('http://192.168.227.150:8000/api/multimodal/records/REC-001'),
      );
    });
  });

  group('Diagnostic Error Formatting Tests', () {
    const testUrl = 'http://192.168.227.150:8000';

    test('Formats TimeoutException with server address and Wi-Fi guidance', () {
      final msg = ApiService.formatError(
        TimeoutException('Timed out'),
        testUrl,
      );
      expect(msg, contains('Connection timed out connecting to $testUrl'));
      expect(msg, contains('same Wi-Fi'));
    });

    test('Formats connection refused SocketException with port guidance', () {
      final msg = ApiService.formatError(
        const SocketException('OS Error: Connection refused, errno = 111'),
        testUrl,
      );
      expect(msg, contains('Connection refused at $testUrl'));
      expect(msg, contains('port 8000'));
    });

    test('Formats failed host lookup SocketException', () {
      final msg = ApiService.formatError(
        const SocketException('Failed host lookup: 192.168.227.150'),
        testUrl,
      );
      expect(msg, contains('Unable to resolve host "192.168.227.150"'));
    });

    test('Formats unreachable network route SocketException', () {
      final msg = ApiService.formatError(
        const SocketException('Network is unreachable'),
        testUrl,
      );
      expect(msg, contains('Network route unreachable'));
    });

    test('Formats FormatException for malformed responses', () {
      final msg = ApiService.formatError(
        const FormatException('Unexpected character at line 1'),
        testUrl,
      );
      expect(msg, contains('Malformed response from CareMind backend'));
    });

    test(
      'Rejects invalid candidate URL in checkHealth before making requests',
      () async {
        final result = await ApiService.checkHealth(customBaseUrl: '');
        expect(result.isSuccess, isFalse);
        expect(result.errorMessage, contains('Invalid URL format'));
      },
    );
  });

  group('AppState Connectivity & Banner Widget Tests', () {
    testWidgets(
      'Error banner displays formatted error and provides Retry & Configure buttons',
      (WidgetTester tester) async {
        final appState = AppState(autoLoad: false);
        appState.setErrorMessageForTesting(
          'Connection timed out connecting to http://192.168.227.150:8000. Verify backend is running and phone is on the same Wi-Fi.',
        );

        await tester.pumpWidget(
          ChangeNotifierProvider<AppState>.value(
            value: appState,
            child: const MaterialApp(home: MainShell()),
          ),
        );
        await tester.pump();

        expect(
          find.textContaining(
            'Connection timed out connecting to http://192.168.227.150:8000',
          ),
          findsOneWidget,
        );
        expect(find.text('Configure Server URL'), findsOneWidget);
        expect(find.text('Retry Connection'), findsOneWidget);
      },
    );

    testWidgets('Tracks connection status properly', (
      WidgetTester tester,
    ) async {
      final appState = AppState(autoLoad: false);
      expect(appState.isConnecting, isFalse);
    });
  });
}
