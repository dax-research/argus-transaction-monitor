from django.db import models

# Create your models here.
class User(models.Model):
    user_id = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=15)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user_id