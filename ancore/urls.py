from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from kanban import urls as kanban_urls
from planner import urls as planner_urls
from tasks import urls as tasks_urls
from documents import urls as documents_urls
from documents import workspace_urls as office_urls
from documents import suite_views
from resources import urls as resources_urls
from spaces import urls as spaces_urls, team_urls
from dashboard import pulpit_urls
from core.media import public_media

urlpatterns = [
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/dashboards/', include((pulpit_urls.urlpatterns, 'workplace_pulpits'), namespace='workplace_pulpits')),
    path('dashboards/', include('dashboard.pulpit_urls')),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/', include((spaces_urls.urlpatterns, 'workplace_spaces'), namespace='workplace_spaces')),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/teams/', include((team_urls.urlpatterns, 'workplace_teams'), namespace='workplace_teams')),
    path('', include('spaces.urls')),
    path('teams/', include('spaces.team_urls')),
    path('drive-office-service/<uuid:pk>/source/', suite_views.source, {'drive': True}, name='drive-office-service-source'),
    path('drive-office-service/<uuid:pk>/callback/', suite_views.callback, {'drive': True}, name='drive-office-service-callback'),
    path('office-service/<uuid:pk>/source/', suite_views.source, name='office-service-source'),
    path('office-service/<uuid:pk>/callback/', suite_views.callback, name='office-service-callback'),
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/tasks/', include((tasks_urls.urlpatterns, 'workplace_tasks'), namespace='workplace_tasks')),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/kanban/', include((kanban_urls.urlpatterns, 'workplace_kanban'), namespace='workplace_kanban')),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/calendar/', include((planner_urls.urlpatterns, 'workplace_planner'), namespace='workplace_planner')),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/documents/', include((documents_urls.urlpatterns, 'workplace_documents'), namespace='workplace_documents')),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/office/', include((office_urls.urlpatterns, 'workplace_office'), namespace='workplace_office')),
    path('workplaces/', include('workplaces.urls')),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/resources/', include((resources_urls.urlpatterns, 'workplace_resources'), namespace='workplace_resources')),
    path('resources/', include('resources.urls')),
    path('documents/', include('documents.urls')),
    path('office/', include('documents.workspace_urls')),
    path('tasks/', include('tasks.urls')),
    path('kanban/', include('kanban.urls')),
    path('calendar/', include('planner.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, view=public_media, document_root=settings.MEDIA_ROOT)
