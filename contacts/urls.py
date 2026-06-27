from django.urls import path

from . import views

app_name = 'contacts'

urlpatterns = [
    path('', views.contacts, name='contacts'),
    path('users/', views.user_directory, name='user-directory'),
    path('users/lookup/', views.lookup_ancore_login, name='lookup-ancore-login'),
    path('users/<int:user_id>/add/', views.add_user_contact, name='add-user-contact'),
    path('companies/', views.companies, name='companies'),
    path('companies/<int:company_id>/', views.view_company, name='view-company'),
    path('companies/<int:company_id>/edit/', views.edit_company, name='edit-company'),
    path('companies/<int:company_id>/delete/', views.delete_company, name='delete-company'),
    path('guests/', views.guest_contacts, name='guests'),
    path('view-contact/<int:contact_id>/', views.view_contact, name='view-contact'),
    path('view-contact/<int:contact_id>/edit/', views.edit_contact, name='edit-contact'),
    path('delete/<int:contact_id>/', views.delete_contact, name='delete'),
]
