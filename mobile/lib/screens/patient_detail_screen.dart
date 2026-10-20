import 'package:flutter/material.dart';

import '../models/patient.dart';
import '../models/record_detail.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/waveform_painter.dart';

class PatientDetailScreen extends StatefulWidget {
  final PatientOverview patient;
  final VoidCallback onBack;

  const PatientDetailScreen({
    super.key,
    required this.patient,
    required this.onBack,
  });

  @override
  State<PatientDetailScreen> createState() => _PatientDetailScreenState();
}

class _PatientDetailScreenState extends State<PatientDetailScreen> {
  bool _isLoadingTimeline = true;
  RecordReplayTimeline? _timeline;
  int _selectedWindowIdx = 0;
  bool _isDiagnosticsExpanded = false;

  @override
  void initState() {
    super.initState();
    _loadTimeline();
  }

  Future<void> _loadTimeline() async {
    final result = await ApiService.getReplayTimeline(widget.patient.recordId);
    if (mounted) {
      setState(() {
        _isLoadingTimeline = false;
        if (result.isSuccess) {
          _timeline = result.data;
          _selectedWindowIdx = widget.patient.windowIndex;
        }
      });
    }
  }

  Color _getPriorityColor(String priority) {
    switch (priority) {
      case 'CRITICAL_PRIORITY':
        return AppTheme.critical;
      case 'HIGH_PRIORITY':
        return AppTheme.high;
      case 'ROUTINE_MONITORING':
      default:
        return AppTheme.routine;
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.patient;
    final prioColor = _getPriorityColor(p.priorityStatus);

    WindowDetail? currentWin;
    if (_timeline != null && _timeline!.timeline.isNotEmpty) {
      final safeIdx = _selectedWindowIdx.clamp(
        0,
        _timeline!.timeline.length - 1,
      );
      currentWin = _timeline!.timeline[safeIdx];
    }

    final hasEcg = p.availableModalities.contains('ECG');
    final hasPpg = p.availableModalities.contains('PPG');
    final hasAbp = p.availableModalities.contains('ABP');

    final ecgSamples = currentWin?.waveformSamples['ecg'] ?? [];
    final ppgSamples = currentWin?.waveformSamples['ppg'] ?? [];
    final abpSamples = currentWin?.waveformSamples['abp'] ?? [];

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: widget.onBack,
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(p.bedId, overflow: TextOverflow.ellipsis),
            Text(
              p.formattedSubjectId,
              style: const TextStyle(
                fontSize: 12,
                color: AppTheme.textSecondary,
                fontWeight: FontWeight.normal,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
        actions: [
          Container(
            margin: const EdgeInsets.only(right: 16),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: prioColor.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Text(
              p.priorityLabel,
              style: TextStyle(
                color: prioColor,
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top Risk Callout & Category Banner
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.border),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.02),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    Wrap(
                      alignment: WrapAlignment.spaceBetween,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: 8,
                      runSpacing: 10,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'CareMind Risk Score',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                                color: AppTheme.textSecondary,
                              ),
                            ),
                            const SizedBox(height: 4),
                            RichText(
                              text: TextSpan(
                                children: [
                                  TextSpan(
                                    text: p.riskScore.toStringAsFixed(1),
                                    style: TextStyle(
                                      fontSize: 32,
                                      fontWeight: FontWeight.w900,
                                      color: prioColor,
                                    ),
                                  ),
                                  const TextSpan(
                                    text: ' / 100',
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w600,
                                      color: AppTheme.textSecondary,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 8,
                          ),
                          decoration: BoxDecoration(
                            color: AppTheme.background,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.border),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Category: ${p.riskCategory}',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w800,
                                  color: prioColor,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                'Trend: ${p.riskTrendStatus}',
                                style: const TextStyle(
                                  fontSize: 10,
                                  color: AppTheme.textSecondary,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    LinearProgressIndicator(
                      value: (p.riskScore / 100.0).clamp(0.0, 1.0),
                      backgroundColor: AppTheme.border,
                      color: prioColor,
                      minHeight: 6,
                      borderRadius: BorderRadius.circular(3),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      p.disclaimer,
                      style: const TextStyle(
                        fontSize: 10,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Window Selection Timeline Bar
              if (_timeline != null && _timeline!.timeline.isNotEmpty) ...[
                const Text(
                  'Continuous Timeline Replay Window',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 8),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: List.generate(_timeline!.timeline.length, (idx) {
                      final win = _timeline!.timeline[idx];
                      final isSelected = idx == _selectedWindowIdx;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(
                          label: Text(
                            'Window $idx (${win.timestamp.split('•').last.trim()})',
                          ),
                          selected: isSelected,
                          onSelected: (_) {
                            setState(() {
                              _selectedWindowIdx = idx;
                            });
                          },
                          selectedColor: AppTheme.primary,
                          labelStyle: TextStyle(
                            color: isSelected
                                ? Colors.white
                                : AppTheme.textPrimary,
                            fontSize: 11,
                            fontWeight: isSelected
                                ? FontWeight.bold
                                : FontWeight.normal,
                          ),
                        ),
                      );
                    }),
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // Continuous Waveform Panels (ECG, PPG, ABP)
              const Text(
                'Continuous Waveform Signals',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(height: 8),

              if (_isLoadingTimeline)
                const ContainerLoadingWaveform()
              else ...[
                // ECG Channel
                WaveformCard(
                  title: 'ECG Lead II',
                  unit: 'mV',
                  samples: ecgSamples,
                  color: AppTheme.ecgColor,
                  isMonitored: hasEcg,
                ),

                // PPG Channel
                WaveformCard(
                  title: 'PPG Pleth',
                  unit: 'relative',
                  samples: ppgSamples,
                  color: AppTheme.ppgColor,
                  isMonitored: hasPpg,
                ),

                // ABP Channel
                WaveformCard(
                  title: 'Arterial Blood Pressure (ABP)',
                  unit: 'mmHg',
                  samples: abpSamples,
                  color: AppTheme.abpColor,
                  isMonitored: hasAbp,
                ),
              ],
              const SizedBox(height: 16),

              // Bedside Vitals Grid (Responsive Two-Column / Single-Column with natural vertical expansion)
              const Text(
                'Observed Bedside Vitals',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.surface,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppTheme.border),
                ),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final isVeryNarrow = constraints.maxWidth < 320;

                    final hrTile = _DetailVitalTile(
                      label: 'Heart Rate (HR)',
                      value: p.vitals.hrDisplay,
                      isAlert: (p.vitals.hr ?? 0) > 100,
                    );
                    final spo2Tile = _DetailVitalTile(
                      label: 'Oxygen Saturation (SpO2)',
                      value: p.vitals.spo2Display,
                      isAlert: (p.vitals.spo2 ?? 100) < 95,
                    );
                    final respTile = _DetailVitalTile(
                      label: 'Respiratory Rate',
                      value: p.vitals.respDisplay,
                      isAlert: (p.vitals.resp ?? 0) > 20,
                    );
                    final mapTile = _DetailVitalTile(
                      label: 'Mean Arterial Pressure (MAP)',
                      value: p.vitals.mapDisplay,
                      isAlert: (p.vitals.map ?? 80) < 65,
                    );

                    if (isVeryNarrow) {
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          hrTile,
                          const SizedBox(height: 8),
                          spo2Tile,
                          const SizedBox(height: 8),
                          respTile,
                          const SizedBox(height: 8),
                          mapTile,
                        ],
                      );
                    }

                    return Column(
                      children: [
                        IntrinsicHeight(
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Expanded(child: hrTile),
                              const SizedBox(width: 10),
                              Expanded(child: spo2Tile),
                            ],
                          ),
                        ),
                        const SizedBox(height: 10),
                        IntrinsicHeight(
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Expanded(child: respTile),
                              const SizedBox(width: 10),
                              Expanded(child: mapTile),
                            ],
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
              const SizedBox(height: 16),

              // Why Is This Patient Prioritized? (Explainability)
              const Text(
                'Why is this patient prioritized?',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.surface,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppTheme.border),
                ),
                child: p.contributingFactors.isEmpty
                    ? const Text(
                        'No active physiological risk factors detected.',
                      )
                    : Column(
                        children: p.contributingFactors.map((f) {
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 8,
                                    vertical: 3,
                                  ),
                                  decoration: BoxDecoration(
                                    color: f.impact == 'HIGH'
                                        ? AppTheme.criticalBg
                                        : AppTheme.highBg,
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    f.impact,
                                    style: TextStyle(
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                      color: f.impact == 'HIGH'
                                          ? AppTheme.critical
                                          : AppTheme.high,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        f.factor,
                                        style: const TextStyle(
                                          fontSize: 13,
                                          fontWeight: FontWeight.bold,
                                          color: AppTheme.textPrimary,
                                        ),
                                      ),
                                      Text(
                                        f.detail,
                                        style: const TextStyle(
                                          fontSize: 11,
                                          color: AppTheme.textSecondary,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      ),
              ),
              const SizedBox(height: 16),

              // Secondary Technical Diagnostics Expandable Section
              ExpansionTile(
                title: const Text(
                  '⚙️ Secondary Model Diagnostics',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.textSecondary,
                  ),
                ),
                childrenPadding: const EdgeInsets.all(12),
                initiallyExpanded: _isDiagnosticsExpanded,
                onExpansionChanged: (val) =>
                    setState(() => _isDiagnosticsExpanded = val),
                children: [
                  Text(
                    'Record ID: ${p.recordId}',
                    style: const TextStyle(fontSize: 12),
                  ),
                  Text(
                    'Subject ID: ${p.subjectId}',
                    style: const TextStyle(fontSize: 12),
                  ),
                  Text(
                    'Stay ID: ${p.stayId}',
                    style: const TextStyle(fontSize: 12),
                  ),
                  Text(
                    'Available Modalities: ${p.availableModalities.join(', ')}',
                    style: const TextStyle(fontSize: 12),
                  ),
                  const Text(
                    'Data Provenance: Real MIMIC-IV Clinical & Waveform Database',
                    style: TextStyle(fontSize: 12),
                  ),
                ],
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}

class _DetailVitalTile extends StatelessWidget {
  final String label;
  final String value;
  final bool isAlert;

  const _DetailVitalTile({
    required this.label,
    required this.value,
    required this.isAlert,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 64),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: isAlert ? AppTheme.criticalBg : AppTheme.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isAlert
              ? AppTheme.critical.withValues(alpha: 0.3)
              : AppTheme.border,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: isAlert ? AppTheme.critical : AppTheme.textSecondary,
              height: 1.2,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w900,
              color: isAlert ? AppTheme.critical : AppTheme.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}

class ContainerLoadingWaveform extends StatelessWidget {
  const ContainerLoadingWaveform({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 120,
      width: double.infinity,
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(10),
      ),
      child: const Center(
        child: CircularProgressIndicator(color: AppTheme.primary),
      ),
    );
  }
}
