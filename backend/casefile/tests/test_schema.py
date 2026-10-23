import pytest
from django.core.management import call_command
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_schema_endpoint_serves_openapi_3():
    response = APIClient().get("/api/v1/schema/?format=json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["openapi"].startswith("3.")
    assert "/api/v1/health/" in schema["paths"]


def test_schema_is_valid_with_no_warnings(tmp_path):
    # Raises (non-zero exit) on any validation error or warning.
    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(tmp_path / "s.yml"))
