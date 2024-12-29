from .models import Produit
from django.db.models import F, Count
from decimal import Decimal

def alertes_stock(request):
    """
    Context processor pour gérer les alertes de stock
    Retourne le nombre de produits en alerte et la liste des produits
    """
    if request.user.is_authenticated:
        produits_en_alerte = Produit.objects.filter(
            quantite_stock__lte=F('seuil_alerte')
        ).annotate(
            manquant=F('seuil_alerte') - F('quantite_stock')
        ).order_by('-manquant')

        return {
            'produits_en_alerte': produits_en_alerte,
            'nombre_alertes': produits_en_alerte.count(),
        }
    return {
        'produits_en_alerte': [],
        'nombre_alertes': 0,
    } 