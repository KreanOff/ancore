from django.urls import path
from . import views

app_name = 'planner'

urlpatterns = [
    path('', views.index, name='index'),
    path('sidebar/', views.sidebar, name='sidebar'),
    path('events/', views.events_list, name='events'),
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:event_id>/update/', views.update_event, name='update_event'),
    path('events/<int:event_id>/delete/', views.delete_event, name='delete_event'),
]
