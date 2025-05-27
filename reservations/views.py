from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum
from datetime import datetime, timedelta
import json
from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import Client
from accounts.utils import send_reservation_confirmation_email, send_payment_confirmation_email, send_cancellation_email
from rooms.models import Room
from .models import Reservation, Payment, Service, ReservationStatus
from .forms import ReservationForm, PaymentForm, ServiceForm, ReservationStatusForm
# reservations/views.py - Ajouter ces vues pour les réceptionnistes

from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.models import User

@login_required
def receptionist_create_reservation(request):
    """Vue spéciale pour les réceptionnistes pour créer des réservations"""
    
    # Vérifier si l'utilisateur est réceptionniste, manager ou admin
    if not request.user.profile.role or request.user.profile.role.name not in ['Réceptionniste', 'Manager', 'Administrateur']:
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        client_id = request.POST.get('client_id')
        check_in_date = request.POST.get('check_in_date')
        check_out_date = request.POST.get('check_out_date')
        room_ids = request.POST.getlist('rooms')
        service_ids = request.POST.getlist('services')
        notes = request.POST.get('notes', '')
        
        try:
            # Valider le client
            if not client_id:
                messages.error(request, "Veuillez sélectionner un client.")
                return redirect('receptionist_create_reservation')
            
            client = get_object_or_404(Client, id=client_id)
            
            # Valider les dates
            if not check_in_date or not check_out_date:
                messages.error(request, "Veuillez sélectionner les dates d'arrivée et de départ.")
                return redirect('receptionist_create_reservation')
            
            check_in = datetime.strptime(check_in_date, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_date, '%Y-%m-%d').date()
            
            if check_out <= check_in:
                messages.error(request, "La date de départ doit être postérieure à la date d'arrivée.")
                return redirect('receptionist_create_reservation')
            
            # Valider les chambres
            if not room_ids:
                messages.error(request, "Veuillez sélectionner au moins une chambre.")
                return redirect('receptionist_create_reservation')
            
            rooms = Room.objects.filter(id__in=room_ids, is_available=True)
            if len(rooms) != len(room_ids):
                messages.error(request, "Une ou plusieurs chambres sélectionnées ne sont pas disponibles.")
                return redirect('receptionist_create_reservation')
            
            # Créer la réservation
            reservation = Reservation.objects.create(
                client=client,
                check_in_date=check_in,
                check_out_date=check_out,
                notes=notes,
                status=ReservationStatus.PENDING,
                total_amount=0  # Sera recalculé après
            )
            
            # Ajouter les chambres
            reservation.rooms.set(rooms)
            
            # Ajouter les services si sélectionnés
            if service_ids:
                services = Service.objects.filter(id__in=service_ids, is_available=True)
                reservation.services.set(services)
            
            # Recalculer le montant total
            reservation.total_amount = reservation.calculate_total()
            reservation.save()
            
            # Envoyer l'email de confirmation
            try:
                from accounts.utils import send_reservation_confirmation_email
                if send_reservation_confirmation_email(reservation):
                    messages.success(
                        request, 
                        f'Réservation #{reservation.id} créée avec succès ! Email de confirmation envoyé à {client.profile.user.email}.'
                    )
                else:
                    messages.success(request, f'Réservation #{reservation.id} créée avec succès !')
                    messages.warning(request, 'L\'email de confirmation n\'a pas pu être envoyé.')
            except Exception as e:
                messages.success(request, f'Réservation #{reservation.id} créée avec succès !')
                messages.warning(request, f'Erreur lors de l\'envoi de l\'email: {str(e)}')
            
            # Rediriger vers les détails de la réservation
            return redirect('reservation_detail', pk=reservation.id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la création de la réservation: {str(e)}")
            return redirect('receptionist_create_reservation')
    
    # GET request - afficher le formulaire
    # Récupérer toutes les chambres disponibles
    available_rooms = Room.objects.filter(is_available=True).select_related('room_type')
    
    # Récupérer tous les services disponibles
    available_services = Service.objects.filter(is_available=True)
    
    # Récupérer tous les clients pour la recherche (limité pour performance)
    recent_clients = Client.objects.select_related('profile__user').order_by('-profile__date_joined')[:50]
    
    context = {
        'available_rooms': available_rooms,
        'available_services': available_services,
        'recent_clients': recent_clients,
    }
    
    return render(request, 'reservations/receptionist_reservation_form.html', context)


@login_required
def search_clients_ajax(request):
    """Recherche AJAX de clients pour les réceptionnistes"""
    
    # Vérifier les permissions
    if not request.user.profile.role or request.user.profile.role.name not in ['Réceptionniste', 'Manager', 'Administrateur']:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'clients': []})
    
    # Rechercher dans les noms, emails et téléphones
    clients = Client.objects.filter(
        Q(profile__user__first_name__icontains=query) |
        Q(profile__user__last_name__icontains=query) |
        Q(profile__user__email__icontains=query) |
        Q(profile__phone__icontains=query)
    ).select_related('profile__user')[:10]  # Limiter à 10 résultats
    
    client_data = []
    for client in clients:
        full_name = client.profile.user.get_full_name() or client.profile.user.username
        client_data.append({
            'id': client.id,
            'full_name': full_name,
            'email': client.profile.user.email,
            'phone': client.profile.phone or '',
        })
    
    return JsonResponse({'clients': client_data})


