from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.AccountLoginView.as_view(), name='login'),
    path('logout/', views.AccountLogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('profile/status/', views.update_presence_status, name='update_presence_status'),
    path('profile/add-account/', views.add_account, name='add_account'),
    path('profile/switch-account/', views.switch_account, name='switch_account'),
    path('profile/remove-account/', views.remove_account, name='remove_account'),
    path('presence/ping/', views.presence_ping, name='presence_ping'),
]
