from django.urls import path
from . import teams

app_name = 'teams'
urlpatterns = [
    path('', teams.index, name='index'),
    path('create/', teams.edit, name='create'),
    path('<int:pk>/', teams.detail, name='detail'),
    path('<int:pk>/edit/', teams.edit, name='edit'),
    path('<int:pk>/members/', teams.members, name='members'),
    path('<int:pk>/members/<int:member_pk>/remove/', teams.remove_member, name='remove_member'),
    path('<int:pk>/photo/', teams.photo, name='photo'),
]
