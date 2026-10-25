from django.urls import path

from . import views, team_views, invitations


app_name = 'workplaces'

urlpatterns = [
    path('join/<uuid:token>/', invitations.join, name='join-link'),
    path('<int:workplace_id>/invite-links/', invitations.create_link, name='invite-link-create'),
    path('<int:workplace_id>/invite-links/<int:link_id>/revoke/', invitations.revoke_link, name='invite-link-revoke'),
    path('<int:workplace_id>/team/candidates/', team_views.member_candidates, name='member-candidates'),
    path('<int:workplace_id>/team/', team_views.team, name='team'),
    path('<int:workplace_id>/team/<int:member_id>/', team_views.member_update, name='member-update'),
    path('', views.workplaces, name='workplaces'),
    path('<int:workplace_id>/switch/', views.switch_workplace, name='switch'),
    path('<int:workplace_id>/default/', views.set_default_workplace, name='set-default'),
    path('<int:workplace_id>/favorites/toggle/', views.toggle_sidebar_favorite, name='toggle-sidebar-favorite'),
    path('<int:workplace_id>/favorites/reorder/', views.reorder_sidebar_favorites, name='reorder-sidebar-favorites'),
    path('<int:workplace_id>/settings/', views.update_workplace, name='update'),
    path('<int:workplace_id>/delete/', views.delete_workplace, name='delete'),
    path('<slug:workplace_slug>/', views.workplace_home, name='workplace-home'),
]
