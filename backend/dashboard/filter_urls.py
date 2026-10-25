from django.urls import path
from . import filter_views as views
from . import filter_sharing

app_name = 'filters'
urlpatterns = [
    path('', views.index, name='index'),
    path('manage/', views.manage, name='manage'),
    path('manage/new/', views.edit, {'management': True}, name='manage_create'),
    path('manage/<int:pk>/edit/', views.edit, {'management': True}, name='manage_edit'),
    path('search/', views.search, name='search'),
    path('lookup/', views.lookup, name='lookup'),
    path('new/', views.edit, name='create'),
    path('<int:pk>/', views.search, name='detail'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('<int:pk>/team/', filter_sharing.team, name='team'),
    path('<int:pk>/team/candidates/', filter_sharing.candidates, name='team_candidates'),
    path('<int:pk>/save/', views.save_query, name='save'),
    path('<int:pk>/favorite/', views.favorite, name='favorite'),
    path('<int:pk>/delete/', views.delete, name='delete'),
]
