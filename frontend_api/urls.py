from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("api/auth/login/",    views.login_view,    name="auth-login"),
    path("api/auth/register/", views.register_view, name="auth-register"),
    path("api/auth/logout/",   views.logout_view,   name="auth-logout"),
    path("api/auth/refresh/",  views.refresh_view,  name="auth-refresh"),
    path("api/auth/google/",   views.google_auth_view, name="auth-google"),  # Google OAuth

    # Dashboard
    path("api/dashboard/stats/",                             views.stats_view,               name="dash-stats"),
    path("api/dashboard/transactions/",                      views.transactions_view,         name="dash-transactions"),
    path("api/dashboard/transactions/<str:txn_id>/flag/",    views.flag_transaction_view,     name="dash-flag-txn"),
    path("api/dashboard/investigations/",                    views.investigations_view,       name="dash-investigations"),
    path("api/dashboard/investigations/<int:pk>/",           views.investigation_update_view, name="dash-inv-update"),
    path("api/dashboard/audit-log/",                         views.audit_log_view,            name="dash-audit"),
    
    # Simulation & SHAP Explainability
    path("simulate/",                                        views.simulate_fraud_view,       name="simulate-fraud"),
    path("explain/",                                         views.explain_fraud_view,        name="explain-fraud"),
]
