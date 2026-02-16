# Avoid loading model on every request.
from django.apps import AppConfig

class FraudEngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fraud_engine'

    detector = None

    def ready(self):
        from .services.ml_rf_v1 import ArgusFraudDetector
        FraudEngineConfig.detector = ArgusFraudDetector()
