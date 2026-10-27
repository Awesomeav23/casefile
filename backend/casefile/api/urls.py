from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.urls import auth_urlpatterns, me_urlpatterns

from .views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("auth/", include(auth_urlpatterns)),
    path("me/", include(me_urlpatterns)),
]

if settings.DEBUG:  # interactive docs in development only (API_PLAN preamble)
    urlpatterns.append(path("docs/", SpectacularSwaggerView.as_view(url_name="schema")))
