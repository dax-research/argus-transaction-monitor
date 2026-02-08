from django.contrib import admin
from .models import Transaction

# Register your models here.

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):

    list_display = (
        'txn_id',
        'user',
        'amount',
        'currency',
        'status',
        'fraud_decision',
        'risk_score',
        'created_at'
    )

    search_fields = (
        'txn_id',
        'user__user_id',
        'user__phone',
    )

    list_filter = (
        'status',
        'fraud_decision',
        'created_at',
    )

    ordering = ('-created_at',)

    readonly_fields = (
        'txn_id',
        'risk_score',
        'created_at',
        'updated_at',
    )

