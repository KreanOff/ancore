from django.urls import path
from . import views
from .api import accounts_api

urlpatterns = [
    path('api/v1/page/', accounts_api, name='accounts-api'),
    path('login/', views.AccountLoginView.as_view(), name='login'),
    path('logout/', views.AccountLogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('register/workspace/', views.register_workspace, name='register_workspace'),
    path('workspaces/', views.select_workspace, name='select_workspace'),
    path('profile/', views.profile, name='profile'),
    path('profile/banner/', views.update_profile_banner, name='update_profile_banner'),
    path('profile/status/', views.update_presence_status, name='update_presence_status'),
    path('presence/ping/', views.presence_ping, name='presence_ping'),
]
