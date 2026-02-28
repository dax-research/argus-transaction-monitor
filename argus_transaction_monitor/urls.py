from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token  # add this
urlpatterns = [
    path("", include("transactions.urls")),
    path("", include("otp_service.urls")),
    path("api-token-auth/", obtain_auth_token),
]