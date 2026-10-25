import 'package:flutter/material.dart';

import '../providers/app_state.dart';
import '../theme/app_theme.dart';

class AddPatientModal extends StatefulWidget {
  final AppState appState;

  const AddPatientModal({super.key, required this.appState});

  static void show(BuildContext context, AppState appState) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => AddPatientModal(appState: appState),
    );
  }

  @override
  State<AddPatientModal> createState() => _AddPatientModalState();
}

class _AddPatientModalState extends State<AddPatientModal>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // Form State
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _idController = TextEditingController();
  final _bedController = TextEditingController();
  final _ageController = TextEditingController();
  final _notesController = TextEditingController();
  String _selectedSex = 'M';

  bool _isSubmitting = false;
  String? _formError;

  // Available Cohort Records State
  bool _isLoadingCohort = true;
  List<Map<String, dynamic>> _availableCohortRecords = [];
  String? _selectedCohortRecordId;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);

    // Auto-suggest next bed ID based on current roster count
    final nextBedNumber = widget.appState.allPatients.length + 1;
    _bedController.text = 'Bed ICU-${nextBedNumber.toString().padLeft(2, '0')}';

    _loadAvailableCohortRecords();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _nameController.dispose();
    _idController.dispose();
    _bedController.dispose();
    _ageController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _loadAvailableCohortRecords() async {
    final result = await widget.appState.getAvailableCohortRecords();
    if (mounted) {
      setState(() {
        _isLoadingCohort = false;
        if (result.isSuccess && result.data != null) {
          _availableCohortRecords = result.data!;
          if (_availableCohortRecords.isNotEmpty) {
            _selectedCohortRecordId = _availableCohortRecords.first['record_id']
                ?.toString();
          }
        }
      });
    }
  }

  Future<void> _submitManualRegistration() async {
    if (!_formKey.currentState!.validate()) return;

    final name = _nameController.text.trim();
    final patientId = _idController.text.trim();
    final bedId = _bedController.text.trim();
    final notes = _notesController.text.trim();
    final ageText = _ageController.text.trim();
    final age = ageText.isNotEmpty ? int.tryParse(ageText) : null;

    // Check duplicate locally against currently loaded patients
    final isDuplicate = widget.appState.allPatients.any(
      (p) =>
          p.recordId.toLowerCase() == patientId.toLowerCase() ||
          p.subjectId.toString().toLowerCase() == patientId.toLowerCase(),
    );
    if (isDuplicate) {
      setState(() {
        _formError =
            "Patient ID '$patientId' already exists in current roster.";
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _formError = null;
    });

    final payload = {
      'name': name,
      'patient_id': patientId,
      'bed_id': bedId.isNotEmpty ? bedId : 'Unassigned Bed',
      'age': age,
      'sex': _selectedSex,
      'notes': notes,
    };

    final result = await widget.appState.registerPatient(payload);

    if (!mounted) return;

    if (result.isSuccess) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            "Patient '$name' (ID: $patientId) registered successfully.",
          ),
          backgroundColor: const Color(0xFF059669),
          duration: const Duration(seconds: 4),
        ),
      );
    } else {
      setState(() {
        _isSubmitting = false;
        _formError =
            result.errorMessage ?? 'Registration failed. Check connection.';
      });
    }
  }

  Future<void> _submitCohortEnrollment() async {
    if (_selectedCohortRecordId == null) return;

    setState(() {
      _isSubmitting = true;
      _formError = null;
    });

    final result = await widget.appState.addCohortPatient(
      _selectedCohortRecordId!,
    );

    if (!mounted) return;

    if (result.isSuccess) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            "MIMIC Record $_selectedCohortRecordId enrolled into monitored cohort.",
          ),
          backgroundColor: const Color(0xFF059669),
          duration: const Duration(seconds: 4),
        ),
      );
    } else {
      setState(() {
        _isSubmitting = false;
        _formError = result.errorMessage ?? 'Failed to enroll cohort patient.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: DraggableScrollableSheet(
        initialChildSize: 0.85,
        maxChildSize: 0.95,
        minChildSize: 0.5,
        expand: false,
        builder: (context, scrollController) {
          return SingleChildScrollView(
            controller: scrollController,
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                // Handle
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
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Expanded(
                      child: Text(
                        'Add Patient to ICU Roster',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.textPrimary,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                const Text(
                  'Register a new patient profile or enroll an available MIMIC-IV cohort record.',
                  style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                ),
                const SizedBox(height: 16),

                // Error Notice
                if (_formError != null)
                  Container(
                    margin: const EdgeInsets.only(bottom: 14),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: AppTheme.criticalBg,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: AppTheme.critical.withValues(alpha: 0.3),
                      ),
                    ),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.error_outline_rounded,
                          color: AppTheme.critical,
                          size: 18,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _formError!,
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppTheme.critical,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                // Tabs: Manual EMR vs Genuine Cohort Record
                Container(
                  decoration: BoxDecoration(
                    color: AppTheme.background,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: TabBar(
                    controller: _tabController,
                    indicatorSize: TabBarIndicatorSize.tab,
                    indicator: BoxDecoration(
                      color: AppTheme.primary,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    labelColor: Colors.white,
                    unselectedLabelColor: AppTheme.textSecondary,
                    labelStyle: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                    tabs: const [
                      Tab(text: 'Manual EMR Register'),
                      Tab(text: 'MIMIC Waveform Cohort'),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // Tab Content
                AnimatedBuilder(
                  animation: _tabController,
                  builder: (context, _) {
                    if (_tabController.index == 0) {
                      return _buildManualForm();
                    } else {
                      return _buildCohortSelector();
                    }
                  },
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildManualForm() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Name Field
          TextFormField(
            controller: _nameController,
            decoration: const InputDecoration(
              labelText: 'Patient Full Name *',
              hintText: 'e.g. Sarah Jenkins',
              border: OutlineInputBorder(),
              isDense: true,
              prefixIcon: Icon(Icons.person_outline_rounded, size: 20),
            ),
            validator: (val) {
              if (val == null || val.trim().isEmpty) {
                return 'Patient name is required.';
              }
              return null;
            },
          ),
          const SizedBox(height: 12),

          // ID and Bed Row
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _idController,
                  decoration: const InputDecoration(
                    labelText: 'Patient ID *',
                    hintText: 'e.g. 10094562',
                    border: OutlineInputBorder(),
                    isDense: true,
                    prefixIcon: Icon(Icons.tag_rounded, size: 20),
                  ),
                  validator: (val) {
                    if (val == null || val.trim().isEmpty) {
                      return 'Patient ID is required.';
                    }
                    return null;
                  },
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextFormField(
                  controller: _bedController,
                  decoration: const InputDecoration(
                    labelText: 'Bed Assignment',
                    hintText: 'e.g. Bed ICU-04',
                    border: OutlineInputBorder(),
                    isDense: true,
                    prefixIcon: Icon(Icons.hotel_outlined, size: 20),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Age and Sex Row
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _ageController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Age (optional)',
                    hintText: 'e.g. 64',
                    border: OutlineInputBorder(),
                    isDense: true,
                    prefixIcon: Icon(Icons.cake_outlined, size: 20),
                  ),
                  validator: (val) {
                    if (val != null && val.trim().isNotEmpty) {
                      final n = int.tryParse(val.trim());
                      if (n == null || n <= 0 || n > 120) {
                        return 'Enter valid age';
                      }
                    }
                    return null;
                  },
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _selectedSex,
                  isExpanded: true,
                  decoration: const InputDecoration(
                    labelText: 'Sex',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  items: const [
                    DropdownMenuItem(value: 'M', child: Text('Male (M)')),
                    DropdownMenuItem(value: 'F', child: Text('Female (F)')),
                    DropdownMenuItem(value: 'Other', child: Text('Other')),
                  ],
                  onChanged: (val) {
                    if (val != null) setState(() => _selectedSex = val);
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Clinical Notes
          TextFormField(
            controller: _notesController,
            maxLines: 2,
            decoration: const InputDecoration(
              labelText: 'Clinical Notes / Admission Diagnosis (optional)',
              hintText: 'e.g. Admitted following coronary bypass, stable post-op observation.',
              border: OutlineInputBorder(),
              isDense: true,
            ),
          ),
          const SizedBox(height: 16),

          // Info Banner
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppTheme.primaryLight,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Row(
              children: [
                Icon(
                  Icons.info_outline_rounded,
                  color: AppTheme.primary,
                  size: 18,
                ),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Manually registered patients are enrolled with status "Registered — No Data Source Connected". Waveform AI risk monitoring begins when telemetry is linked.',
                    style: TextStyle(
                      fontSize: 11,
                      color: AppTheme.primary,
                      height: 1.3,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Submit Button
          SizedBox(
            width: double.infinity,
            height: 48,
            child: ElevatedButton.icon(
              onPressed: _isSubmitting ? null : _submitManualRegistration,
              icon: _isSubmitting
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.person_add_alt_1_rounded, size: 20),
              label: Text(
                _isSubmitting ? 'Registering...' : 'Register Patient',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCohortSelector() {
    if (_isLoadingCohort) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(30),
          child: CircularProgressIndicator(color: AppTheme.primary),
        ),
      );
    }

    if (_availableCohortRecords.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppTheme.background,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppTheme.border),
        ),
        child: const Column(
          children: [
            Icon(
              Icons.check_circle_outline_rounded,
              color: AppTheme.primary,
              size: 36,
            ),
            SizedBox(height: 8),
            Text(
              'All Genuine MIMIC-IV Records Monitored',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 4),
            Text(
              'All available genuine cohort records from local inventory are already enrolled into active monitoring. Synthetic records are never fabricated.',
              style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Select an unmonitored MIMIC-IV waveform record to enroll:',
          style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
        ),
        const SizedBox(height: 10),
        ListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: _availableCohortRecords.length,
          itemBuilder: (context, index) {
            final rec = _availableCohortRecords[index];
            final recId = rec['record_id']?.toString() ?? '';
            final isSelected = _selectedCohortRecordId == recId;
            final modalities = (rec['available_modalities'] as List? ?? [])
                .join(', ');

            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
                side: BorderSide(
                  color: isSelected ? AppTheme.primary : AppTheme.border,
                ),
              ),
              child: ListTile(
                leading: Icon(
                  isSelected
                      ? Icons.radio_button_checked_rounded
                      : Icons.radio_button_off_rounded,
                  color: isSelected ? AppTheme.primary : AppTheme.textSecondary,
                ),
                title: Text(
                  'Patient #${rec['subject_id']}',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                subtitle: Text(
                  'Record $recId • ${rec['tier'] ?? 'Tier 2'}\nModalities: $modalities',
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppTheme.textSecondary,
                  ),
                ),
                onTap: () {
                  setState(() => _selectedCohortRecordId = recId);
                },
              ),
            );
          },
        ),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          height: 48,
          child: ElevatedButton.icon(
            onPressed: (_isSubmitting || _selectedCohortRecordId == null)
                ? null
                : _submitCohortEnrollment,
            icon: _isSubmitting
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.add_chart_rounded, size: 20),
            label: Text(
              _isSubmitting ? 'Enrolling...' : 'Enroll MIMIC Record',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primary,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
