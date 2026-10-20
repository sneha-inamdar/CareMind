import 'package:flutter/material.dart';

import '../providers/app_state.dart';
import '../theme/app_theme.dart';

class ReplayControlCard extends StatelessWidget {
  final AppState appState;

  const ReplayControlCard({super.key, required this.appState});

  @override
  Widget build(BuildContext context) {
    final currentStep = appState.currentWindowIndex;
    final totalSteps = appState.totalWindows;
    final humanCurrentWindow = currentStep + 1;
    final status = appState.replayStatus;
    final isBusy = appState.isReplayBusy;

    // Status Badge Details
    Color statusColor;
    Color statusBg;
    String statusLabel;
    IconData statusIcon;

    switch (status) {
      case ReplayStatus.playing:
        statusColor = const Color(0xFF059669);
        statusBg = const Color(0xFFECFDF5);
        statusLabel = 'PLAYING';
        statusIcon = Icons.play_arrow_rounded;
        break;
      case ReplayStatus.completed:
        statusColor = AppTheme.primary;
        statusBg = AppTheme.primaryLight;
        statusLabel = 'COMPLETED';
        statusIcon = Icons.check_circle_outline_rounded;
        break;
      case ReplayStatus.paused:
        statusColor = const Color(0xFFD97706);
        statusBg = const Color(0xFFFFFBEB);
        statusLabel = 'PAUSED';
        statusIcon = Icons.pause_rounded;
        break;
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Row: Title, Window Indicator, Replay State Badge
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.primaryLight,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.fast_forward_rounded,
                  color: AppTheme.primary,
                  size: 20,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'ICU Replay Simulation',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.textPrimary,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Window $humanCurrentWindow / $totalSteps • MIMIC-IV Timeline',
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              // Prominent Replay State Badge
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 5,
                ),
                decoration: BoxDecoration(
                  color: statusBg,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: statusColor.withValues(alpha: 0.3)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(statusIcon, color: statusColor, size: 14),
                    const SizedBox(width: 4),
                    Text(
                      statusLabel,
                      style: TextStyle(
                        color: statusColor,
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Timeline Step Segments Progress Bar
          Row(
            children: List.generate(totalSteps, (index) {
              final isPassed = index < currentStep;
              final isCurrent = index == currentStep;
              Color segColor;
              if (isCurrent) {
                segColor = AppTheme.primary;
              } else if (isPassed) {
                segColor = AppTheme.primary.withValues(alpha: 0.4);
              } else {
                segColor = AppTheme.border;
              }

              return Expanded(
                child: Container(
                  height: 5,
                  margin: EdgeInsets.only(
                    right: index == totalSteps - 1 ? 0 : 4,
                  ),
                  decoration: BoxDecoration(
                    color: segColor,
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
              );
            }),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: Text(
                  'Window 1 (T+00:00)',
                  style: TextStyle(
                    fontSize: 10,
                    color: AppTheme.textSecondary.withValues(alpha: 0.8),
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Expanded(
                child: Text(
                  'Window $totalSteps (T+18:00)',
                  textAlign: TextAlign.end,
                  style: TextStyle(
                    fontSize: 10,
                    color: AppTheme.textSecondary.withValues(alpha: 0.8),
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Replay Control Buttons (Responsive Layout with 48x48 min touch targets)
          LayoutBuilder(
            builder: (context, constraints) {
              final bool isNarrow = constraints.maxWidth < 340;

              final playPauseButton = SizedBox(
                height: 48,
                child: ElevatedButton.icon(
                  onPressed: isBusy ? null : appState.toggleReplayPlayPause,
                  icon: isBusy
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : Icon(
                          status == ReplayStatus.playing
                              ? Icons.pause_rounded
                              : (status == ReplayStatus.completed
                                    ? Icons.replay_rounded
                                    : Icons.play_arrow_rounded),
                          size: 20,
                        ),
                  label: Text(
                    status == ReplayStatus.playing
                        ? 'Pause'
                        : (status == ReplayStatus.completed
                              ? 'Replay'
                              : 'Play'),
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
                    ),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: status == ReplayStatus.playing
                        ? const Color(0xFFD97706)
                        : AppTheme.primary,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                ),
              );

              final nextButton = SizedBox(
                height: 48,
                child: OutlinedButton.icon(
                  onPressed: isBusy ? null : appState.stepSimulation,
                  icon: const Icon(Icons.skip_next_rounded, size: 20),
                  label: const FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      'Next Window',
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                      ),
                    ),
                  ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.textPrimary,
                    side: const BorderSide(color: AppTheme.border),
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                ),
              );

              final resetButton = SizedBox(
                height: 48,
                child: OutlinedButton.icon(
                  onPressed: isBusy ? null : appState.resetSimulation,
                  icon: const Icon(Icons.restart_alt_rounded, size: 18),
                  label: const FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      'Reset',
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                      ),
                    ),
                  ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.textSecondary,
                    side: const BorderSide(color: AppTheme.border),
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                ),
              );

              if (isNarrow) {
                // Stack buttons on narrow mobile screen
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    playPauseButton,
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(child: nextButton),
                        const SizedBox(width: 8),
                        Expanded(child: resetButton),
                      ],
                    ),
                  ],
                );
              }

              // Horizontal row on standard screen
              return Row(
                children: [
                  Expanded(flex: 3, child: playPauseButton),
                  const SizedBox(width: 8),
                  Expanded(flex: 3, child: nextButton),
                  const SizedBox(width: 8),
                  Expanded(flex: 2, child: resetButton),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
