from django.urls import path
from . import views
from . import suite_views as suite
from .move_views import move

app_name = 'documents'
urlpatterns = [
    path('', views.library, name='library'),
    path('libraries/create/', views.library_create, name='library-create'),
    path('libraries/<int:pk>/edit/', views.library_edit, name='library-edit'),
    path('libraries/<int:pk>/photo/', views.library_photo, name='library-photo'),
    path('libraries/<int:pk>/delete/', views.library_delete, name='library-delete'),
    path('upload/', views.upload, name='upload'),
    path('folders/<int:pk>/move/', move, {'drive': True, 'kind': 'folder'}, name='folder-move'),
    path('<uuid:pk>/move/', move, {'drive': True}, name='move'),
    path('folders/create/', views.folder_create, name='folder-create'),
    path('folders/<int:pk>/edit/', views.folder_edit, name='folder-edit'),
    path('folders/<int:pk>/delete/', views.folder_delete, name='folder-delete'),
    path('folders/<int:pk>/star/', views.folder_star, name='folder-star'),
    path('folders/<int:pk>/download/', views.folder_download, name='folder-download'),
    path('<uuid:pk>/', views.detail, name='detail'),
    path('<uuid:pk>/preview/', views.preview, name='preview'),
    path('<uuid:pk>/editor/', suite.editor, {'drive': True}, name='editor'),
    path('<uuid:pk>/rename/', suite.rename, {'drive': True}, name='rename'),
    path('<uuid:pk>/save/', suite.save_office, {'drive': True}, name='office-save'),
    path('<uuid:pk>/state/', suite.state, {'drive': True}, name='state'),
    path('<uuid:pk>/convert/', suite.convert, {'drive': True}, name='convert'),
    path('<uuid:pk>/content/', views.preview_content, name='preview-content'),
    path('<uuid:pk>/download/', views.download, name='download'),
    path('<uuid:pk>/star/', views.star, name='star'),
    path('<uuid:pk>/trash/', views.trash, name='trash'),
    path('<uuid:pk>/restore/', views.restore, name='restore'),
]
