from django.urls import path
from .views import process_transaction, transaction_history, profile

urlpatterns = [
    path("api/transaction/process/", process_transaction, name="process_transaction"),
    path("api/transactions/", transaction_history, name="transaction_history"),
    path("api/profile/", profile, name="profile"),
]