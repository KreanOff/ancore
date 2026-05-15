from django.urls import path
from . import views

app_name = 'kanban'

urlpatterns = [
    path('', views.index, name='index'),
    path('create-card/', views.create_card, name='create_card'),
    path('create-column/', views.create_column, name='create_column'),
    path('move-card/', views.move_card, name='move_card'),
    path('reorder-cards/', views.reorder_cards, name='reorder_cards'),
    path('reorder-columns/', views.reorder_columns, name='reorder_columns'),
    path('column/<int:column_id>/update-name/', views.update_column_name, name='update_column_name'),
    path('column/<int:column_id>/delete/', views.delete_column, name='delete_column'),
    path('card/<int:card_id>/delete/', views.delete_card, name='delete_card'),
    path('card/<int:card_id>/', views.card_detail, name='card_detail'),
    path('card/<int:card_id>/toggle/', views.toggle_card_complete, name='toggle_card_complete'),
    path('card/<int:card_id>/update/', views.update_card, name='update_card'),
]
