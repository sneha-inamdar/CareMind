import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../theme/app_theme.dart';
import '../widgets/add_patient_modal.dart';
import '../widgets/patient_card.dart';
import '../widgets/patient_filter_bar.dart';

class PatientsScreen extends StatelessWidget {
  const PatientsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final filtered = appState.filteredPatients;

    return RefreshIndicator(
      onRefresh: appState.loadData,
      color: AppTheme.primary,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Filter Bar & + Add Patient Button
            PatientFilterBar(
              activeFilter: appState.activeFilter,
              totalCount: appState.totalAllCount,
              filteredCount: filtered.length,
              criticalCount: appState.criticalCount,
              highCount: appState.highCount,
              routineCount: appState.routineCount,
              registeredCount: appState.registeredCount,
              onFilterChanged: (filter) => appState.setFilter(filter),
              onResetFilter: () => appState.resetFilter(),
              onAddPatient: () => AddPatientModal.show(context, appState),
            ),
            const SizedBox(height: 14),

            // Roster List
            Expanded(
              child: filtered.isEmpty
                  ? Center(
                      child: SingleChildScrollView(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(
                              Icons.search_off_rounded,
                              size: 48,
                              color: AppTheme.textSecondary,
                            ),
                            const SizedBox(height: 12),
                            Text(
                              'No ${appState.activeFilter} patients found in roster.',
                              style: const TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.textSecondary,
                              ),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 12),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              alignment: WrapAlignment.center,
                              children: [
                                ElevatedButton.icon(
                                  onPressed: () =>
                                      AddPatientModal.show(context, appState),
                                  icon: const Icon(
                                    Icons.person_add_rounded,
                                    size: 16,
                                  ),
                                  label: const Text('Add Patient'),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppTheme.primary,
                                    foregroundColor: Colors.white,
                                    elevation: 0,
                                  ),
                                ),
                                OutlinedButton(
                                  onPressed: () => appState.resetFilter(),
                                  style: OutlinedButton.styleFrom(
                                    side: const BorderSide(
                                      color: AppTheme.border,
                                    ),
                                  ),
                                  child: const Text('Reset Filter'),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    )
                  : ListView.builder(
                      itemCount: filtered.length,
                      itemBuilder: (context, index) {
                        final p = filtered[index];
                        return PatientCard(
                          patient: p,
                          onInspect: () => appState.selectPatient(p),
                          onRemove: () => appState.removePatient(p.recordId),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
