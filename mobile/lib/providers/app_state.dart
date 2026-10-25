import 'dart:async';

import 'package:flutter/material.dart';

import '../config/api_config.dart';
import '../models/patient.dart';
import '../models/alert.dart';
import '../models/simulation_state.dart';
import '../services/api_service.dart';

enum ReplayStatus { playing, paused, completed }

class AppState extends ChangeNotifier {
  int _currentTabIndex = 0;
  String _activeFilter =
      'ALL'; // 'ALL', 'CRITICAL', 'HIGH', 'ROUTINE', 'REGISTERED'

  bool _isLoading = false;
  bool _isConnecting = false;
  bool _isBackendReachable = false;
  String? _errorMessage;

  List<PatientOverview> _patients = [];
  List<PatientOverview> _registeredPatients = [];
  List<ActiveAlert> _activeAlerts = [];
  SimulationState? _simulationState;

  PatientOverview? _selectedPatient;

  // Replay Control State
  ReplayStatus _replayStatus = ReplayStatus.paused;
  bool _isReplayBusy = false;
  Timer? _replayTimer;

  int get currentTabIndex => _currentTabIndex;
  String get activeFilter => _activeFilter;
  bool get isLoading => _isLoading;
  bool get isConnecting => _isConnecting;
  bool get isBackendReachable => _isBackendReachable;
  String? get errorMessage => _errorMessage;

  List<PatientOverview> get patients => _patients;
  List<PatientOverview> get registeredPatients => _registeredPatients;
  List<PatientOverview> get allPatients => [
    ..._patients,
    ..._registeredPatients,
  ];
  List<ActiveAlert> get activeAlerts => _activeAlerts;
  SimulationState? get simulationState => _simulationState;
  PatientOverview? get selectedPatient => _selectedPatient;

  ReplayStatus get replayStatus => _replayStatus;
  bool get isReplayBusy => _isReplayBusy;

  int get currentWindowIndex => _simulationState?.currentStep ?? 0;
  int get totalWindows => _simulationState?.totalSteps ?? 4;

  List<PatientOverview> get filteredPatients {
    if (_activeFilter == 'CRITICAL') {
      return _patients
          .where((p) => p.priorityStatus == 'CRITICAL_PRIORITY')
          .toList();
    } else if (_activeFilter == 'HIGH') {
      return _patients
          .where((p) => p.priorityStatus == 'HIGH_PRIORITY')
          .toList();
    } else if (_activeFilter == 'ROUTINE') {
      return _patients
          .where((p) => p.priorityStatus == 'ROUTINE_MONITORING')
          .toList();
    } else if (_activeFilter == 'REGISTERED') {
      return _registeredPatients;
    }
    return allPatients;
  }

  int get criticalCount =>
      _patients.where((p) => p.priorityStatus == 'CRITICAL_PRIORITY').length;
  int get highCount =>
      _patients.where((p) => p.priorityStatus == 'HIGH_PRIORITY').length;
  int get routineCount =>
      _patients.where((p) => p.priorityStatus == 'ROUTINE_MONITORING').length;
  int get registeredCount => _registeredPatients.length;
  int get totalAllCount => allPatients.length;

  AppState({bool autoLoad = true}) {
    if (autoLoad) {
      loadData();
    }
  }

  @override
  void dispose() {
    _replayTimer?.cancel();
    super.dispose();
  }

  void setTabIndex(int index) {
    _currentTabIndex = index;
    notifyListeners();
  }

  void setFilter(String filter) {
    _activeFilter = filter;
    _currentTabIndex = 1; // Switch to Patients tab when filter tapped
    notifyListeners();
  }

  void resetFilter() {
    _activeFilter = 'ALL';
    notifyListeners();
  }

  void selectPatient(PatientOverview patient) {
    _selectedPatient = patient;
    notifyListeners();
  }

  void clearSelectedPatient() {
    _selectedPatient = null;
    notifyListeners();
  }

  Future<void> setBaseUrl(String url) async {
    try {
      await ApiConfig.setBaseUrl(url);
    } catch (e) {
      _errorMessage = 'Invalid URL: ${e.toString()}';
      notifyListeners();
      return;
    }
    await loadData();
  }

