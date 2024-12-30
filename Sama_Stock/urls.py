from django.urls import path
from . import views

app_name = 'Sama_Stock'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('produits/', views.liste_produits, name='liste_produits'),
    path('produit/ajouter/', views.ajouter_produit, name='ajouter_produit'),
    path('produit/<int:pk>/', views.detail_produit, name='detail_produit'),
    path('produit/<int:pk>/modifier/', views.modifier_produit, name='modifier_produit'),
    path('produit/<int:pk>/supprimer/', views.supprimer_produit, name='supprimer_produit'),
    path('mouvement/', views.mouvement_stock, name='mouvement_stock'),
    path('statistiques/', views.statistiques, name='statistiques'),
    
    # URLs pour les commandes
    path('commandes/', views.liste_commandes, name='liste_commandes'),
    path('commandes/gestion/', views.gestion_commandes, name='gestion_commandes'),
    path('commande/client/nouvelle/', views.nouvelle_commande_client, name='nouvelle_commande_client'),
    path('commande/fournisseur/nouvelle/', views.nouvelle_commande_fournisseur, name='nouvelle_commande_fournisseur'),
    path('commande/<int:pk>/', views.detail_commande, name='detail_commande'),
    path('commande/<int:pk>/modifier/', views.modifier_commande, name='modifier_commande'),
    path('commande/<int:pk>/valider/', views.valider_commande, name='valider_commande'),
    path('commande/<int:pk>/livrer/', views.livrer_commande, name='livrer_commande'),
    path('commande/<int:pk>/annuler/', views.annuler_commande, name='annuler_commande'),
    path('commande/<int:pk>/pdf/', views.generer_bon_commande, name='generer_bon_commande'),
    path('commandes/export/', views.export_commandes, name='export_commandes'),
    
    # Autres URLs
    path('inventaire/nouveau/', views.nouvel_inventaire, name='nouvel_inventaire'),
    path('inventaire/<int:pk>/', views.inventaire_en_cours, name='inventaire_en_cours'),
    path('statistiques/export/', views.export_statistiques, name='export_statistiques'),
    path('profil/', views.profil, name='profil'),
    path('fournisseurs/', views.liste_fournisseurs, name='liste_fournisseurs'),
    path('fournisseur/ajouter/', views.ajouter_fournisseur, name='ajouter_fournisseur'),
    path('fournisseur/<int:pk>/modifier/', views.modifier_fournisseur, name='modifier_fournisseur'),
    path('fournisseur/<int:pk>/supprimer/', views.supprimer_fournisseur, name='supprimer_fournisseur'),
    path('categories/', views.liste_categories, name='liste_categories'),
    path('categorie/ajouter/', views.ajouter_categorie, name='ajouter_categorie'),
    path('categorie/<int:pk>/modifier/', views.modifier_categorie, name='modifier_categorie'),
    path('categorie/<int:pk>/supprimer/', views.supprimer_categorie, name='supprimer_categorie'),
] 