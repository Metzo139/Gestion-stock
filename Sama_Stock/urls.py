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
    path('commandes/', views.gestion_commandes, name='gestion_commandes'),
    path('commande/nouvelle/', views.nouvelle_commande, name='nouvelle_commande'),
    path('inventaire/nouveau/', views.nouvel_inventaire, name='nouvel_inventaire'),
    path('inventaire/<int:pk>/', views.inventaire_en_cours, name='inventaire_en_cours'),
    path('commande/<int:pk>/valider/', views.valider_commande, name='valider_commande'),
    path('commande/<int:pk>/livrer/', views.livrer_commande, name='livrer_commande'),
    path('commande/<int:pk>/annuler/', views.annuler_commande, name='annuler_commande'),
    path('commande/<int:pk>/pdf/', views.generer_bon_commande, name='generer_bon_commande'),
    path('statistiques/export/', views.export_statistiques, name='export_statistiques'),
    path('profil/', views.profil, name='profil'),
] 