from django.db import models
from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
class Client(models.Model):
    raison_sociale = models.CharField(max_length=255)
    ai = models.CharField(max_length=50)  # AI : Identifiant fiscal
    rc = models.CharField(max_length=50)  # RC : Registre du commerce
    nif = models.CharField(max_length=50) # NIF : Numéro d'Identification Fiscale
    nis = models.CharField(max_length=50) # NIS : Numéro d'Identification Statistique

    def __str__(self):
        return str(self.raison_sociale)  
class Projet(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='projects')
    nom_projet = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    date_lancement = models.DateField()  # Date de début du projet
    date_fin = models.DateField()        # Date de fin prévue

    def __str__(self):
        return f"{self.nom_projet} "
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('client', 'Client'),
        ('superviseur', 'Superviseur'),
        ('merchandiser', 'Merchandiser'),
    )
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='clien_staff')
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    wilaya = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"
class PointDeVente(models.Model):
    TYPE_PDV_CHOICES = [
        ('epicerie', 'Épicerie'),
        ('supermarche', 'Supermarché'),
        ('hypermarché', 'Hypermarché'),
        ('autre', 'Autre'),
    ]

    code = models.CharField(max_length=20, unique=True, editable=False)
    no_pdv = models.CharField(max_length=50, unique=True)
    region = models.CharField(max_length=100)
    wilaya = models.CharField(max_length=100)
    commune = models.CharField(max_length=100)
    type_pdv = models.CharField(max_length=50, choices=TYPE_PDV_CHOICES)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    def save(self, *args, **kwargs):
        if not self.code:
            # Génération du code : ex: PDV-BLIDA-001A23
            prefix = "PDV"
            wilaya_part = self.wilaya.upper().replace(" ", "")[:5]
            unique_part = uuid.uuid4().hex[:6].upper()
            self.code = f"{prefix}-{wilaya_part}-{unique_part}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.commune}, {self.wilaya}"
class Concurrent(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='concurrents')
    nom = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.nom} (Concurrent de {self.client})"
class ProduitClient(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='produits')
    nom = models.CharField(max_length=255)
    categorie = models.CharField(max_length=100)
    format = models.CharField(max_length=100)
    image = CloudinaryField('image', blank=True, null=True)

    def __str__(self):
        return f"{self.nom} - {self.format}"  # OK
class ProduitConcurrent(models.Model):
    concurrent = models.ForeignKey(Concurrent, on_delete=models.CASCADE, related_name='produits')
    nom = models.CharField(max_length=255)
    categorie = models.CharField(max_length=100)
    format = models.CharField(max_length=100)
    image = CloudinaryField('image', blank=True, null=True)

    def __str__(self):
        return f"{self.nom} - {self.format}"
class Mission(models.Model):
    ETAT_CHOICES = (
        ('planned', 'Planifiée'),
        ('in_progress', 'En cours'),
        ('done', 'Faite'),
        ('failed', 'Échouée'),
    )

    REASON_CHOICES = (
        ('pdv_closed', 'PDV fermé'),
        ('other', 'Autre raison'),
    )

    code = models.CharField(max_length=20, unique=True, editable=False)
    pdv = models.ForeignKey(
        PointDeVente,
        on_delete=models.CASCADE,
        related_name="missions"
    )
    date_mission = models.DateField()
    merchandiser = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'merchandiser'}
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="missions_created"
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='clien_missions')
    etat = models.CharField(max_length=20, choices=ETAT_CHOICES, default='planned')
    raison_echec = models.CharField(max_length=50, choices=REASON_CHOICES, blank=True, null=True)

    # Nouveaux champs pour tracking
    begin_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    begin_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    begin_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    end_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    end_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"MSN-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.date_mission < timezone.now().date():
            raise ValidationError("La date de mission ne peut pas être dans le passé.")

    def start(self, lat=None, lon=None):
        self.begin_time = timezone.now()
        if lat and lon:
            self.begin_latitude = lat
            self.begin_longitude = lon
        self.save()

    def finish(self, lat=None, lon=None):
        self.end_time = timezone.now()
        if lat and lon:
            self.end_latitude = lat
            self.end_longitude = lon
        self.save()

    def __str__(self):
        return f"{self.code}"
class RealisationClientData(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    pdv = models.ForeignKey(PointDeVente, on_delete=models.CASCADE)
    merch = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'merchandiser'})
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='clien_realisations')
    date_realisation = models.DateField(auto_now_add=True)

    produit = models.ForeignKey(ProduitClient, on_delete=models.CASCADE)

    disponible = models.BooleanField(default=False, help_text="Produit disponible dans le PDV")
    handling = models.BooleanField(default=False, help_text="Le produit est-il bien présenté ?")
    facing_share = models.FloatField(null=True, blank=True, help_text="Part de linéaire (%)")
    prix_vente = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(null=True, blank=True)
    wilaya = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        # Récupération automatique wilaya / région depuis le PDV
        if self.pdv:
            self.wilaya = self.pdv.wilaya
            self.region = self.pdv.region
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.mission} - {self.produit}"
class RealisationConcurrenceData(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    pdv = models.ForeignKey(PointDeVente, on_delete=models.CASCADE)

    merch = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='realisation_concurrent_merch')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='clien_realisation_concurrent')

    date_realisation = models.DateField(auto_now_add=True)

    produit_concurrent = models.ForeignKey(ProduitConcurrent, on_delete=models.CASCADE)

    disponible = models.BooleanField(default=False)
    facing_share = models.FloatField(null=True, blank=True)
    prix_vente = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(null=True, blank=True)
    wilaya = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        # Récupération automatique wilaya / région depuis le PDV
        if self.pdv:
            self.wilaya = self.pdv.wilaya
            self.region = self.pdv.region
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.mission} - {self.produit_concurrent} @ {self.pdv}"
class PhotoMission(models.Model):
    TYPE_PHOTO_CHOICES = [
        ('avant', 'Avant'),
        ('apres', 'Après'),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='clien_photos')
    mission = models.ForeignKey('Mission', on_delete=models.CASCADE, related_name='photos')
    categorie = models.CharField(max_length=100)
    image = CloudinaryField('image')
    type_photo = models.CharField(max_length=5, choices=TYPE_PHOTO_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    pdv = models.ForeignKey(
        PointDeVente,
        on_delete=models.CASCADE, null=True, blank=True,
        related_name="photos_pdv"
    )
    wilaya = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        # Récupération automatique du client et PDV depuis la mission
        if self.mission:
            self.client = self.mission.client
            self.pdv = self.mission.pdv

        # Si on a un PDV, mettre à jour wilaya et région
        if self.pdv:
            self.wilaya = self.pdv.wilaya
            self.region = self.pdv.region

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.mission} - {self.categorie} - {self.type_photo}"
