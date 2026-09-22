from django.urls import path

from . import views, team_views


app_name = 'workplaces'

urlpatterns = [
    path('<int:workplace_id>/team/', team_views.team, name='team'),
    path('<int:workplace_id>/team/<int:member_id>/', team_views.member_update, name='member-update'),
    path('<int:workplace_id>/invitations/<int:invitation_id>/cancel/', team_views.invitation_cancel, name='invitation-cancel'),
    path('invitations/<int:invitation_id>/respond/', team_views.invitation_response, name='invitation-response'),
    path('', views.workplaces, name='workplaces'),
    path('<int:workplace_id>/switch/', views.switch_workplace, name='switch'),
    path('<int:workplace_id>/favorites/toggle/', views.toggle_sidebar_favorite, name='toggle-sidebar-favorite'),
    path('<int:workplace_id>/favorites/reorder/', views.reorder_sidebar_favorites, name='reorder-sidebar-favorites'),
    path('<int:workplace_id>/settings/', views.update_workplace, name='update'),
    path('<int:workplace_id>/delete/', views.delete_workplace, name='delete'),
    path('<slug:workplace_slug>/', views.workplace_home, name='workplace-home'),
]
