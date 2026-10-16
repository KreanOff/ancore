from django.urls import path
from . import views

app_name = 'resources'
urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.edit, name='create'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('<int:pk>/delete/', views.delete, name='delete'),
]
