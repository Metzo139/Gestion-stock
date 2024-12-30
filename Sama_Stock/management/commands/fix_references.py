from django.core.management.base import BaseCommand
from Sama_Stock.models import Commande

class Command(BaseCommand):
    help = 'Vérifie et corrige les références des commandes'

    def handle(self, *args, **kwargs):
        commandes = Commande.objects.all().order_by('date_commande')
        compteurs = {'CMD-F': 1, 'CMD-C': 1}
        
        for commande in commandes:
            prefix = 'CMD-F' if commande.type_commande == 'ACHAT' else 'CMD-C'
            nouvelle_reference = f"{prefix}-{compteurs[prefix]:04d}"
            
            if commande.reference != nouvelle_reference:
                ancienne_reference = commande.reference
                commande.reference = nouvelle_reference
                commande.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Référence mise à jour : {ancienne_reference} -> {nouvelle_reference}'
                    )
                )
            
            compteurs[prefix] += 1 