from django.contrib import admin
from django.urls import include, path, re_path

from casefile.api.views import api_not_found

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("casefile.api.urls")),
    # Must stay last: unknown API routes return the JSON error envelope.
    re_path(r"^api/", api_not_found),
]

handler500 = "casefile.api.views.api_server_error"
