import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class OverviewSummaryCards extends StatelessWidget {
  final int totalMonitored;
  final int criticalCount;
  final int highPriorityCount;
  final int activeAlertsCount;
  final Function(String filter) onFilterSelect;
  final VoidCallback onAlertsSelect;

  const OverviewSummaryCards({
    super.key,
    required this.totalMonitored,
    required this.criticalCount,
    required this.highPriorityCount,
    required this.activeAlertsCount,
    required this.onFilterSelect,
    required this.onAlertsSelect,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _SummaryCard(
                title: 'MONITORED',
                value: '$totalMonitored',
                label: 'Active Beds',
                accentColor: AppTheme.primary,
                bgColor: AppTheme.primaryLight,
                icon: Icons.monitor_heart_outlined,
                onTap: () => onFilterSelect('ALL'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _SummaryCard(
                title: 'CRITICAL',
                value: '$criticalCount',
                label: 'Risk ≥ 75.0',
                accentColor: AppTheme.critical,
                bgColor: AppTheme.criticalBg,
                icon: Icons.warning_amber_rounded,
                onTap: () => onFilterSelect('CRITICAL'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _SummaryCard(
                title: 'HIGH PRIORITY',
                value: '$highPriorityCount',
                label: 'Risk 50–74.9',
                accentColor: AppTheme.high,
                bgColor: AppTheme.highBg,
                icon: Icons.priority_high_rounded,
                onTap: () => onFilterSelect('HIGH'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _SummaryCard(
                title: 'ACTIVE ALERTS',
                value: '$activeAlertsCount',
                label: 'Unresolved',
                accentColor: Colors.purple.shade700,
                bgColor: Colors.purple.shade50,
                icon: Icons.notifications_active_outlined,
                onTap: onAlertsSelect,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final String title;
  final String value;
  final String label;
  final Color accentColor;
  final Color bgColor;
  final IconData icon;
  final VoidCallback onTap;

  const _SummaryCard({
    required this.title,
    required this.value,
    required this.label,
    required this.accentColor,
    required this.bgColor,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppTheme.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppTheme.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: TextStyle(
                        color: accentColor,
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: bgColor,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(icon, size: 16, color: accentColor),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                value,
                style: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  height: 1.1,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                label,
                style: const TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
