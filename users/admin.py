from django.contrib import admin
from .models import User
# Register your models here.

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'phone', 'is_blocked', 'created_at')
    search_fields = ('user_id', 'phone')
    list_filter = ('is_blocked', 'created_at')