@login_required
def create_client_ajax(request):
    """Création AJAX d'un nouveau client pour les réceptionnistes"""
    
    # Vérifier les permissions
    if not request.user.profile.role or request.user.profile.role.name not in ['Réceptionniste', 'Manager', 'Administrateur']:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    try:
        # Récupérer les données
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        
        # Validation
        if not first_name or not last_name or not email:
            return JsonResponse({'error': 'Prénom, nom et email sont requis'}, status=400)
        
        # Vérifier si l'email existe déjà
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Un utilisateur avec cet email existe déjà'}, status=400)
        
        # Générer un nom d'utilisateur unique
        username = f"{first_name.lower()}.{last_name.lower()}"
        counter = 1
        original_username = username
        while User.objects.filter(username=username).exists():
            username = f"{original_username}{counter}"
            counter += 1
        
        # Créer l'utilisateur avec un mot de passe temporaire
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=temp_password
        )
        
        # Mettre à jour le profil
        profile = user.profile
        profile.phone = phone
        profile.save()
        
        # Récupérer ou créer le client
        client, created = Client.objects.get_or_create(
            profile=profile,
            defaults={'address': address}
        )
        
        # Retourner les données du client créé
        return JsonResponse({
            'success': True,
            'client': {
                'id': client.id,
                'full_name': user.get_full_name(),
                'email': user.email,
                'phone': phone,
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Erreur lors de la création: {str(e)}'}, status=500)
@login_required
def reservation_list(request):
    """Affiche la liste des réservations de l'utilisateur ou toutes les réservations pour le personnel"""
    
    # Déterminer si l'utilisateur est un client ou un employé
    is_staff = request.user.profile.role and request.user.profile.role.name in ['Administrateur', 'Manager', 'Réceptionniste']
    
    if is_staff:
        # Personnel: afficher toutes les réservations avec filtres
        reservations = Reservation.objects.all().order_by('-created_at')
        
        # Filtrer par statut si spécifié
        status = request.GET.get('status')
        if status:
            reservations = reservations.filter(status=status)
        
        # Filtrer par date si spécifié
        date_filter = request.GET.get('date_filter')
        if date_filter == 'today':
            today = timezone.now().date()
            reservations = reservations.filter(
                Q(check_in_date=today) | Q(check_out_date=today)
            )
        elif date_filter == 'upcoming':
            today = timezone.now().date()
            reservations = reservations.filter(check_in_date__gt=today)
        elif date_filter == 'past':
            today = timezone.now().date()
            reservations = reservations.filter(check_out_date__lt=today)
    else:
        # Client: afficher uniquement ses réservations
        try:
            client = Client.objects.get(profile__user=request.user)
            reservations = Reservation.objects.filter(client=client).order_by('-created_at')
        except Client.DoesNotExist:
            messages.error(request, "Votre profil client n'est pas configuré correctement.")
            return redirect('dashboard')
    
    context = {
        'reservations': reservations,
        'is_staff': is_staff,
        'statuses': ReservationStatus.choices,
        'selected_status': request.GET.get('status', ''),
        'date_filter': request.GET.get('date_filter', '')
    }
    
    return render(request, 'reservations/reservation_list.html', context)

@login_required
def reservation_detail(request, pk):
    """Affiche les détails d'une réservation"""
    
    reservation = get_object_or_404(Reservation, pk=pk)
    
    # Vérifier si l'utilisateur a le droit de voir cette réservation
    is_staff = request.user.profile.role and request.user.profile.role.name in ['Administrateur', 'Manager', 'Réceptionniste']
    is_owner = hasattr(request.user.profile, 'client') and request.user.profile.client == reservation.client
    
    if not (is_staff or is_owner):
        messages.error(request, "Vous n'avez pas l'autorisation de voir cette réservation.")
        return redirect('reservation_list')
    
    # Obtenir les paiements liés à cette réservation
    payments = Payment.objects.filter(reservation=reservation)
    total_paid = sum(payment.amount for payment in payments if payment.is_confirmed)
    balance = reservation.total_amount - total_paid
    
    # Calculer le nombre de nuits
    nights = (reservation.check_out_date - reservation.check_in_date).days
    
    # Pour le changement de statut (uniquement pour le personnel)
    if is_staff:
        if request.method == 'POST':
            status_form = ReservationStatusForm(request.POST, instance=reservation)
            if status_form.is_valid():
                status_form.save()
                messages.success(request, 'Statut de la réservation mis à jour!')
                return redirect('reservation_detail', pk=reservation.pk)
        else:
            status_form = ReservationStatusForm(instance=reservation)
    else:
        status_form = None
    
    context = {
        'reservation': reservation,
        'payments': payments,
        'total_paid': total_paid,
        'balance': balance,
        'is_staff': is_staff,
        'status_form': status_form,
        'nights': nights
    }
    
    return render(request, 'reservations/reservation_detail.html', context)

@login_required
def create_reservation(request):
    """Crée une nouvelle réservation"""
    
    # Obtenir les données de recherche de disponibilité depuis la session
    search_data = request.session.get('search', None)
    initial_data = {}
    
    if search_data:
        initial_data['check_in_date'] = datetime.fromisoformat(search_data['check_in'])
        initial_data['check_out_date'] = datetime.fromisoformat(search_data['check_out'])
    
    # Obtenir l'ID de la chambre depuis les paramètres d'URL
    room_id = request.GET.get('room_id')
    selected_rooms = []
    
    if room_id:
        try:
            selected_rooms = [Room.objects.get(id=room_id)]
        except Room.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = ReservationForm(request.POST, user=request.user)
        if form.is_valid():
            # Créer la réservation sans l'enregistrer
            reservation = form.save(commit=False)
            
            # Si l'utilisateur est un client, définir automatiquement le client
            if not request.user.is_staff:
                try:
                    client = Client.objects.get(profile__user=request.user)
                    reservation.client = client
                except Client.DoesNotExist:
                    messages.error(request, "Votre profil client n'est pas configuré correctement.")
                    return redirect('dashboard')
            
            # Définir un montant temporaire pour l'enregistrement initial
            reservation.total_amount = 0
            
            # Enregistrer pour obtenir un ID
            reservation.save()
            
            # Ajouter les chambres et services (relations many-to-many)
            reservation.rooms.set(form.cleaned_data['rooms'])
            if form.cleaned_data.get('services'):
                reservation.services.set(form.cleaned_data['services'])
            
            # Recalculer et mettre à jour le montant total
            reservation.total_amount = reservation.calculate_total()
            reservation.save()
            
            # Envoyer l'email de confirmation de réservation
            try:
                if send_reservation_confirmation_email(reservation):
                    messages.success(request, f'Réservation créée avec succès! Un email de confirmation a été envoyé à {reservation.client.profile.user.email}.')
                else:
                    messages.success(request, 'Réservation créée avec succès!')
                    messages.warning(request, 'L\'email de confirmation n\'a pas pu être envoyé.')
            except Exception as e:
                messages.success(request, 'Réservation créée avec succès!')
                messages.warning(request, f'Erreur lors de l\'envoi de l\'email: {str(e)}')
            
            # Rediriger vers le paiement
            return redirect('payment_form', reservation_id=reservation.id)
    else:
        form = ReservationForm(user=request.user, initial=initial_data)
        if selected_rooms:
            form.fields['rooms'].initial = selected_rooms
    
    return render(request, 'reservations/reservation_form.html', {'form': form})

@login_required
def create_payment(request, reservation_id):
    """Ajoute un paiement à une réservation"""
    
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    
    # Vérifier si l'utilisateur a le droit d'ajouter un paiement
    is_staff = request.user.profile.role and request.user.profile.role.name in ['Administrateur', 'Manager', 'Réceptionniste']
    is_owner = hasattr(request.user.profile, 'client') and request.user.profile.client == reservation.client
    
    if not (is_staff or is_owner):
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
        return redirect('reservation_list')
    
    # Calculer le solde restant
    existing_payments = Payment.objects.filter(reservation=reservation, is_confirmed=True)
    total_paid = sum(payment.amount for payment in existing_payments)
    balance = reservation.total_amount - total_paid
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, reservation=reservation)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.reservation = reservation
            
            # Simuler une confirmation de paiement (dans un système réel, cela passerait par un service de paiement)
            # Pour le moment, tous les paiements sont automatiquement confirmés
            payment.is_confirmed = True
            payment.save()
            
            # Mettre à jour le statut de la réservation si entièrement payée
            new_total_paid = total_paid + payment.amount
            if new_total_paid >= reservation.total_amount:
                reservation.status = ReservationStatus.CONFIRMED
                reservation.save()
            
            # Envoyer l'email de confirmation de paiement
            try:
                if send_payment_confirmation_email(payment):
                    messages.success(request, f'Paiement effectué avec succès! Un email de confirmation a été envoyé à {reservation.client.profile.user.email}.')
                else:
                    messages.success(request, 'Paiement effectué avec succès!')
                    messages.warning(request, 'L\'email de confirmation n\'a pas pu être envoyé.')
            except Exception as e:
                messages.success(request, 'Paiement effectué avec succès!')
                messages.warning(request, f'Erreur lors de l\'envoi de l\'email: {str(e)}')
            
            # Rediriger vers la confirmation de réservation
            return redirect('reservation_confirmation', pk=reservation.id)
    else:
        # Préremplir le montant avec le solde restant
        form = PaymentForm(reservation=reservation, initial={'amount': balance})
    
    # Calculer le nombre de nuits
    nights = (reservation.check_out_date - reservation.check_in_date).days
    
    context = {
        'form': form,
        'reservation': reservation,
        'total_paid': total_paid,
        'balance': balance,
        'nights': nights
    }
    
    return render(request, 'reservations/payment_form.html', context)

@login_required
def reservation_confirmation(request, pk):
    """Affiche la confirmation d'une réservation"""
    
    reservation = get_object_or_404(Reservation, pk=pk)
    
    # Vérifier si l'utilisateur a le droit de voir cette réservation
    is_staff = request.user.profile.role and request.user.profile.role.name in ['Administrateur', 'Manager', 'Réceptionniste']
    is_owner = hasattr(request.user.profile, 'client') and request.user.profile.client == reservation.client
    
    if not (is_staff or is_owner):
        messages.error(request, "Vous n'avez pas l'autorisation de voir cette réservation.")
        return redirect('reservation_list')
    
    # Obtenir les paiements liés à cette réservation
    payments = Payment.objects.filter(reservation=reservation, is_confirmed=True)
    total_paid = sum(payment.amount for payment in payments)
    
    # Calculer le nombre de nuits
    nights = (reservation.check_out_date - reservation.check_in_date).days
    
    context = {
        'reservation': reservation,
        'payments': payments,
        'total_paid': total_paid,
        'nights': nights
    }
    
    return render(request, 'reservations/reservation_confirmation.html', context)

@login_required
def cancel_reservation(request, pk):
    """Annule une réservation"""
    
    reservation = get_object_or_404(Reservation, pk=pk)
    
    # Vérifier si l'utilisateur a le droit d'annuler cette réservation
    is_staff = request.user.profile.role and request.user.profile.role.name in ['Administrateur', 'Manager', 'Réceptionniste']
    is_owner = hasattr(request.user.profile, 'client') and request.user.profile.client == reservation.client
    
    if not (is_staff or is_owner):
        messages.error(request, "Vous n'avez pas l'autorisation d'annuler cette réservation.")
        return redirect('reservation_list')
    
    # Vérifier si la réservation peut être annulée
    if reservation.status in [ReservationStatus.CHECKED_IN, ReservationStatus.CHECKED_OUT]:
        messages.error(request, "Cette réservation ne peut plus être annulée.")
        return redirect('reservation_detail', pk=reservation.pk)
    
    if request.method == 'POST':
        reservation.status = ReservationStatus.CANCELLED
        reservation.save()
        
        # Envoyer l'email d'annulation
        try:
            if send_cancellation_email(reservation):
                messages.success(request, f'Réservation annulée avec succès! Un email de confirmation a été envoyé à {reservation.client.profile.user.email}.')
            else:
                messages.success(request, 'Réservation annulée avec succès!')
                messages.warning(request, 'L\'email de confirmation d\'annulation n\'a pas pu être envoyé.')
        except Exception as e:
            messages.success(request, 'Réservation annulée avec succès!')
            messages.warning(request, f'Erreur lors de l\'envoi de l\'email: {str(e)}')
        
        return redirect('reservation_list')
    
    return render(request, 'reservations/reservation_cancel.html', {'reservation': reservation})

@login_required
def check_in(request, pk):
    """Effectue le check-in d'une réservation"""
    
    # Vérifier si l'utilisateur est un membre du personnel
    if not request.user.profile.role or request.user.profile.role.name not in ['Administrateur', 'Manager', 'Réceptionniste']:
        messages.error(request, "Vous n'avez pas l'autorisation d'effectuer cette action.")
        return redirect('reservation_list')
    
    # CORRECTION: Récupérer la réservation AVANT les vérifications
    reservation = get_object_or_404(Reservation, pk=pk)
    
    # Vérifier si la réservation peut faire l'objet d'un check-in
    if reservation.status != ReservationStatus.CONFIRMED:
        messages.error(request, "Cette réservation ne peut pas faire l'objet d'un check-in.")
        return redirect('reservation_detail', pk=reservation.pk)
    
    # Vérifier si la date actuelle est bien la date d'arrivée ou postérieure
    today = timezone.now().date()
    if today < reservation.check_in_date:
        messages.warning(request, "Attention: check-in anticipé. La date d'arrivée prévue est le " + 
                        reservation.check_in_date.strftime("%d/%m/%Y"))
    
    if request.method == 'POST':
        reservation.status = ReservationStatus.CHECKED_IN
        reservation.save()
        
        # Mettre à jour le statut des chambres (les marquer comme occupées)
        for room in reservation.rooms.all():
            room.status = 'OCCUPIED'
            room.save()
            
        messages.success(request, 'Check-in effectué avec succès!')
        return redirect('reservation_detail', pk=reservation.pk)
    
    # Calculer le montant restant à payer
    payments = Payment.objects.filter(reservation=reservation, is_confirmed=True)
    total_paid = sum(payment.amount for payment in payments)
    balance = reservation.total_amount - total_paid
    
    # Calculer le nombre de nuits
    nights = (reservation.check_out_date - reservation.check_in_date).days
    
    context = {
        'reservation': reservation,
        'balance': balance,
        'total_paid': total_paid,
        'nights': nights
    }
    
    return render(request, 'reservations/check_in.html', context)

@login_required
def check_out(request, pk):
    """Effectue le check-out d'une réservation"""
    
    # Vérifier si l'utilisateur est un membre du personnel
    if not request.user.profile.role or request.user.profile.role.name not in ['Administrateur', 'Manager', 'Réceptionniste']:
        messages.error(request, "Vous n'avez pas l'autorisation d'effectuer cette action.")
        return redirect('reservation_list')
    
    reservation = get_object_or_404(Reservation, pk=pk)
    
    # Vérifier si la réservation peut faire l'objet d'un check-out
    if reservation.status != ReservationStatus.CHECKED_IN:
        messages.error(request, "Cette réservation ne peut pas faire l'objet d'un check-out.")
        return redirect('reservation_detail', pk=reservation.pk)
    
    # Vérifier s'il y a des montants impayés
    payments = Payment.objects.filter(reservation=reservation, is_confirmed=True)
    total_paid = sum(payment.amount for payment in payments)
    balance = reservation.total_amount - total_paid
    
    if request.method == 'POST':
        # Vérifier si tous les paiements ont été effectués
        if balance > 0 and 'force_checkout' not in request.POST:
            messages.warning(request, f"Il reste un solde de {balance}€ à régler. Veuillez effectuer le paiement avant le check-out ou cocher la case pour forcer le check-out.")
            return redirect('check_out', pk=reservation.pk)
        
        reservation.status = ReservationStatus.CHECKED_OUT
        reservation.save()
        
        # Libérer les chambres (les marquer comme disponibles mais nécessitant un nettoyage)
        for room in reservation.rooms.all():
            room.status = 'CLEANING'
            room.save()
        
        messages.success(request, 'Check-out effectué avec succès!')
        return redirect('reservation_detail', pk=reservation.pk)
    
    # Récupérer les services additionnels consommés pendant le séjour
    extra_services = []  # Dans un système réel, cela viendrait d'un autre modèle
    
    context = {
        'reservation': reservation,
        'balance': balance,
        'total_paid': total_paid,
        'extra_services': extra_services
    }
    
    return render(request, 'reservations/check_out.html', context)

@login_required
def manage_services(request):
    """Gère les services additionnels"""
    
    # Vérifier si l'utilisateur a la permission
    if not request.user.profile.role or request.user.profile.role.name not in ['Administrateur', 'Manager']:
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
        return redirect('dashboard')
    
    services = Service.objects.all()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        is_available = 'is_available' in request.POST
        
        if not name or not price:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return redirect('manage_services')
        
        Service.objects.create(
            name=name,
            description=description,
            price=float(price),
            is_available=is_available
        )
        
        messages.success(request, 'Service ajouté avec succès!')
        return redirect('manage_services')
    
    return render(request, 'reservations/service_list.html', {'services': services})

@login_required
def service_update(request, pk):
    """Met à jour un service existant"""
    
    # Vérifier si l'utilisateur a la permission
    if not request.user.profile.role or request.user.profile.role.name not in ['Administrateur', 'Manager']:
        messages.error(request, "Vous n'avez pas l'autorisation de modifier un service.")
        return redirect('manage_services')
    
    service = get_object_or_404(Service, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        is_available = 'is_available' in request.POST
        
        if not name or not price:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return redirect('manage_services')
        
        service.name = name
        service.description = description
        service.price = float(price)
        service.is_available = is_available
        service.save()
        
        messages.success(request, f'Service "{name}" mis à jour avec succès!')
        
    return redirect('manage_services')

@login_required
def service_delete(request, pk):
    """Supprime un service"""
    
    # Vérifier si l'utilisateur a la permission
    if not request.user.profile.role or request.user.profile.role.name not in ['Administrateur', 'Manager']:
        messages.error(request, "Vous n'avez pas l'autorisation de supprimer un service.")
        return redirect('manage_services')
    
    service = get_object_or_404(Service, pk=pk)
    
    if request.method == 'POST':
        name = service.name
        service.delete()
        messages.success(request, f'Service "{name}" supprimé avec succès!')
        
    return redirect('manage_services')

@login_required
def payment_form(request, reservation_id):
    """Affiche le formulaire de paiement pour une réservation"""
    
    # Récupérer la réservation
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Vérifier que l'utilisateur est bien le propriétaire de la réservation
    if reservation.client.profile.user != request.user and not request.user.is_staff:
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette réservation.")
        return redirect('dashboard')
    
    # Calculer le nombre de nuits
    nights = (reservation.check_out_date - reservation.check_in_date).days
    
    # Calculer le montant restant à payer
    payments = Payment.objects.filter(reservation=reservation, is_confirmed=True)
    total_paid = sum(payment.amount for payment in payments)
    balance = reservation.total_amount - total_paid
    
    context = {
        'reservation': reservation,
        'nights': nights,
        'total_paid': total_paid,
        'balance': balance
    }
    
    return render(request, 'reservations/payment_form.html', context)

@login_required
def process_payment(request, reservation_id):
    """Traite un paiement pour une réservation"""
    
    if request.method != 'POST':
        return redirect('payment_form', reservation_id=reservation_id)
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Vérifier que l'utilisateur est bien le propriétaire de la réservation
    if reservation.client.profile.user != request.user and not request.user.is_staff:
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette réservation.")
        return redirect('dashboard')
    
    # Calculer le montant restant à payer
    payments = Payment.objects.filter(reservation=reservation, is_confirmed=True)
    total_paid = sum(payment.amount for payment in payments)
    balance = reservation.total_amount - total_paid
    
    # Traiter le paiement (simulation)
    payment_method = request.POST.get('payment_method')
    reference = request.POST.get('reference', '')
    
    # Vérifier que le formulaire est valide
    if not payment_method:
        messages.error(request, "Veuillez sélectionner une méthode de paiement.")
        return redirect('payment_form', reservation_id=reservation_id)
    
    # Créer un enregistrement de paiement
    payment = Payment.objects.create(
        reservation=reservation,
        amount=balance,  # Payer le solde restant
        payment_method=payment_method,
        reference=reference,
        is_confirmed=True  # Dans un environnement de production, cela dépendrait de la réponse du processeur de paiement
    )
    
    # Mettre à jour le statut de la réservation
    reservation.status = ReservationStatus.CONFIRMED
    reservation.save()
    
    # Envoyer l'email de confirmation de paiement
    try:
        if send_payment_confirmation_email(payment):
            messages.success(request, f"Paiement effectué avec succès! Votre réservation est confirmée. Un email de confirmation a été envoyé à {reservation.client.profile.user.email}.")
        else:
            messages.success(request, "Paiement effectué avec succès! Votre réservation est confirmée.")
            messages.warning(request, 'L\'email de confirmation n\'a pas pu être envoyé.')
    except Exception as e:
        messages.success(request, "Paiement effectué avec succès! Votre réservation est confirmée.")
        messages.warning(request, f'Erreur lors de l\'envoi de l\'email: {str(e)}')
    
    # Rediriger vers la page de confirmation
    return redirect('reservation_confirmation', pk=reservation.id)

@login_required
def search_results(request):
    """Affiche les résultats de recherche pour clients ou réservations"""
    
    # Vérifier si l'utilisateur a les droits d'accès
    if not request.user.profile.role or request.user.profile.role.name not in ['Administrateur', 'Manager', 'Réceptionniste']:
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
        return redirect('dashboard')
    
    search_type = request.GET.get('search_type', 'client')
    query = request.GET.get('query', '')
    results = []
    
    if query:
        if search_type == 'client':
            # Recherche de clients
            clients = Client.objects.filter(
                Q(profile__user__first_name__icontains=query) |
                Q(profile__user__last_name__icontains=query) |
                Q(profile__user__email__icontains=query) |
                Q(profile__phone__icontains=query)
            )
            
            results = [
                {
                    'type': 'Client',
                    'information': f"{client.profile.user.get_full_name()} ({client.profile.user.email})",
                    'details': f"Téléphone: {client.profile.phone or 'Non spécifié'}",
                    'id': client.profile.user.id
                } for client in clients
            ]
        
        elif search_type == 'reservation':
            # Recherche de réservations
            reservations = Reservation.objects.filter(
                Q(id__icontains=query) |
                Q(client__profile__user__first_name__icontains=query) |
                Q(client__profile__user__last_name__icontains=query)
            )
            
            results = [
                {
                    'type': 'Réservation',
                    'information': f"#{reservation.id} - {reservation.client.profile.user.get_full_name()}",
                    'details': f"{reservation.check_in_date.strftime('%d/%m/%Y')} au {reservation.check_out_date.strftime('%d/%m/%Y')}",
                    'id': reservation.id
                } for reservation in reservations
            ]
    
    context = {
        'results': results,
        'search_type': search_type,
        'query': query
    }
    
    return render(request, 'reservations/search_results.html', context)