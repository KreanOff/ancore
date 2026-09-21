from django.urls import path
from . import editor_views as views
from . import suite_views as suite
from . import office_extras as extras

app_name = 'office'
urlpatterns = [
    path('', views.index, name='index'),
    path('create/', suite.create, name='create'),
    path('templates/create/', extras.from_template, name='from-template'),
    path('<uuid:pk>/template/', extras.template_toggle, name='template'),
    path('<uuid:pk>/history/', extras.history, name='history'),
    path('<uuid:pk>/versions/<int:version>/download/', extras.version_download, name='version-download'),
    path('<uuid:pk>/versions/<int:version>/restore/', extras.version_restore, name='version-restore'),
    path('create/text/', views.edit, name='create-text'),
    path('upload/', views.upload, name='upload'),
    path('<uuid:pk>/', views.edit, name='edit'),
    path('<uuid:pk>/editor/', suite.editor, name='editor'),
    path('<uuid:pk>/board/', suite.board_frame, name='board'),
    path('<uuid:pk>/board/save/', suite.save_board, name='board-save'),
    path('<uuid:pk>/save/', suite.save_office, name='office-save'),
    path('<uuid:pk>/state/', suite.state, name='state'),
    path('<uuid:pk>/convert/', suite.convert, name='convert'),
    path('<uuid:pk>/upgrade/', suite.upgrade_text, name='upgrade'),
    path('<uuid:pk>/preview/', views.preview, name='preview'),
    path('<uuid:pk>/download/', views.download, name='download'),
    path('<uuid:pk>/content/', views.content, name='content'),
    path('<uuid:pk>/import/', views.import_text, name='import'),
    path('<uuid:pk>/star/', views.action, {'operation': 'star'}, name='star'),
    path('<uuid:pk>/trash/', views.action, {'operation': 'trash'}, name='trash'),
    path('<uuid:pk>/restore/', views.action, {'operation': 'restore'}, name='restore'),
]
