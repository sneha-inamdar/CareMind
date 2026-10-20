import 'patient.dart';

class WindowDetail {
  final int windowIndex;
  final String timestamp;
  final double riskScore;
  final String riskCategory;
  final PatientVitals vitals;
  final Map<String, List<double>> waveformSamples;
  final List<String> availableModalities;
  final List<ContributingFactor> contributingFactors;
  final String disclaimer;

  WindowDetail({
    required this.windowIndex,
    required this.timestamp,
    required this.riskScore,
    required this.riskCategory,
    required this.vitals,
    required this.waveformSamples,
    required this.availableModalities,
    required this.contributingFactors,
    required this.disclaimer,
  });

  factory WindowDetail.fromJson(Map<String, dynamic> json) {
    double parseDouble(dynamic val, [double defaultVal = 0.0]) {
      if (val == null) return defaultVal;
      if (val is num) return val.toDouble();
      return double.tryParse(val.toString()) ?? defaultVal;
    }

    var vitalsJson = json['clinical_features'] ?? json['vitals'] ?? {};
    var rawFactors = json['contributing_factors'] as List? ?? [];
    List<ContributingFactor> factors = rawFactors
        .map((f) => ContributingFactor.fromJson(Map<String, dynamic>.from(f)))
        .toList();

    var rawModalities = json['available_modalities'] as List? ?? [];
    List<String> modalities = rawModalities.map((m) => m.toString()).toList();

    // Extract waveform samples
    Map<String, List<double>> waveforms = {};
    var rawSamples = json['waveform_samples'];
    if (rawSamples is Map) {
      rawSamples.forEach((key, value) {
        if (value is List) {
          waveforms[key.toString().toLowerCase()] = value
              .map((v) => parseDouble(v, 0.0))
              .toList();
        }
      });
    }

    return WindowDetail(
      windowIndex: json['window_index'] is int ? json['window_index'] : 0,
      timestamp: json['timestamp']?.toString() ?? 'T+00:00',
      riskScore: parseDouble(json['risk_score']),
      riskCategory: json['risk_category']?.toString() ?? 'LOW',
      vitals: PatientVitals.fromJson(Map<String, dynamic>.from(vitalsJson)),
      waveformSamples: waveforms,
      availableModalities: modalities,
      contributingFactors: factors,
      disclaimer: json['disclaimer']?.toString() ?? '',
    );
  }
}

class RecordReplayTimeline {
  final String recordId;
  final int totalWindows;
  final List<WindowDetail> timeline;

  RecordReplayTimeline({
    required this.recordId,
    required this.totalWindows,
    required this.timeline,
  });

  factory RecordReplayTimeline.fromJson(Map<String, dynamic> json) {
    var rawTimeline = json['timeline'] as List? ?? [];
    List<WindowDetail> windows = rawTimeline
        .map((w) => WindowDetail.fromJson(Map<String, dynamic>.from(w)))
        .toList();

    return RecordReplayTimeline(
      recordId: json['record_id']?.toString() ?? '',
      totalWindows: json['total_windows'] is int
          ? json['total_windows']
          : windows.length,
      timeline: windows,
    );
  }
}
