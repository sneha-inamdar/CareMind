import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/patient.dart';
import 'package:mobile/providers/app_state.dart';
import 'package:mobile/screens/main_shell.dart';
import 'package:mobile/screens/patient_detail_screen.dart';
import 'package:mobile/widgets/patient_filter_bar.dart';
import 'package:provider/provider.dart';

void main() {
  group('Responsive Layout & Overflow Prevention Tests (320px width)', () {
    testWidgets(
      'MainShell error banner wraps without overflow on 320px width',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(320, 640);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(tester.view.resetPhysicalSize);

        final appState = AppState();
        // Simulate backend connectivity error to trigger error banner with action buttons
        appState.setErrorMessageForTesting(
          'Connection timeout connecting to FastAPI backend on http://192.168.1.100:8000',
        );

        await tester.pumpWidget(
          ChangeNotifierProvider<AppState>.value(
            value: appState,
            child: const MaterialApp(home: MainShell()),
          ),
        );
        await tester.pump();

        final err = tester.takeException();
        expect(err, isNull);
        expect(find.text('CareMind'), findsOneWidget);
        expect(find.text('Configure Server URL'), findsOneWidget);
        expect(find.text('Retry Connection'), findsOneWidget);
      },
    );

    testWidgets('PatientFilterBar renders without overflow on 320px width', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(320, 640);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final appState = AppState();

      await tester.pumpWidget(
        ChangeNotifierProvider<AppState>.value(
          value: appState,
          child: MaterialApp(
            home: Scaffold(
              body: PatientFilterBar(
                activeFilter: 'CRITICAL',
                totalCount: 22,
                filteredCount: 7,
                criticalCount: 7,
                highCount: 8,
                routineCount: 6,
                registeredCount: 1,
                onFilterChanged: (_) {},
                onResetFilter: () {},
                onAddPatient: () {},
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      final err = tester.takeException();
      expect(err, isNull);
      expect(find.textContaining('All Patients'), findsOneWidget);
      expect(find.text('+ Add Patient'), findsOneWidget);
    });

    testWidgets(
      'PatientDetailScreen bedside vitals grid wraps labels without overflow on 320px width',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(320, 640);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(tester.view.resetPhysicalSize);

        final patientOverview = PatientOverview.fromJson({
          'record_id': 'REC-001',
          'subject_id': '10001234',
          'stay_id': '30005678',
          'bed_id': 'ICU-01',
          'window_index': 0,
          'timestamp': '2026-10-14T10:00:00Z',
          'risk_score': 88.0,
          'risk_category': 'CRITICAL',
          'risk_trend_status': 'STABLE',
          'risk_trend_delta': 0.0,
          'priority_status': 'CRITICAL_PRIORITY',
          'vitals': {
            'heart_rate': 115.0,
            'spo2': 91.0,
            'respiratory_rate': 26.0,
            'mean_arterial_pressure': 60.0,
          },
          'available_modalities': ['ecg', 'ppg'],
          'primary_alert': 'Critical deterioration predicted',
          'contributing_factors': [],
          'active_alerts_count': 1,
          'disclaimer': 'Research tool only',
          'is_monitored': true,
          'monitoring_status': 'monitored',
        });

        await tester.pumpWidget(
          MaterialApp(
            home: PatientDetailScreen(patient: patientOverview, onBack: () {}),
          ),
        );
        await tester.pump();

        final err = tester.takeException();
        expect(err, isNull);
        expect(find.text('Oxygen Saturation (SpO2)'), findsOneWidget);
        expect(find.text('Mean Arterial Pressure (MAP)'), findsOneWidget);
        expect(find.text('Heart Rate (HR)'), findsOneWidget);
        expect(find.text('Respiratory Rate'), findsOneWidget);
      },
    );
  });
}
