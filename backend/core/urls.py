from django.urls import path
from .views import home, serve_template

urlpatterns = [
    path('', home, name='home'),
    path('dashboard.html', serve_template, {'page': 'dashboard.html'}, name='dashboard'),
    # catch-all for frontend html files (e.g. /dashboard.html)
    path('<str:page>', serve_template, name='page'),
]