import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class PatientFilterBar extends StatelessWidget {
  final String activeFilter;
  final int totalCount;
  final int filteredCount;
  final int criticalCount;
  final int highCount;
  final int routineCount;
  final int registeredCount;
  final Function(String filter) onFilterChanged;
  final VoidCallback onResetFilter;
  final VoidCallback onAddPatient;

  const PatientFilterBar({
    super.key,
    required this.activeFilter,
    required this.totalCount,
    required this.filteredCount,
    this.criticalCount = 0,
    this.highCount = 0,
    this.routineCount = 0,
    this.registeredCount = 0,
    required this.onFilterChanged,
    required this.onResetFilter,
    required this.onAddPatient,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Top Action Row: Title and + Add Patient Button
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'ICU Patient Roster',
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    '$totalCount total beds ($registeredCount unmonitored EMR)',
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppTheme.textSecondary,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            // Prominent + Add Patient Button with comfortable 48px touch target
            SizedBox(
              height: 44,
              child: ElevatedButton.icon(
                onPressed: onAddPatient,
                icon: const Icon(Icons.person_add_alt_1_rounded, size: 18),
                label: const Text(
                  '+ Add Patient',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

        // Filter Chips Row (Horizontally Scrollable)
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              _FilterChip(
                label: 'All Patients ($totalCount)',
                isSelected: activeFilter == 'ALL',
                onTap: () => onFilterChanged('ALL'),
              ),
              const SizedBox(width: 6),
              _FilterChip(
                label: criticalCount > 0
                    ? 'Critical ($criticalCount)'
                    : 'Critical',
                isSelected: activeFilter == 'CRITICAL',
                color: AppTheme.critical,
                onTap: () => onFilterChanged('CRITICAL'),
              ),
              const SizedBox(width: 6),
              _FilterChip(
                label: highCount > 0
                    ? 'High Priority ($highCount)'
                    : 'High Priority',
                isSelected: activeFilter == 'HIGH',
                color: AppTheme.high,
                onTap: () => onFilterChanged('HIGH'),
              ),
              const SizedBox(width: 6),
              _FilterChip(
                label: routineCount > 0 ? 'Routine ($routineCount)' : 'Routine',
                isSelected: activeFilter == 'ROUTINE',
                color: AppTheme.routine,
                onTap: () => onFilterChanged('ROUTINE'),
              ),
              if (registeredCount > 0) ...[
                const SizedBox(width: 6),
                _FilterChip(
                  label: 'Registered ($registeredCount)',
                  isSelected: activeFilter == 'REGISTERED',
                  color: Colors.blueGrey,
                  onTap: () => onFilterChanged('REGISTERED'),
                ),
              ],
            ],
          ),
        ),

        // Active Filter Banner if filtered (Never overlaps count and reset action)
        if (activeFilter != 'ALL') ...[
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: AppTheme.primaryLight,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: AppTheme.primary.withValues(alpha: 0.2),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    'Showing $filteredCount $activeFilter Priority Patient${filteredCount == 1 ? '' : 's'}',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.primary,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                InkWell(
                  onTap: onResetFilter,
                  child: const Padding(
                    padding: EdgeInsets.symmetric(vertical: 2, horizontal: 4),
                    child: Text(
                      'Reset Filter',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.primary,
                        decoration: TextDecoration.underline,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool isSelected;
  final Color? color;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.isSelected,
    this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final activeColor = color ?? AppTheme.primary;

    return ChoiceChip(
      label: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
          color: isSelected ? Colors.white : AppTheme.textPrimary,
        ),
      ),
      selected: isSelected,
      onSelected: (_) => onTap(),
      selectedColor: activeColor,
      backgroundColor: AppTheme.surface,
      elevation: 0,
      side: BorderSide(color: isSelected ? activeColor : AppTheme.border),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    );
  }
}
