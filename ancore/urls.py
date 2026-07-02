from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/tasks/', include(('tasks.urls', 'tasks'), namespace='workplace_tasks')),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/kanban/', include(('kanban.urls', 'kanban'), namespace='workplace_kanban')),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/contacts/', include(('contacts.urls', 'contacts'), namespace='workplace_contacts')),
    re_path(r'^workplaces/[-a-zA-Z0-9_]+/calendar/', include(('planner.urls', 'planner'), namespace='workplace_planner')),
    path('workplaces/', include('workplaces.urls')),
    path('tasks/', include('tasks.urls')),
    path('kanban/', include('kanban.urls')),
    path('contacts/', include('contacts.urls')),
    path('calendar/', include('planner.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
