import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from content import models as m
from content.importer import import_case
from content.tests.test_validator import MINI

pytestmark = pytest.mark.django_db

MODELS = [
    m.Case,
    m.CaseImport,
    m.Person,
    m.Location,
    m.Evidence,
    m.Topic,
    m.Statement,
    m.TimelineEvent,
    m.AccusationQuestion,
    m.Contradiction,
    m.CaseSolution,
    m.RedHerring,
    m.HintTrack,
]


@pytest.fixture
def staff(client):
    import_case(MINI)
    admin = get_user_model().objects.create_superuser("admin@example.com", "a-long-password-1")
    client.force_login(admin)
    return client


def url(model, action, *args):
    return reverse(f"admin:content_{model._meta.model_name}_{action}", args=args)


@pytest.mark.parametrize("model", MODELS, ids=lambda x: x.__name__)
def test_changelist_and_detail_pages_load(staff, model):
    assert staff.get(url(model, "changelist")).status_code == 200
    obj = model.objects.first()
    assert staff.get(url(model, "change", obj.pk)).status_code == 200  # read-only view


@pytest.mark.parametrize("model", MODELS, ids=lambda x: x.__name__)
def test_content_cannot_be_added_through_the_admin(staff, model):
    assert staff.get(url(model, "add")).status_code == 403
