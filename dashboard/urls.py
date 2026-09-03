from django.urls import path
from . import views

urlpatterns = [
    path('global-search/', views.global_search, name='global_search'),
    path('settings/', views.settings, name='settings'),
    path('notifications/', views.notifications, name='notifications'),
    path('', views.home, name='home'),
]
