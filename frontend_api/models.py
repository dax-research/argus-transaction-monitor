from django.db import models


class Investigation(models.Model):
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("CLOSED_RESOLVED", "Closed – Resolved"),
        ("CLOSED_FALSE_POSITIVE", "Closed – False Positive"),
    ]

    txn_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="OPEN")
    notes = models.TextField(blank=True, default="")
    resolution = models.TextField(blank=True, default="")
    analyst_name = models.CharField(max_length=150, default="Unassigned")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.status}] {self.txn_id}"
