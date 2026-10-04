from django.urls import path, re_path
from . import views

urlpatterns = [
    path('for-you/', views.for_you, name='for_you'),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/for-you/$', views.for_you, name='workplace_for_you'),
    path('global-search/', views.global_search, name='global_search'),
    path('settings/', views.settings, name='settings'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/action/', views.notification_action, name='notification_action'),
    path('', views.home, name='home'),
]
