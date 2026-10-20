import 'package:flutter/material.dart';

import '../models/patient.dart';
import '../theme/app_theme.dart';

class PatientCard extends StatelessWidget {
  final PatientOverview patient;
  final VoidCallback onInspect;
  final VoidCallback? onRemove;

  const PatientCard({
    super.key,
    required this.patient,
    required this.onInspect,
    this.onRemove,
  });

  Color _getPriorityColor(String priority) {
    switch (priority) {
      case 'CRITICAL_PRIORITY':
        return AppTheme.critical;
      case 'HIGH_PRIORITY':
        return AppTheme.high;
      case 'ROUTINE_MONITORING':
        return AppTheme.routine;
      case 'UNMONITORED':
      default:
        return AppTheme.textSecondary;
    }
  }

  Color _getPriorityBg(String priority) {
    switch (priority) {
      case 'CRITICAL_PRIORITY':
        return AppTheme.criticalBg;
      case 'HIGH_PRIORITY':
        return AppTheme.highBg;
      case 'ROUTINE_MONITORING':
        return AppTheme.routineBg;
      case 'UNMONITORED':
      default:
        return const Color(0xFFF1F5F9);
    }
  }

  String _getTrendIcon(String trend) {
    switch (trend) {
      case 'ESCALATING':
        return '↑ Escalating';
      case 'IMPROVING':
        return '↓ Improving';
      case 'STABLE':
      default:
        return '→ Stable';
    }
  }

