from django.urls import path
from . import pulpit_views as views

app_name = 'pulpits'
urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.edit, name='create'),
    path('manage/', views.manage, name='manage'),
    path('manage/create/', views.edit, {'management': True}, name='manage_create'),
    path('manage/<int:pk>/edit/', views.edit, {'management': True}, name='manage_edit'),
    path('manage/<int:pk>/copy/', views.edit, {'management': True, 'copy': True}, name='manage_copy'),
    path('manage/<int:pk>/groups/', views.dashboard_groups, {'management': True}, name='manage_dashboard_groups'),
    path('manage/<int:pk>/delete/', views.delete, {'management': True}, name='manage_delete'),
    path('groups/', views.groups, name='groups'),
    path('groups/create/', views.group_edit, name='group_create'),
    path('groups/<int:pk>/edit/', views.group_edit, name='group_edit'),
    path('groups/<int:pk>/delete/', views.group_delete, name='group_delete'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('<int:pk>/copy/', views.edit, {'copy': True}, name='copy'),
    path('<int:pk>/delete/', views.delete, name='delete'),
    path('<int:pk>/favorite/', views.favorite, name='favorite'),
    path('<int:pk>/groups/', views.dashboard_groups, name='dashboard_groups'),
    path('<int:pk>/arrange/', views.arrange, name='arrange'),
    path('<int:pk>/gadgets/add/', views.gadget_edit, name='gadget_add'),
    path('<int:pk>/gadgets/<int:gadget_pk>/edit/', views.gadget_edit, name='gadget_edit'),
    path('<int:pk>/gadgets/<int:gadget_pk>/delete/', views.gadget_delete, name='gadget_delete'),
]
