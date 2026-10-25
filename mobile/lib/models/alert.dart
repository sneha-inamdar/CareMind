class ActiveAlert {
  final String alertId;
  final String severity;
  final String patientId;
  final String recordId;
  final String bedId;
  final String alertType;
  final String title;
  final String message;
  final String timestamp;
  final String status;
  final Map<String, dynamic>? evidence;

  ActiveAlert({
    required this.alertId,
    required this.severity,
    required this.patientId,
    required this.recordId,
    required this.bedId,
    required this.alertType,
    required this.title,
    required this.message,
    required this.timestamp,
    required this.status,
    this.evidence,
  });

  factory ActiveAlert.fromJson(Map<String, dynamic> json) {
    return ActiveAlert(
      alertId:
          json['alert_id']?.toString() ??
          'alert_${DateTime.now().millisecondsSinceEpoch}',
      severity: json['severity']?.toString() ?? 'MODERATE',
      patientId:
          (json['patient_id'] ?? json['subject_id'])?.toString() ?? 'N/A',
      recordId: json['record_id']?.toString() ?? '',
      bedId: json['bed_id']?.toString() ?? 'Bed ICU',
      alertType: json['alert_type']?.toString() ?? 'PHYSIOLOGICAL_ABNORMALITY',
      title:
          json['title']?.toString() ??
          json['alert_type']?.toString() ??
          'Alert',
      message:
          json['message']?.toString() ?? json['description']?.toString() ?? '',
      timestamp: json['timestamp']?.toString() ?? 'Just now',
      status: json['status']?.toString() ?? 'ACTIVE',
      evidence: json['evidence'] is Map
          ? Map<String, dynamic>.from(json['evidence'])
          : null,
    );
  }

  String get formattedPatientTag => 'Patient #$patientId ($bedId)';
}