  void _confirmRemoval(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          children: [
            const Icon(Icons.warning_amber_rounded, color: AppTheme.critical),
            const SizedBox(width: 8),
            const Expanded(
              child: Text(
                'Remove from Roster?',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        content: Text(
          'Are you sure you want to remove ${patient.formattedSubjectId} (${patient.bedId}) from the ICU monitoring roster?\n\nHistorical records will remain preserved in database.',
          style: const TextStyle(fontSize: 13, color: AppTheme.textPrimary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              onRemove?.call();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.critical,
              foregroundColor: Colors.white,
            ),
            child: const Text('Confirm Remove'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final prioColor = _getPriorityColor(patient.priorityStatus);
    final prioBg = _getPriorityBg(patient.priorityStatus);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Row: Bed ID, Subject ID & Priority Badge
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        patient.bedId,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.textPrimary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        patient.formattedSubjectId,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppTheme.textSecondary,
                          fontWeight: FontWeight.w500,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 5,
                  ),
                  decoration: BoxDecoration(
                    color: prioBg,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: prioColor.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    patient.priorityLabel,
                    style: TextStyle(
                      color: prioColor,
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.3,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            if (!patient.isMonitored) ...[
              // Registered Patient Profile (No Waveform Data)
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.background,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppTheme.border),
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AppTheme.surface,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: const Icon(
                        Icons.person_outline_rounded,
                        color: AppTheme.primary,
                        size: 22,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                patient.name ?? 'Registered Patient',
                                style: const TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w800,
                                  color: AppTheme.textPrimary,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                              if (patient.age != null) ...[
                                const SizedBox(width: 6),
                                Text(
                                  '(${patient.age}y${patient.sex != null && patient.sex!.isNotEmpty ? ', ${patient.sex}' : ''})',
                                  style: const TextStyle(
                                    fontSize: 11,
                                    color: AppTheme.textSecondary,
                                  ),
                                ),
                              ],
                            ],
                          ),
                          const SizedBox(height: 2),
                          Text(
                            patient.notes != null &&
                                    patient.notes!.trim().isNotEmpty
                                ? patient.notes!
                                : 'No continuous waveform telemetry connected yet.',
                            style: const TextStyle(
                              fontSize: 11,
                              color: AppTheme.textSecondary,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              if (onRemove != null)
                SizedBox(
                  width: double.infinity,
                  height: 44,
                  child: OutlinedButton.icon(
                    onPressed: () => _confirmRemoval(context),
                    icon: const Icon(
                      Icons.delete_outline_rounded,
                      size: 16,
                      color: AppTheme.critical,
                    ),
                    label: const Text(
                      'Remove from Roster',
                      style: TextStyle(
                        color: AppTheme.critical,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: AppTheme.critical),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                ),
            ] else ...[
              // Monitored Patient: CareMind Risk Score & Trend
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.background,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppTheme.border),
                ),
                child: Row(
                  children: [
                    // Risk Score Callout
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'CareMind Risk Score',
                            style: TextStyle(
                              fontSize: 11,
                              color: AppTheme.textSecondary,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.baseline,
                            textBaseline: TextBaseline.alphabetic,
                            children: [
                              Text(
                                patient.riskScore.toStringAsFixed(1),
                                style: TextStyle(
                                  fontSize: 24,
                                  fontWeight: FontWeight.w900,
                                  color: prioColor,
                                ),
                              ),
                              const Text(
                                ' / 100',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: AppTheme.textSecondary,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    // Trend Badge
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: AppTheme.surface,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: Column(
                        children: [
                          Text(
                            _getTrendIcon(patient.riskTrendStatus),
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: patient.riskTrendStatus == 'ESCALATING'
                                  ? AppTheme.critical
                                  : AppTheme.textSecondary,
                            ),
                          ),
                          if (patient.riskTrendDelta != 0)
                            Text(
                              '${patient.riskTrendDelta > 0 ? '+' : ''}${patient.riskTrendDelta.toStringAsFixed(1)}',
                              style: const TextStyle(
                                fontSize: 10,
                                color: AppTheme.textSecondary,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),

              // Vitals Grid: HR, SpO2, Resp, MAP
              Row(
                children: [
                  _VitalItem(
                    label: 'HR',
                    value: patient.vitals.hrDisplay,
                    isAlert: (patient.vitals.hr ?? 0) > 100,
                  ),
                  _VitalItem(
                    label: 'SpO2',
                    value: patient.vitals.spo2Display,
                    isAlert: (patient.vitals.spo2 ?? 100) < 95,
                  ),
                  _VitalItem(
                    label: 'Resp',
                    value: patient.vitals.respDisplay,
                    isAlert: (patient.vitals.resp ?? 0) > 20,
                  ),
                  _VitalItem(
                    label: 'MAP',
                    value: patient.vitals.mapDisplay,
                    isAlert: (patient.vitals.map ?? 80) < 65,
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Modalities & Alerts Row
              Row(
                children: [
                  Expanded(
                    child: Wrap(
                      spacing: 4,
                      runSpacing: 4,
                      children: patient.availableModalities.map((mod) {
                        return Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: AppTheme.primaryLight,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            mod,
                            style: const TextStyle(
                              fontSize: 10,
                              color: AppTheme.primary,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                  if (patient.activeAlertsCount > 0)
                    Container(
                      margin: const EdgeInsets.only(left: 6),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: AppTheme.criticalBg,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        '${patient.activeAlertsCount} Alert${patient.activeAlertsCount > 1 ? 's' : ''}',
                        style: const TextStyle(
                          fontSize: 11,
                          color: AppTheme.critical,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),

              // Action Buttons Row
              Row(
                children: [
                  Expanded(
                    child: SizedBox(
                      height: 44,
                      child: ElevatedButton.icon(
                        onPressed: onInspect,
                        icon: const Icon(Icons.analytics_outlined, size: 16),
                        label: const Text(
                          'Inspect Patient',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.primary,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          elevation: 0,
                        ),
                      ),
                    ),
                  ),
                  if (onRemove != null) ...[
                    const SizedBox(width: 8),
                    SizedBox(
                      height: 44,
                      width: 44,
                      child: IconButton.outlined(
                        onPressed: () => _confirmRemoval(context),
                        icon: const Icon(
                          Icons.delete_outline_rounded,
                          size: 18,
                          color: AppTheme.critical,
                        ),
                        tooltip: 'Remove Patient',
                        style: IconButton.styleFrom(
                          side: const BorderSide(color: AppTheme.border),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _VitalItem extends StatelessWidget {
  final String label;
  final String value;
  final bool isAlert;

  const _VitalItem({
    required this.label,
    required this.value,
    this.isAlert = false,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
        margin: const EdgeInsets.symmetric(horizontal: 2),
        decoration: BoxDecoration(
          color: isAlert ? AppTheme.criticalBg : AppTheme.surface,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isAlert
                ? AppTheme.critical.withValues(alpha: 0.3)
                : AppTheme.border,
          ),
        ),
        child: Column(
          children: [
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(
                label,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  color: isAlert ? AppTheme.critical : AppTheme.textSecondary,
                ),
              ),
            ),
            const SizedBox(height: 2),
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(
                value,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  color: isAlert ? AppTheme.critical : AppTheme.textPrimary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
