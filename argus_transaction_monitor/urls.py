from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.authtoken.views import obtain_auth_token


def index(request):
    """Landing / health-check."""
    return HttpResponse("<h1>Argus Transaction Monitor</h1><p>API ready.</p>")


# ── Frontend HTML page views ──────────────────────────────────────────────────
def login_page(request):
    return render(request, "login.html")

def analyst_dashboard_page(request):
    return render(request, "dashboard_analyst.html")

def auditor_dashboard_page(request):
    return render(request, "dashboard_auditor.html")

def role_selection_page(request):
    return render(request, "role-selection.html")


urlpatterns = [
    path("admin/",  admin.site.urls),
    path("",        index, name="index"),

    # ── Frontend HTML pages ────────────────────────────────────────────────
    path("login/",              login_page,              name="login"),
    path("dashboard/analyst/",  analyst_dashboard_page,  name="dash-analyst"),
    path("dashboard/auditor/",  auditor_dashboard_page,  name="dash-auditor"),
    path("role-selection/",     role_selection_page,     name="role-selection"),

    # ── API routes ─────────────────────────────────────────────────────────
    path("", include("transactions.urls")),
    path("", include("otp_service.urls")),
    path("", include("analyst_dashboard.urls")),
    path("", include("frontend_api.urls")),

    # Legacy DRF token auth (for customer-app)
    path("api-token-auth/", obtain_auth_token),
]