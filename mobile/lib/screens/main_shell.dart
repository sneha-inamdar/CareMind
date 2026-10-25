import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../theme/app_theme.dart';
import '../widgets/api_config_modal.dart';
import '../widgets/model_diagnostics_modal.dart';
import 'overview_screen.dart';
import 'patients_screen.dart';
import 'alerts_screen.dart';
import 'patient_detail_screen.dart';

class MainShell extends StatelessWidget {
  const MainShell({super.key});

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);

    // If a patient is selected for inspection, show Patient Detail Screen
    if (appState.selectedPatient != null) {
      return PatientDetailScreen(
        patient: appState.selectedPatient!,
        onBack: () => appState.clearSelectedPatient(),
      );
    }

    final screens = const [OverviewScreen(), PatientsScreen(), AlertsScreen()];

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: AppTheme.primaryLight,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(
                Icons.favorite_rounded,
                color: AppTheme.primary,
                size: 20,
              ),
            ),
            const SizedBox(width: 10),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'CareMind',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.5,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    'ICU Multimodal Intelligence',
                    style: TextStyle(
                      fontSize: 10,
                      color: AppTheme.textSecondary,
                      fontWeight: FontWeight.w500,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          // Model Diagnostics secondary action button
          IconButton(
            icon: const Icon(
              Icons.psychology_outlined,
              color: AppTheme.primary,
            ),
            tooltip: 'Model Diagnostics',
            onPressed: () => ModelDiagnosticsModal.show(context),
          ),

          // API Config button
          IconButton(
            icon: const Icon(
              Icons.settings_outlined,
              color: AppTheme.textSecondary,
            ),
            tooltip: 'Server Settings',
            onPressed: () => ApiConfigModal.show(
              context,
              (newUrl) => appState.setBaseUrl(newUrl),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // Network / Connection Error Banner
          if (appState.errorMessage != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              color: AppTheme.criticalBg,
              child: Column(
                children: [
                  Row(
                    children: [
                      const Icon(
                        Icons.wifi_off_rounded,
                        color: AppTheme.critical,
                        size: 20,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          appState.errorMessage!,
                          style: const TextStyle(
                            color: AppTheme.critical,
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                          ),
                          maxLines: 4,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    alignment: WrapAlignment.end,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: 8,
                    runSpacing: 6,
                    children: [
                      OutlinedButton.icon(
                        onPressed: () => ApiConfigModal.show(
                          context,
                          (newUrl) => appState.setBaseUrl(newUrl),
                        ),
                        icon: const Icon(
                          Icons.settings_outlined,
                          size: 14,
                          color: AppTheme.critical,
                        ),
                        label: const Text(
                          'Configure Server URL',
                          style: TextStyle(
                            color: AppTheme.critical,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size(0, 36),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 6,
                          ),
                          side: const BorderSide(color: AppTheme.critical),
                        ),
                      ),
                      ElevatedButton.icon(
                        onPressed: appState.isLoading
                            ? null
                            : appState.loadData,
                        icon: appState.isLoading
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.refresh_rounded, size: 14),
                        label: Text(
                          appState.isLoading
                              ? 'Connecting...'
                              : 'Retry Connection',
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        style: ElevatedButton.styleFrom(
                          minimumSize: const Size(0, 36),
                          backgroundColor: AppTheme.critical,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 6,
                          ),
                          elevation: 0,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

          // Main View Content
          Expanded(
            child: appState.isLoading
                ? const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        CircularProgressIndicator(color: AppTheme.primary),
                        SizedBox(height: 16),
                        Text(
                          'Connecting to CareMind Engine...',
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  )
                : IndexedStack(
                    index: appState.currentTabIndex,
                    children: screens,
                  ),
          ),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: appState.currentTabIndex,
        onTap: (index) => appState.setTabIndex(index),
        items: [
          const BottomNavigationBarItem(
            icon: Icon(Icons.dashboard_outlined),
            activeIcon: Icon(Icons.dashboard_rounded),
            label: 'Overview',
          ),
          BottomNavigationBarItem(
            icon: Stack(
              children: [
                const Icon(Icons.people_outline_rounded),
                if (appState.criticalCount > 0)
                  Positioned(
                    right: 0,
                    top: 0,
                    child: Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(
                        color: AppTheme.critical,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
              ],
            ),
            activeIcon: const Icon(Icons.people_rounded),
            label: 'Patients',
          ),
          BottomNavigationBarItem(
            icon: Stack(
              children: [
                const Icon(Icons.notifications_none_rounded),
                if (appState.activeAlerts.isNotEmpty)
                  Positioned(
                    right: 0,
                    top: 0,
                    child: Container(
                      padding: const EdgeInsets.all(2),
                      decoration: const BoxDecoration(
                        color: AppTheme.critical,
                        shape: BoxShape.circle,
                      ),
                      constraints: const BoxConstraints(
                        minWidth: 12,
                        minHeight: 12,
                      ),
                      child: Text(
                        '${appState.activeAlerts.length}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 8,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ),
              ],
            ),
            activeIcon: const Icon(Icons.notifications_rounded),
            label: 'Alerts',
          ),
        ],
      ),
    );
  }
}
