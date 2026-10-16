from django.urls import path
from . import api, views

app_name = 'resources'
urlpatterns = [
    path('api/v1/', api.collection, name='api-list'),
    path('api/v1/new/', api.new, name='api-new'),
    path('api/v1/<int:pk>/', api.detail, name='api-detail'),
    path('api/v1/<int:pk>/delete/', api.delete, name='api-delete'),
    path('', views.index, name='index'),
    path('create/', views.edit, name='create'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('<int:pk>/delete/', views.delete, name='delete'),
]
