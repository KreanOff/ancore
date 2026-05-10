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
    path('tasks/edit-task/<int:task_id>/', tasks.edit_task, name='edit_task'),
    path('tasks/view-task/<int:task_id>/', tasks.view_task, name='view-task'),
        path('tasks/update/<int:task_id>/', tasks.update_task_status, name='update_task_status'),
    path('tasks/delete-attachment/<int:attachment_id>/', tasks.delete_attachment, name='delete_attachment'),
    path('tasks/delete/<int:task_id>/', tasks.delete_task, name='delete_task'),
    path('tasks/delete/', tasks.delete_tasks, name='delete_tasks'),
]
