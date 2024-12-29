from django.contrib import admin
from .models import Categorie, Produit, Fournisseur, Commande, LigneCommande, Mouvement, Inventaire, LigneInventaire

@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'description')
    search_fields = ('nom',)

@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'categorie', 'prix_unitaire', 'quantite_stock', 'seuil_alerte')
    list_filter = ('categorie', 'fournisseur_principal')
    search_fields = ('nom', 'description')

@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'contact', 'email')
    search_fields = ('nom', 'email')

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('id', 'fournisseur', 'date_commande', 'statut', 'creee_par')
    list_filter = ('statut', 'fournisseur')
    search_fields = ('fournisseur__nom',)

@admin.register(Mouvement)
class MouvementAdmin(admin.ModelAdmin):
    list_display = ('produit', 'type_mouvement', 'quantite', 'date_mouvement', 'effectue_par')
    list_filter = ('type_mouvement', 'produit__categorie')
    search_fields = ('produit__nom',)

@admin.register(Inventaire)
class InventaireAdmin(admin.ModelAdmin):
    list_display = ('date_debut', 'date_fin', 'effectue_par', 'statut')
    list_filter = ('statut',)