  /// Loads CareMind ICU simulation and patient data with reliable connectivity diagnostics.
  /// Prevents concurrent/duplicate health requests.
  Future<void> loadData() async {
    if (_isConnecting) return;
    _isConnecting = true;
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      // 1. Diagnostics: check health endpoint to verify reachability
      final healthResult = await ApiService.checkHealth();
      if (!healthResult.isSuccess) {
        _isBackendReachable = false;
        _errorMessage =
            healthResult.errorMessage ??
            'Unable to connect to CareMind backend at ${ApiConfig.baseUrl}';
        return;
      }

      _isBackendReachable = true;

      // 2. Fetch simulation state
      final simResult = await ApiService.getSimulationState();
      if (simResult.isSuccess && simResult.data != null) {
        _applySimulationState(simResult.data!);
        _errorMessage = null;
        return;
      }

      // 3. Fallback: fetch patients and alerts directly
      final patientsResult = await ApiService.getPatientsOverview();
      final alertsResult = await ApiService.getActiveAlerts();

      if (patientsResult.isSuccess) {
        final list = patientsResult.data ?? [];
        _patients = list.where((p) => p.isMonitored).toList();
        _registeredPatients = list.where((p) => !p.isMonitored).toList();
        _activeAlerts = alertsResult.data ?? [];
        _errorMessage = null;
      } else {
        // Health check succeeded, but patient overview endpoint failed
        _errorMessage =
            'Connected to CareMind engine, but failed to load patient data: ${patientsResult.errorMessage ?? 'Unknown error'}';
      }
    } finally {
      _isLoading = false;
      _isConnecting = false;
      notifyListeners();
    }
  }

  void _applySimulationState(SimulationState state) {
    _simulationState = state;
    _patients = state.patients;
    _registeredPatients = state.registeredPatients;
    _activeAlerts = state.activeAlerts;

    // Check if simulation step is at the end
    if (state.currentStep >= state.totalSteps - 1) {
      if (_replayStatus == ReplayStatus.playing) {
        _stopReplayTimer();
        _replayStatus = ReplayStatus.completed;
      }
    }

    // Synchronize selected patient if open
    if (_selectedPatient != null) {
      final updated = allPatients.firstWhere(
        (p) =>
            p.recordId == _selectedPatient!.recordId ||
            (p.subjectId != null &&
                p.subjectId.toString() ==
                    _selectedPatient!.subjectId.toString()),
        orElse: () => _selectedPatient!,
      );
      _selectedPatient = updated;
    }
  }

  void _stopReplayTimer() {
    _replayTimer?.cancel();
    _replayTimer = null;
  }

  /// Toggle between Play and Pause for the ICU Replay simulation
  Future<void> toggleReplayPlayPause() async {
    if (_isReplayBusy) return;

    if (_replayStatus == ReplayStatus.playing) {
      // Pause simulation
      _stopReplayTimer();
      _replayStatus = ReplayStatus.paused;
      notifyListeners();

      _isReplayBusy = true;
      try {
        final result = await ApiService.pauseSimulation();
        if (result.isSuccess && result.data != null) {
          _applySimulationState(result.data!);
        }
      } catch (e) {
        // Ignored, client pause is maintained
      } finally {
        _isReplayBusy = false;
        notifyListeners();
      }
    } else {
      // If completed or at last window, reset or step to start
      if (_replayStatus == ReplayStatus.completed ||
          (_simulationState != null &&
              _simulationState!.currentStep >=
                  _simulationState!.totalSteps - 1)) {
        await resetSimulation();
      }

      _replayStatus = ReplayStatus.playing;
      notifyListeners();

      _isReplayBusy = true;
      try {
        final result = await ApiService.startSimulation();
        if (result.isSuccess && result.data != null) {
          _applySimulationState(result.data!);
        }
      } catch (e) {
        // Fallback continues
      } finally {
        _isReplayBusy = false;
        notifyListeners();
      }

      // Schedule periodic playback
      _stopReplayTimer();
      _replayTimer = Timer.periodic(const Duration(milliseconds: 2500), (_) {
        if (_replayStatus == ReplayStatus.playing && !_isReplayBusy) {
          _onReplayTimerTick();
        }
      });
    }
  }

  void _onReplayTimerTick() async {
    if (_simulationState != null &&
        _simulationState!.currentStep >= _simulationState!.totalSteps - 1) {
      _stopReplayTimer();
      _replayStatus = ReplayStatus.completed;
      notifyListeners();
      return;
    }
    await stepSimulation(isAutoTick: true);
  }

  /// Advance ICU Replay simulation by 1 window
  Future<void> stepSimulation({bool isAutoTick = false}) async {
    if (_isReplayBusy) return;
    _isReplayBusy = true;
    if (!isAutoTick) {
      notifyListeners();
    }

    try {
      final result = await ApiService.stepSimulation();
      if (result.isSuccess && result.data != null) {
        _applySimulationState(result.data!);
        if (result.data!.currentStep >= result.data!.totalSteps - 1) {
          if (_replayStatus == ReplayStatus.playing) {
            _stopReplayTimer();
            _replayStatus = ReplayStatus.completed;
          }
        }
      } else {
        _errorMessage = result.errorMessage;
      }
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isReplayBusy = false;
      notifyListeners();
    }
  }

  /// Reset simulation back to initial window (Window 0)
  Future<void> resetSimulation() async {
    if (_isReplayBusy) return;
    _stopReplayTimer();
    _replayStatus = ReplayStatus.paused;
    _isReplayBusy = true;
    notifyListeners();

    try {
      final result = await ApiService.resetSimulation();
      if (result.isSuccess && result.data != null) {
        _applySimulationState(result.data!);
        _replayStatus = ReplayStatus.paused;
      } else {
        _errorMessage = result.errorMessage;
      }
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isReplayBusy = false;
      notifyListeners();
    }
  }

  /// Manually Register a patient profile
  Future<ApiResult<Map<String, dynamic>>> registerPatient(
    Map<String, dynamic> data,
  ) async {
    final result = await ApiService.registerPatient(data);
    if (result.isSuccess) {
      await loadData();
    }
    return result;
  }

  /// Enroll an available genuine MIMIC-IV cohort record
  Future<ApiResult<Map<String, dynamic>>> addCohortPatient(
    String recordId,
  ) async {
    final result = await ApiService.addCohortPatient(recordId);
    if (result.isSuccess) {
      await loadData();
    }
    return result;
  }

  /// Get list of available unmonitored cohort records
  Future<ApiResult<List<Map<String, dynamic>>>>
  getAvailableCohortRecords() async {
    return await ApiService.getAvailableCohortRecords();
  }

  /// Remove a patient from monitoring or registered roster
  Future<ApiResult<Map<String, dynamic>>> removePatient(String recordId) async {
    final result = await ApiService.removePatient(recordId);
    if (result.isSuccess) {
      if (_selectedPatient?.recordId == recordId ||
          _selectedPatient?.subjectId.toString() == recordId) {
        clearSelectedPatient();
      }
      await loadData();
    }
    return result;
  }

  @visibleForTesting
  void setErrorMessageForTesting(String? msg) {
    _isLoading = false;
    _isConnecting = false;
    _errorMessage = msg;
    notifyListeners();
  }
}
