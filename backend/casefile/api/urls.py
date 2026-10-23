from django.conf import settings
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
]

if settings.DEBUG:  # interactive docs in development only (API_PLAN preamble)
    urlpatterns.append(path("docs/", SpectacularSwaggerView.as_view(url_name="schema")))
