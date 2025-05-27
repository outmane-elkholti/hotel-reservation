# accounts/utils.py - VERSION COMPLÈTE
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_welcome_email(user):
    """
    Envoie un email de bienvenue au nouvel utilisateur inscrit
    """
    try:
        # Préparer les données pour le template
        context = {
            'user': user,
            'hotel_name': 'Hôtel Deluxe',
            'hotel_phone': '+33 1 23 45 67 89',
            'hotel_email': 'info@hoteldeluxe.com',
            'hotel_address': '123 Avenue des Champs-Élysées, 75008 Paris, France'
        }
        
        # Render HTML email template
        html_content = render_to_string('emails/welcome_email.html', context)
        
        # Render plain text version
        text_content = render_to_string('emails/welcome_email.txt', context)
        
        # Email details
        subject = f'Bienvenue à l\'Hôtel Deluxe, {user.get_full_name()} !'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        
        # Send email
        send_mail(
            subject=subject,
            message=text_content,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_content,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email de bienvenue: {e}")
        return False

def send_reservation_confirmation_email(reservation):
    """
    Envoie un email de confirmation de réservation au client
    """
    try:
        # Préparer les données pour le template
        context = {
            'reservation': reservation,
            'client': reservation.client,
            'user': reservation.client.profile.user,
            'rooms': reservation.rooms.all(),
            'services': reservation.services.all(),
            'nights': (reservation.check_out_date - reservation.check_in_date).days,
            'hotel_name': 'Hôtel Deluxe',
            'hotel_phone': '+33 1 23 45 67 89',
            'hotel_email': 'info@hoteldeluxe.com',
            'hotel_address': '123 Avenue des Champs-Élysées, 75008 Paris, France'
        }
        
        # Render HTML email template
        html_content = render_to_string('emails/reservation_confirmation.html', context)
        
        # Render plain text version
        text_content = render_to_string('emails/reservation_confirmation.txt', context)
        
        # Email details
        subject = f'Confirmation de réservation #{reservation.id} - Hôtel Deluxe'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [reservation.client.profile.user.email]
        
        # Send email
        send_mail(
            subject=subject,
            message=text_content,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_content,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email: {e}")
        return False

def send_payment_confirmation_email(payment):
    """
    Envoie un email de confirmation de paiement au client
    """
    try:
        reservation = payment.reservation
        
        # Calculer le montant total payé
        total_paid = sum(p.amount for p in reservation.payments.filter(is_confirmed=True))
        balance = reservation.total_amount - total_paid
        
        context = {
            'payment': payment,
            'reservation': reservation,
            'client': reservation.client,
            'user': reservation.client.profile.user,
            'total_paid': total_paid,
            'balance': balance,
            'hotel_name': 'Hôtel Deluxe',
            'hotel_phone': '+33 1 23 45 67 89',
            'hotel_email': 'info@hoteldeluxe.com',
        }
        
        html_content = render_to_string('emails/payment_confirmation.html', context)
        text_content = render_to_string('emails/payment_confirmation.txt', context)
        
        subject = f'Confirmation de paiement - Réservation #{reservation.id}'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [reservation.client.profile.user.email]
        
        send_mail(
            subject=subject,
            message=text_content,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_content,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email de paiement: {e}")
        return False

def send_cancellation_email(reservation):
    """
    Envoie un email de confirmation d'annulation au client
    """
    try:
        context = {
            'reservation': reservation,
            'client': reservation.client,
            'user': reservation.client.profile.user,
            'hotel_name': 'Hôtel Deluxe',
            'hotel_phone': '+33 1 23 45 67 89',
            'hotel_email': 'info@hoteldeluxe.com',
        }
        
        html_content = render_to_string('emails/reservation_cancellation.html', context)
        text_content = render_to_string('emails/reservation_cancellation.txt', context)
        
        subject = f'Annulation de réservation #{reservation.id} - Hôtel Deluxe'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [reservation.client.profile.user.email]
        
        send_mail(
            subject=subject,
            message=text_content,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_content,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email d'annulation: {e}")
        return False