from django.urls import path
from .views import analyst_transactions, flag_transaction, analyst_stats

urlpatterns = [
    path("api/analyst/transactions/", analyst_transactions, name="analyst_transactions"),
    path("api/analyst/flag/<str:txn_id>/", flag_transaction, name="flag_transaction"),
    path("api/analyst/stats/", analyst_stats, name="analyst_stats"),
]
