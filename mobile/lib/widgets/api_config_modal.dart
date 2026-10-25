import 'package:flutter/material.dart';

import '../config/api_config.dart';
import '../services/api_service.dart';
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
  bool _isTesting = false;
  String? _testStatusMessage;
  bool? _testSuccess;

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

  Future<void> _testConnection() async {
    setState(() {
      _isTesting = true;
      _testStatusMessage = null;
      _testSuccess = null;
    });

    final input = _controller.text.trim();
    if (input.isEmpty) {
      setState(() {
        _isTesting = false;
        _testSuccess = false;
        _testStatusMessage = 'Please enter a server URL.';
      });
      return;
    }

    try {
      final normalized = ApiConfig.normalizeUrl(input);
      // Auto-update controller with normalized URL
      _controller.text = normalized;

      final result = await ApiService.checkHealth(customBaseUrl: normalized);
      if (!mounted) return;

      setState(() {
        _isTesting = false;
        if (result.isSuccess) {
          _testSuccess = true;
          final system = result.data?['system'] ?? 'CareMind Engine';
          final version = result.data?['version'] ?? '1.0.0';
          _testStatusMessage = 'Connected successfully to $system (v$version)';
        } else {
          _testSuccess = false;
          _testStatusMessage = result.errorMessage ?? 'Connection failed.';
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isTesting = false;
        _testSuccess = false;
        _testStatusMessage = 'Invalid URL format: ${e.toString()}';
      });
    }
  }

  void _handleSave() {
    final input = _controller.text.trim();
    if (input.isEmpty) {
      setState(() {
        _testSuccess = false;
        _testStatusMessage = 'Backend URL cannot be empty.';
      });
      return;
    }

    try {
      final normalized = ApiConfig.normalizeUrl(input);
      widget.onSave(normalized);
      Navigator.pop(context);
    } catch (e) {
      setState(() {
        _testSuccess = false;
        _testStatusMessage = 'Invalid URL: ${e.toString()}';
      });
    }
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
            const SizedBox(height: 4),
            const Text(
              'Backend runs on port 8000 by default. Port 8000 will be added automatically if omitted.',
              style: TextStyle(fontSize: 11, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _controller,
              decoration: InputDecoration(
                labelText: 'Base URL',
                hintText: 'http://192.168.x.x:8000',
                border: const OutlineInputBorder(),
                isDense: true,
                suffixIcon: IconButton(
                  icon: _isTesting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.network_check_rounded, size: 20),
                  tooltip: 'Test Connection',
                  onPressed: _isTesting ? null : _testConnection,
                ),
              ),
              onSubmitted: (_) => _handleSave(),
            ),
            const SizedBox(height: 8),
            // Diagnostic status banner
            if (_testStatusMessage != null)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: _testSuccess == true
                      ? AppTheme.routineBg
                      : AppTheme.criticalBg,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: _testSuccess == true
                        ? AppTheme.routine
                        : AppTheme.critical,
                    width: 0.8,
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      _testSuccess == true
                          ? Icons.check_circle_outline_rounded
                          : Icons.error_outline_rounded,
                      size: 16,
                      color: _testSuccess == true
                          ? AppTheme.routine
                          : AppTheme.critical,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        _testStatusMessage!,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: _testSuccess == true
                              ? AppTheme.routine
                              : AppTheme.critical,
                        ),
                      ),
                    ),
                  ],
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
                  avatar: const Icon(Icons.wifi_rounded, size: 14),
                  label: const Text('Phone Wi-Fi IP (192.168.x.x:8000)'),
                  onPressed: () {
                    // Extract existing IP if already present or keep host
                    Uri? current;
                    try {
                      current = Uri.parse(_controller.text);
                    } catch (_) {}
                    final host =
                        current?.host.isNotEmpty == true &&
                            current!.host != 'localhost' &&
                            current.host != '10.0.2.2'
                        ? current.host
                        : '192.168.227.150';
                    _controller.text = 'http://$host:8000';
                    setState(() {
                      _testStatusMessage = null;
                      _testSuccess = null;
                    });
                  },
                ),
                ActionChip(
                  avatar: const Icon(Icons.language_rounded, size: 14),
                  label: const Text('Web/Localhost (localhost:8000)'),
                  onPressed: () {
                    _controller.text = ApiConfig.defaultLocalhostUrl;
                    setState(() {
                      _testStatusMessage = null;
                      _testSuccess = null;
                    });
                  },
                ),
                ActionChip(
                  avatar: const Icon(Icons.phone_android_rounded, size: 14),
                  label: const Text('Android Emulator (10.0.2.2:8000)'),
                  onPressed: () {
                    _controller.text = ApiConfig.defaultEmulatorUrl;
                    setState(() {
                      _testStatusMessage = null;
                      _testSuccess = null;
                    });
                  },
                ),
                ActionChip(
                  avatar: const Icon(Icons.restart_alt_rounded, size: 14),
                  label: const Text('Reset Auto-Detect'),
                  onPressed: () {
                    ApiConfig.resetToDefault();
                    setState(() {
                      _controller.text = ApiConfig.baseUrl;
                      _testStatusMessage = null;
                      _testSuccess = null;
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
        OutlinedButton.icon(
          onPressed: _isTesting ? null : _testConnection,
          icon: _isTesting
              ? const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.network_check_rounded, size: 14),
          label: const Text('Test', style: TextStyle(fontSize: 12)),
        ),
        ElevatedButton(
          onPressed: _handleSave,
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
