from django.urls import path
from .views import process_transaction

urlpatterns = [
    path("api/transaction/process/", process_transaction, name="process_transaction"),
]