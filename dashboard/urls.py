from django.urls import path
from tasks.views.project_settings import project_field_settings
from . import views

urlpatterns = [
    path('global-search/', views.global_search, name='global_search'),
    path('settings/', views.settings, name='settings'),
    path('settings/project-fields/', project_field_settings, name='project_field_settings'),
    path('notifications/', views.notifications, name='notifications'),
    path('', views.home, name='home'),
]
