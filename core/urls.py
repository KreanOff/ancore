from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('tasks/', views.tasks, name='tasks'),
    path('kanban/', views.kanban, name='kanban'),
    path('calendar/', views.calendar, name='calendar'),
    path('tickets/', views.tickets, name='tickets'),
]
