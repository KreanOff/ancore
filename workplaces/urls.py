from django.urls import path

from . import views


app_name = 'workplaces'

urlpatterns = [
    path('', views.workplaces, name='workplaces'),
    path('<int:workplace_id>/switch/', views.switch_workplace, name='switch'),
    path('<int:workplace_id>/settings/', views.update_workplace, name='update'),
    path('<int:workplace_id>/delete/', views.delete_workplace, name='delete'),
    path('<slug:workplace_slug>/', views.workplace_home, name='workplace-home'),
]
