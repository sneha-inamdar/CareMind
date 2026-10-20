class ContributingFactor {
  final String factor;
  final String impact;
  final String detail;

  ContributingFactor({
    required this.factor,
    required this.impact,
    required this.detail,
  });

  factory ContributingFactor.fromJson(Map<String, dynamic> json) {
    return ContributingFactor(
      factor: json['factor']?.toString() ?? 'Unspecified factor',
      impact: json['impact']?.toString() ?? 'MODERATE',
      detail: json['detail']?.toString() ?? '',
    );
  }
}

class PatientVitals {
  final double? hr;
  final double? spo2;
  final double? resp;
  final double? map;
  final double? sbp;
  final double? dbp;
  final double? temp;

  PatientVitals({
    this.hr,
    this.spo2,
    this.resp,
    this.map,
    this.sbp,
    this.dbp,
    this.temp,
  });

  factory PatientVitals.fromJson(Map<String, dynamic> json) {
    double? parseDouble(dynamic val) {
      if (val == null) return null;
      if (val is num) return val.toDouble();
      return double.tryParse(val.toString());
    }

    return PatientVitals(
      hr: parseDouble(json['HR'] ?? json['hr'] ?? json['heart_rate']),
      spo2: parseDouble(
        json['SpO2'] ?? json['spo2'] ?? json['oxygen_saturation'],
      ),
      resp: parseDouble(
        json['Resp'] ?? json['resp'] ?? json['respiratory_rate'],
      ),
      map: parseDouble(
        json['MAP'] ?? json['map'] ?? json['mean_arterial_pressure'],
      ),
      sbp: parseDouble(json['SBP'] ?? json['sbp']),
      dbp: parseDouble(json['DBP'] ?? json['dbp']),
      temp: parseDouble(json['Temp'] ?? json['temp'] ?? json['temperature']),
    );
  }

  String get hrDisplay => hr != null ? '${hr!.round()} bpm' : 'N/A';
  String get spo2Display => spo2 != null ? '${spo2!.round()}%' : 'N/A';
  String get respDisplay => resp != null ? '${resp!.round()} /min' : 'N/A';
  String get mapDisplay => map != null ? '${map!.round()} mmHg' : 'N/A';
}

class PatientOverview {
  final String recordId;
  final dynamic subjectId;
  final dynamic stayId;
  final String bedId;
  final int windowIndex;
  final String timestamp;
  final double riskScore;
  final String riskCategory;
  final String riskTrendStatus;
  final double riskTrendDelta;
  final String priorityStatus;
  final PatientVitals vitals;
  final List<String> availableModalities;
  final String primaryAlert;
  final List<ContributingFactor> contributingFactors;
  final int activeAlertsCount;
  final String disclaimer;
  final String? name;
  final bool isMonitored;
  final String? monitoringStatus;
  final int? age;
  final String? sex;
  final String? notes;

  PatientOverview({
    required this.recordId,
    required this.subjectId,
    required this.stayId,
    required this.bedId,
    required this.windowIndex,
    required this.timestamp,
    required this.riskScore,
    required this.riskCategory,
    required this.riskTrendStatus,
    required this.riskTrendDelta,
    required this.priorityStatus,
    required this.vitals,
    required this.availableModalities,
    required this.primaryAlert,
    required this.contributingFactors,
    required this.activeAlertsCount,
    required this.disclaimer,
    this.name,
    this.isMonitored = true,
    this.monitoringStatus,
    this.age,
    this.sex,
    this.notes,
  });

  factory PatientOverview.fromJson(Map<String, dynamic> json) {
    double parseDouble(dynamic val, [double defaultVal = 0.0]) {
      if (val == null) return defaultVal;
      if (val is num) return val.toDouble();
      return double.tryParse(val.toString()) ?? defaultVal;
    }

    var rawFactors = json['contributing_factors'] as List? ?? [];
    List<ContributingFactor> factors = rawFactors
        .map((f) => ContributingFactor.fromJson(Map<String, dynamic>.from(f)))
        .toList();

    var rawModalities = json['available_modalities'] as List? ?? [];
    List<String> modalities = rawModalities.map((m) => m.toString()).toList();

    var vitalsJson = json['vitals'] ?? json['clinical_features'] ?? {};

    final isMonitored = json['is_monitored'] != false;
    final priority =
        json['priority_status']?.toString() ??
        (isMonitored ? 'ROUTINE_MONITORING' : 'UNMONITORED');

    return PatientOverview(
      recordId:
          json['record_id']?.toString() ?? json['patient_id']?.toString() ?? '',
      subjectId: json['subject_id'] ?? json['patient_id'] ?? 'N/A',
      stayId: json['stay_id'] ?? 'N/A',
      bedId:
          json['bed_id']?.toString() ??
          (isMonitored ? 'Bed ICU' : 'Unassigned Bed'),
      windowIndex: json['window_index'] is int ? json['window_index'] : 0,
      timestamp: json['timestamp']?.toString() ?? 'T+00:00',
      riskScore: parseDouble(json['risk_score']),
      riskCategory:
          json['risk_category']?.toString() ??
          (isMonitored ? 'LOW' : 'UNMONITORED'),
      riskTrendStatus: json['risk_trend_status']?.toString() ?? 'STABLE',
      riskTrendDelta: parseDouble(json['risk_trend_delta']),
      priorityStatus: priority,
      vitals: PatientVitals.fromJson(Map<String, dynamic>.from(vitalsJson)),
      availableModalities: modalities,
      primaryAlert:
          json['primary_alert']?.toString() ??
          (isMonitored
              ? 'Normal Parameters'
              : 'No physiological sensor connected'),
      contributingFactors: factors,
      activeAlertsCount: json['active_alerts_count'] is int
          ? json['active_alerts_count']
          : 0,
      disclaimer: json['disclaimer']?.toString() ?? '',
      name: json['name']?.toString(),
      isMonitored: isMonitored,
      monitoringStatus:
          json['monitoring_status']?.toString() ??
          (isMonitored
              ? 'Dataset Replay Active'
              : 'Registered — No Data Source Connected'),
      age: json['age'] is int
          ? json['age']
          : (json['age'] != null ? int.tryParse(json['age'].toString()) : null),
      sex: json['sex']?.toString(),
      notes: json['notes']?.toString(),
    );
  }

  String get formattedSubjectId {
    if (name != null && name!.trim().isNotEmpty) {
      return 'Patient #$subjectId • ${name!.trim()}';
    }
    return 'Patient #$subjectId';
  }

  String get priorityLabel {
    if (!isMonitored) {
      return 'MANUAL REGISTRATION';
    }
    switch (priorityStatus) {
      case 'CRITICAL_PRIORITY':
        return 'CRITICAL PRIORITY';
      case 'HIGH_PRIORITY':
        return 'HIGH PRIORITY';
      case 'ROUTINE_MONITORING':
      default:
        return 'ROUTINE MONITORING';
    }
  }
}
