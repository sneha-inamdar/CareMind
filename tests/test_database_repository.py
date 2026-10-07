"""
Unit tests for CareMind Database Repository Abstraction Layer & Supabase Integration.

Validates:
1. DatabaseConfig initialization & environment check
2. LocalJSONRepository data loading & patient prioritization sorting
3. Repository factory function fallback behavior
4. API endpoints integration with repository layer
"""

import pytest
import os
import json
from fastapi.testclient import TestClient

from src.db.config import DatabaseConfig
from src.db.repository import LocalJSONRepository, get_repository, CareMindBaseRepository
from backend.main import app


@pytest.fixture
def test_client():
    return TestClient(app)


def test_database_config():
    """Test DatabaseConfig loads environment variables correctly."""
    config = DatabaseConfig()
    assert hasattr(config, "supabase_url")
    assert hasattr(config, "supabase_key")
    # Default without .env should return False for is_supabase_configured
    assert isinstance(config.is_supabase_configured, bool)


def test_local_json_repository():
    """Test LocalJSONRepository retrieves records and prioritizes patients by risk score DESC."""
    repo = LocalJSONRepository()
    
    records = repo.get_available_records()
    assert len(records) >= 3

    patients = repo.get_patients_overview(window_index=0)
    assert len(patients) >= 3
    
    # Verify patients are sorted by risk_score DESC
    scores = [p["risk_score"] for p in patients]
    assert scores == sorted(scores, reverse=True), "Patients must be sorted by highest risk score first."


def test_repository_factory():
    """Test get_repository() returns a valid CareMindBaseRepository instance."""
    repo = get_repository()
    assert isinstance(repo, CareMindBaseRepository)


def test_api_patients_endpoint_with_repository(test_client):
    """Test GET /api/multimodal/patients endpoint returns sorted patients via repository."""
    res = test_client.get("/api/multimodal/patients?window_index=0")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["patient_count"] >= 3
    
    patients = data["patients"]
    scores = [p["risk_score"] for p in patients]
    assert scores == sorted(scores, reverse=True)
