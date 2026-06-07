from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', views.AccountLogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('profile/add-account/', views.add_account, name='add_account'),
    path('profile/switch-account/', views.switch_account, name='switch_account'),
    path('profile/remove-account/', views.remove_account, name='remove_account'),
    path('presence/ping/', views.presence_ping, name='presence_ping'),
]
