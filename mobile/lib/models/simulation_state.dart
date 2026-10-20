import 'patient.dart';
import 'alert.dart';

class SimulationState {
  final bool isRunning;
  final int currentStep;
  final int totalSteps;
  final int patientCount;
  final List<PatientOverview> patients;
  final List<ActiveAlert> activeAlerts;
  final List<PatientOverview> registeredPatients;

  SimulationState({
    required this.isRunning,
    required this.currentStep,
    required this.totalSteps,
    required this.patientCount,
    required this.patients,
    required this.activeAlerts,
    this.registeredPatients = const [],
  });

  factory SimulationState.fromJson(Map<String, dynamic> json) {
    var rawPatients = json['patients'] as List? ?? [];
    List<PatientOverview> patientsList = rawPatients
        .map((p) => PatientOverview.fromJson(Map<String, dynamic>.from(p)))
        .toList();

    var rawAlerts = json['active_alerts'] as List? ?? [];
    List<ActiveAlert> alertsList = rawAlerts
        .map((a) => ActiveAlert.fromJson(Map<String, dynamic>.from(a)))
        .toList();

    var rawRegistered = json['registered_patients'] as List? ?? [];
    List<PatientOverview> registeredList = rawRegistered
        .map((p) => PatientOverview.fromJson(Map<String, dynamic>.from(p)))
        .toList();

    return SimulationState(
      isRunning: json['is_running'] == true,
      currentStep: json['current_step'] is int ? json['current_step'] : 0,
      totalSteps: json['total_steps'] is int ? json['total_steps'] : 4,
      patientCount: json['patient_count'] is int
          ? json['patient_count']
          : patientsList.length,
      patients: patientsList,
      activeAlerts: alertsList,
      registeredPatients: registeredList,
    );
  }

  int get criticalCount =>
      patients.where((p) => p.priorityStatus == 'CRITICAL_PRIORITY').length;
  int get highPriorityCount =>
      patients.where((p) => p.priorityStatus == 'HIGH_PRIORITY').length;
  int get routineCount =>
      patients.where((p) => p.priorityStatus == 'ROUTINE_MONITORING').length;
  int get registeredCount => registeredPatients.length;
}
