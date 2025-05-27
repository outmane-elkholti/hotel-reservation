from django.db import models
from django.utils import timezone
from accounts.models import Client
from rooms.models import Room

class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class ReservationStatus(models.TextChoices):
    PENDING = 'PENDING', 'En attente'
    CONFIRMED = 'CONFIRMED', 'Confirmée'
    CHECKED_IN = 'CHECKED_IN', 'Enregistrée (check-in)'
    CHECKED_OUT = 'CHECKED_OUT', 'Terminée (check-out)'
    CANCELLED = 'CANCELLED', 'Annulée'

class PaymentMethod(models.TextChoices):
    CREDIT_CARD = 'CREDIT_CARD', 'Carte de crédit'
    CASH = 'CASH', 'Espèces'
    BANK_TRANSFER = 'BANK_TRANSFER', 'Virement bancaire'
    CHECK = 'CHECK', 'Chèque'

class Reservation(models.Model):
    client = models.ForeignKey(Client, related_name='reservations', on_delete=models.CASCADE)
    rooms = models.ManyToManyField(Room, related_name='reservations')
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PENDING
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    services = models.ManyToManyField(Service, related_name='reservations', blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Reservation #{self.id} - {self.client.profile.user.username}"
    
    def calculate_total(self):
        """Calcule le montant total de la réservation"""
        # Si l'objet n'a pas encore d'ID, retourner 0
        if not self.id:
            return 0
        
        # Calculer le nombre de nuits
        nights = (self.check_out_date - self.check_in_date).days
        
        # Prix des chambres
        room_total = sum(room.base_price for room in self.rooms.all()) * nights
        
        # Prix des services
        service_total = sum(service.price for service in self.services.all())
        
        return room_total + service_total
    
    def save(self, *args, **kwargs):
        # Si c'est un nouvel objet (sans ID), enregistrer d'abord
        if not self.id:
            # Définir un montant temporaire pour permettre l'enregistrement initial
            if not self.total_amount:
                self.total_amount = 0
            # Enregistrer pour obtenir un ID
            super().save(*args, **kwargs)
            # Maintenant que nous avons un ID, recalculer le montant
            self.total_amount = self.calculate_total()
            # Enregistrer à nouveau avec le montant correct
            super().save(*args, **kwargs)
        else:
            # Mise à jour d'un objet existant
            if not self.total_amount:
                self.total_amount = self.calculate_total()
            super().save(*args, **kwargs)

class Payment(models.Model):
    reservation = models.ForeignKey(Reservation, related_name='payments', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CREDIT_CARD
    )
    reference = models.CharField(max_length=100, blank=True)
    is_confirmed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Payment #{self.id} for Reservation #{self.reservation.id}"
    
    # reservations/models.py - Ajouter cette méthode au modèle Reservation

def calculate_total(self):
    """
    Calcule le montant total de la réservation
    """
    total = 0
    
    # Calculer le nombre de nuits
    if self.check_out_date and self.check_in_date:
        nights = (self.check_out_date - self.check_in_date).days
        
        # Ajouter le prix des chambres
        for room in self.rooms.all():
            total += room.base_price * nights
        
        # Ajouter le prix des services
        for service in self.services.all():
            total += service.price
    
    return total

# Ajouter aussi cette méthode pour obtenir la durée du séjour
def get_duration_nights(self):
    """
    Retourne le nombre de nuits du séjour
    """
    if self.check_out_date and self.check_in_date:
        return (self.check_out_date - self.check_in_date).days
    return 0