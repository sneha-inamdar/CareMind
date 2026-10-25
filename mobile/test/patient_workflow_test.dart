import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/patient.dart';
import 'package:mobile/providers/app_state.dart';
import 'package:mobile/widgets/add_patient_modal.dart';
import 'package:mobile/widgets/patient_card.dart';

void main() {
  group('Patient Workflow & AddPatientModal Tests', () {
    testWidgets(
      'renders AddPatientModal in bottom sheet and validates required fields',
      (WidgetTester tester) async {
        final appState = AppState();

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: SizedBox(
                height: 800,
                width: 400,
                child: AddPatientModal(appState: appState),
              ),
            ),
          ),
        );
        await tester.pump();

        // Verify tabs exist
        expect(find.text('Manual EMR Register'), findsOneWidget);
        expect(find.text('MIMIC Waveform Cohort'), findsOneWidget);

        // Verify form is rendered
        expect(find.text('Register Patient'), findsOneWidget);

        // Scroll to submit button and tap
        final submitButton = find.widgetWithText(
          ElevatedButton,
          'Register Patient',
        );
        await tester.scrollUntilVisible(
          submitButton,
          50,
          scrollable: find.byType(Scrollable).last,
        );
        await tester.tap(submitButton);
        await tester.pump();

        // Validation message should be visible
        expect(find.text('Patient name is required.'), findsOneWidget);
        expect(find.text('Patient ID is required.'), findsOneWidget);
      },
    );

    testWidgets('renders PatientCard for monitored MIMIC-IV patient', (
      WidgetTester tester,
    ) async {
      final monitoredPatient = PatientOverview.fromJson({
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
          home: Scaffold(
            body: PatientCard(patient: monitoredPatient, onInspect: () {}),
          ),
        ),
      );

      expect(find.text('ICU-01'), findsOneWidget);
      expect(find.text('Patient #10001234'), findsOneWidget);
      expect(find.text('88.0'), findsOneWidget);
      expect(find.text('CRITICAL PRIORITY'), findsOneWidget);
      expect(find.text('115 bpm'), findsOneWidget);
      expect(find.text('91%'), findsOneWidget);
    });

    testWidgets(
      'renders PatientCard for unmonitored registered patient with badge',
      (WidgetTester tester) async {
        final registeredPatient = PatientOverview.fromJson({
          'record_id': 'REC-REG-99',
          'subject_id': 'P-REG-99',
          'stay_id': 'P-REG-99',
          'name': 'John Doe',
          'bed_id': 'ICU-09',
          'window_index': 0,
          'timestamp': '2026-10-14T10:00:00Z',
          'risk_score': 0.0,
          'risk_category': 'PENDING',
          'risk_trend_status': 'STABLE',
          'risk_trend_delta': 0.0,
          'priority_status': 'MANUAL_REGISTRATION',
          'vitals': {},
          'available_modalities': [],
          'primary_alert': '',
          'contributing_factors': [],
          'active_alerts_count': 0,
          'disclaimer': 'Research tool only',
          'is_monitored': false,
          'monitoring_status': 'registered_unmonitored',
          'age': 62,
          'sex': 'M',
          'notes': 'Post-op observation',
        });

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: PatientCard(patient: registeredPatient, onInspect: () {}),
            ),
          ),
        );

        expect(find.text('ICU-09'), findsOneWidget);
        expect(find.text('Patient #P-REG-99 • John Doe'), findsOneWidget);
        expect(find.text('MANUAL REGISTRATION'), findsOneWidget);
        expect(find.text('Post-op observation'), findsOneWidget);
      },
    );
  });
}
