from django.urls import path
from . import pulpit_views as views

app_name = 'pulpits'
urlpatterns = [
    path('manage/<int:pk>/gadgets/quick-add/', views.gadget_quick_add, {'management': True}, name='manage_gadget_quick_add'),
    path('manage/<int:pk>/gadgets/', views.gadgets, {'management': True}, name='manage_gadgets'),
    path('manage/<int:pk>/gadgets/add/', views.gadget_edit, {'management': True}, name='manage_gadget_add'),
    path('manage/<int:pk>/gadgets/<int:gadget_pk>/edit/', views.gadget_edit, {'management': True}, name='manage_gadget_edit'),
    path('manage/<int:pk>/gadgets/<int:gadget_pk>/delete/', views.gadget_delete, {'management': True}, name='manage_gadget_delete'),
    path('', views.index, name='index'),
    path('search/', views.search, name='search'),
    path('create/', views.edit, name='create'),
    path('manage/', views.manage, name='manage'),
    path('manage/create/', views.edit, {'management': True}, name='manage_create'),
    path('manage/<int:pk>/edit/', views.edit, {'management': True}, name='manage_edit'),
    path('manage/<int:pk>/access/', views.access, {'management': True}, name='manage_access'),
    path('manage/<int:pk>/delete/', views.delete, {'management': True}, name='manage_delete'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('<int:pk>/access/', views.access, name='access'),
    path('<int:pk>/delete/', views.delete, name='delete'),
    path('<int:pk>/favorite/', views.favorite, name='favorite'),
    path('<int:pk>/arrange/', views.arrange, name='arrange'),
    path('<int:pk>/gadgets/', views.gadgets, name='gadgets'),
    path('<int:pk>/gadgets/quick-add/', views.gadget_quick_add, name='gadget_quick_add'),
    path('<int:pk>/gadgets/add/', views.gadget_edit, name='gadget_add'),
    path('<int:pk>/gadgets/<int:gadget_pk>/edit/', views.gadget_edit, name='gadget_edit'),
    path('<int:pk>/gadgets/<int:gadget_pk>/delete/', views.gadget_delete, name='gadget_delete'),
]
