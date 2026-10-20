import 'package:flutter/material.dart';

import '../config/api_config.dart';
import '../theme/app_theme.dart';

class ApiConfigModal extends StatefulWidget {
  final Function(String newUrl) onSave;

  const ApiConfigModal({super.key, required this.onSave});

  static void show(BuildContext context, Function(String newUrl) onSave) {
    showDialog(
      context: context,
      builder: (context) => ApiConfigModal(onSave: onSave),
    );
  }

  @override
  State<ApiConfigModal> createState() => _ApiConfigModalState();
}

class _ApiConfigModalState extends State<ApiConfigModal> {
  late TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: ApiConfig.baseUrl);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.settings_remote_outlined, color: AppTheme.primary),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'Backend API Configuration',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppTheme.primaryLight,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.devices_rounded,
                    size: 16,
                    color: AppTheme.primary,
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Detected Platform: ${ApiConfig.platformName}',
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.primary,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Set the CareMind FastAPI server URL:',
              style: TextStyle(fontSize: 13, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _controller,
              decoration: const InputDecoration(
                labelText: 'Base URL',
                hintText: 'http://localhost:8000',
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Quick presets:',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                ActionChip(
                  avatar: const Icon(Icons.language_rounded, size: 14),
                  label: const Text('Web/Localhost (localhost)'),
                  onPressed: () =>
                      _controller.text = ApiConfig.defaultLocalhostUrl,
                ),
                ActionChip(
                  avatar: const Icon(Icons.phone_android_rounded, size: 14),
                  label: const Text('Android Emulator (10.0.2.2)'),
                  onPressed: () =>
                      _controller.text = ApiConfig.defaultEmulatorUrl,
                ),
                ActionChip(
                  avatar: const Icon(Icons.restart_alt_rounded, size: 14),
                  label: const Text('Reset Auto-Detect'),
                  onPressed: () {
                    ApiConfig.resetToDefault();
                    setState(() {
                      _controller.text = ApiConfig.baseUrl;
                    });
                  },
                ),
              ],
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () {
            widget.onSave(_controller.text.trim());
            Navigator.pop(context);
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: Colors.white,
          ),
          child: const Text('Connect'),
        ),
      ],
    );
  }
}
