from django.core.management.base import BaseCommand
from Sama_Stock.models import Commande

class Command(BaseCommand):
    help = 'Met à jour les références des commandes existantes'

    def handle(self, *args, **kwargs):
        commandes = Commande.objects.filter(reference='')
        for commande in commandes:
            prefix = 'CMD-F' if commande.type_commande == 'ACHAT' else 'CMD-C'
            last_cmd = Commande.objects.filter(
                reference__startswith=prefix
            ).exclude(id=commande.id).order_by('-reference').first()
            
            if last_cmd and last_cmd.reference:
                num = int(last_cmd.reference.split('-')[-1]) + 1
            else:
                num = 1
            
            commande.reference = f"{prefix}-{num:04d}"
            commande.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Référence {commande.reference} créée pour la commande {commande.id}')
            ) 