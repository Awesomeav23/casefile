from unittest import mock

import pytest
from django.db import OperationalError
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_ok_without_authentication():
    response = APIClient().get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


@pytest.mark.django_db
def test_health_reports_database_unavailable():
    with mock.patch("casefile.api.views.check_database", side_effect=OperationalError("down")):
        response = APIClient().get("/api/v1/health/")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "service_unavailable"
    assert error["details"] == {"database": "unavailable"}
    assert "down" not in error["message"]
