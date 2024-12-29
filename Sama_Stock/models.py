from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum, F, Q
from django.utils import timezone
from datetime import timedelta
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
from django.db.models.signals import post_save
from django.dispatch import receiver

class Categorie(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.nom
    
    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

class Fournisseur(models.Model):
    nom = models.CharField(max_length=200)
    contact = models.CharField(max_length=100)
    email = models.EmailField()
    adresse = models.TextField()
    date_ajout = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nom

class Produit(models.Model):
    nom = models.CharField(max_length=200)
    categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_stock = models.IntegerField(default=0)
    seuil_alerte = models.IntegerField(default=10)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='produits/', blank=True, null=True)
    code_qr = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    fournisseur_principal = models.ForeignKey(Fournisseur, on_delete=models.SET_NULL, null=True, blank=True)
    emplacement = models.CharField(max_length=100, blank=True)
    unite_mesure = models.CharField(max_length=50, default='unité')
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    marge = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    def __str__(self):
        return self.nom

    def get_mouvements_mois(self):
        debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self.mouvement_set.filter(date_mouvement__gte=debut_mois)

    def get_total_entrees_mois(self):
        return self.get_mouvements_mois().filter(
            type_mouvement='ENTREE'
        ).aggregate(total=Sum('quantite'))['total'] or 0

    def get_total_sorties_mois(self):
        return self.get_mouvements_mois().filter(
            type_mouvement='SORTIE'
        ).aggregate(total=Sum('quantite'))['total'] or 0

    def est_en_alerte(self):
        return self.quantite_stock <= self.seuil_alerte

    def save(self, *args, **kwargs):
        if not self.code_qr and self.id:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"ID: {self.id}\nNom: {self.nom}\nCatégorie: {self.categorie.nom}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            self.code_qr.save(f'qr_{self.nom}.png', File(buffer), save=False)
        
        if self.marge > 0:
            self.prix_unitaire = self.prix_achat * (1 + self.marge/100)
            
        super().save(*args, **kwargs)

    def get_rotation_stock(self):
        """Calcule la rotation du stock sur les 30 derniers jours"""
        debut_periode = timezone.now() - timedelta(days=30)
        sorties = self.mouvement_set.filter(
            type_mouvement='SORTIE',
            date_mouvement__gte=debut_periode
        ).aggregate(total=Sum('quantite'))['total'] or 0
        
        if self.quantite_stock > 0:
            return (sorties / self.quantite_stock) * 30
        return 0

    def get_suggestions_reapprovisionnement(self):
        """Suggère une quantité de réapprovisionnement basée sur l'historique"""
        rotation = self.get_rotation_stock()
        if rotation > 0:
            return max(self.seuil_alerte * 2, int(rotation * 1.5))
        return self.seuil_alerte * 2

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['categorie', 'nom']

class Commande(models.Model):
    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('VALIDEE', 'Validée'),
        ('LIVREE', 'Livrée'),
        ('ANNULEE', 'Annulée'),
    ]
    
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.PROTECT)
    date_commande = models.DateTimeField(auto_now_add=True)
    date_livraison_prevue = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')
    commentaire = models.TextField(blank=True)
    creee_par = models.ForeignKey(User, on_delete=models.PROTECT)
    
    def __str__(self):
        return f"Commande #{self.id} - {self.fournisseur.nom}"

    def get_total(self):
        return sum(ligne.total() for ligne in self.lignecommande_set.all())
    
    def get_nombre_articles(self):
        return sum(ligne.quantite for ligne in self.lignecommande_set.all())

    def get_total_ht(self):
        return sum(ligne.total() for ligne in self.lignecommande_set.all())
    
    def get_total_tva(self):
        return self.get_total_ht() * 0.18  # TVA 18%
    
    def get_total_ttc(self):
        return self.get_total_ht() + self.get_total_tva()

class LigneCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE)
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT)
    quantite = models.IntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    
    def total(self):
        return self.quantite * self.prix_unitaire

class Mouvement(models.Model):
    TYPE_MOUVEMENT = (
        ('ENTREE', 'Entrée en stock'),
        ('SORTIE', 'Sortie de stock'),
    )
    
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    type_mouvement = models.CharField(max_length=6, choices=TYPE_MOUVEMENT)
    quantite = models.IntegerField()
    date_mouvement = models.DateTimeField(auto_now_add=True)
    effectue_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    commentaire = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.type_mouvement} - {self.produit.nom} - {self.quantite}"

    class Meta:
        verbose_name = "Mouvement de stock"
        verbose_name_plural = "Mouvements de stock"
        ordering = ['-date_mouvement']

class Inventaire(models.Model):
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField(null=True, blank=True)
    effectue_par = models.ForeignKey(User, on_delete=models.PROTECT)
    commentaire = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=[
        ('EN_COURS', 'En cours'),
        ('TERMINE', 'Terminé'),
        ('ANNULE', 'Annulé'),
    ], default='EN_COURS')

class LigneInventaire(models.Model):
    inventaire = models.ForeignKey(Inventaire, on_delete=models.CASCADE)
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT)
    quantite_theorique = models.IntegerField()
    quantite_reelle = models.IntegerField()
    commentaire = models.TextField(blank=True)

    def ecart(self):
        return self.quantite_reelle - self.quantite_theorique

class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profils/', null=True, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    fonction = models.CharField(max_length=100, blank=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profil de {self.user.username}'

@receiver(post_save, sender=User)
def creer_profil(sender, instance, created, **kwargs):
    if created:
        Profil.objects.create(user=instance)

@receiver(post_save, sender=User)
def sauvegarder_profil(sender, instance, **kwargs):
    instance.profil.save()
