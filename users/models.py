from django.db import models


       

class User(models.Model):
    user_id = models.CharField(max_length=50, primary_key=True)
    phone = models.CharField(max_length=15)
    is_blocked = models.BooleanField(default=False)
    account_balance = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user_id