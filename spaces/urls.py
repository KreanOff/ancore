from django.urls import path
from . import views

app_name = 'spaces'
urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.edit, name='create'),
    path('items/', views.all_items, name='items'),
    path('items/<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('items/<int:pk>/action/', views.item_action, name='item_action'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('<int:pk>/favorite/', views.favorite, name='favorite'),
    path('<int:space_pk>/items/create/', views.item_edit, name='item_create'),
    path('<int:pk>/sprints/create/', views.sprint_create, name='sprint_create'),
    path('<int:pk>/sprints/<int:sprint_pk>/action/', views.sprint_action, name='sprint_action'),
    path('<int:pk>/members/', views.members, name='members'),
    path('<int:pk>/members/<int:member_pk>/remove/', views.remove_member, name='remove_member'),
    path('<int:pk>/configuration/', views.configuration, name='configuration'),
]
