import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class ModelDiagnosticsModal extends StatelessWidget {
  const ModelDiagnosticsModal({super.key});

  static void show(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => const ModelDiagnosticsModal(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.75,
      maxChildSize: 0.9,
      minChildSize: 0.4,
      expand: false,
      builder: (context, scrollController) {
        return SingleChildScrollView(
          controller: scrollController,
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Handle Bar
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppTheme.border,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Title
              Row(
                children: [
                  const Icon(
                    Icons.psychology_outlined,
                    color: AppTheme.primary,
                    size: 24,
                  ),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      '⚙️ Model Diagnostics & Provenance',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.textPrimary,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Diagnostic Cards
              _DiagnosticSection(
                title: 'MULTIMODAL ARCHITECTURE',
                content: 'Late fusion architecture combining MIT-BIH ECG feature extractor, PhysioNet 2019 clinical risk encoder, and MIMIC-IV continuous signal processing.',
              ),
              const SizedBox(height: 12),
              _DiagnosticSection(
                title: 'RISK CALIBRATION & FORMULA',
                content: 'CareMind Physiological Risk Score uses dynamic logit decision function with temperature scaling (T=1.75) across continuous 0-100 bounds.',
              ),
              const SizedBox(height: 12),
              _DiagnosticSection(
                title: 'DATASET PROVENANCE',
                content: 'Demonstration cohort derived from 3 real MIMIC-IV continuous waveform records (Tier 1 & Tier 2) with timestamp-aligned bed observations.',
              ),
              const SizedBox(height: 12),
              _DiagnosticSection(
                title: 'SCIENTIFIC SAFEGUARDS',
                content: 'No synthetic vital progression. Artificial noise or fabricated observations are strictly prohibited. Modality missingness automatically handled via adaptive sub-score weighting.',
              ),
              const SizedBox(height: 20),

              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => Navigator.pop(context),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  child: const Text('Close Diagnostics'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _DiagnosticSection extends StatelessWidget {
  final String title;
  final String content;

  const _DiagnosticSection({required this.title, required this.content});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.background,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w800,
              color: AppTheme.primary,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            content,
            style: const TextStyle(
              fontSize: 13,
              color: AppTheme.textPrimary,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}
