from django.urls import path

from . import views

auth_urlpatterns = [
    path("csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("password-reset/", views.PasswordResetView.as_view(), name="auth-password-reset"),
    path(
        "password-reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
]

me_urlpatterns = [
    path("profile/", views.ProfileView.as_view(), name="me-profile"),
    path("password/", views.PasswordChangeView.as_view(), name="me-password"),
]
