from django.urls import path
from .views import verify_otp, debug_get_otp

urlpatterns = [
    path("api/verify-otp/", verify_otp, name="verify_otp"),
    path("api/debug/otp/<str:txn_id>/", debug_get_otp, name="debug_get_otp"),
]