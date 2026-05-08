from django.urls import path
from django.contrib.auth import views as auth_views
from .views import dashboard, tasks, kanban, calendar, tickets, auth

urlpatterns = [
    path('', dashboard.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='core/registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', auth.register, name='register'),
    path('tasks/', tasks.tasks, name='tasks'),
    path('kanban/', kanban.kanban, name='kanban'),
    path('calendar/', calendar.calendar, name='calendar'),
    path('tickets/', tickets.tickets, name='tickets'),
    path('tasks/create-task/', tasks.create_task, name='create_task'),
    path('tasks/view-edit-task/<int:task_id>/', tasks.view_edit_task, name='view_edit_task'),
    path('tasks/update/<int:task_id>/', tasks.update_task_status, name='update_task_status'),
]
