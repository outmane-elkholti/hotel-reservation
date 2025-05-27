# reservations/urls.py - Ajouter ces URLs

from django.urls import path
from . import views

urlpatterns = [
    # URLs existantes...
    path('', views.reservation_list, name='reservation_list'),
    path('create/', views.create_reservation, name='create_reservation'),
    path('<int:pk>/', views.reservation_detail, name='reservation_detail'),
    path('<int:pk>/cancel/', views.cancel_reservation, name='cancel_reservation'),
    path('<int:pk>/confirmation/', views.reservation_confirmation, name='reservation_confirmation'),
    
    # Check-in et check-out
    path('<int:pk>/check-in/', views.check_in, name='check_in'),
    path('<int:pk>/check-out/', views.check_out, name='check_out'),
    
    # Gestion des paiements
    path('payment/<int:reservation_id>/', views.payment_form, name='payment_form'),
    path('payment/<int:reservation_id>/process/', views.process_payment, name='process_payment'),
    path('payment/create/<int:reservation_id>/', views.create_payment, name='create_payment'),
    
    # Gestion des services
    path('services/', views.manage_services, name='manage_services'),
    path('services/<int:pk>/update/', views.service_update, name='service_update'),
    path('services/<int:pk>/delete/', views.service_delete, name='service_delete'),
    
    # Recherche
    path('search/', views.search_results, name='search_results'),
    
    # NOUVELLES URLs pour les réceptionnistes
    path('receptionist/create/', views.receptionist_create_reservation, name='receptionist_create_reservation'),
    path('search-clients/', views.search_clients_ajax, name='search_clients_ajax'),
    path('create-client-ajax/', views.create_client_ajax, name='create_client_ajax'),
]