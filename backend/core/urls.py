from django.urls import path
from .views import home, serve_template

urlpatterns = [
    path('', home, name='home'),
    # catch-all for frontend html files (e.g. /dashboard.html)
    path('<str:page>', serve_template, name='page'),
]