from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('tasks/', views.tasks, name='tasks'),
    path('kanban/', views.kanban, name='kanban'),
    path('calendar/', views.calendar, name='calendar'),
    path('tickets/', views.tickets, name='tickets'),
]
