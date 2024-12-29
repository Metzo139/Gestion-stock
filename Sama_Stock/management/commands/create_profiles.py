from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Sama_Stock.models import Profil

class Command(BaseCommand):
    help = 'Crée des profils pour les utilisateurs existants'

    def handle(self, *args, **kwargs):
        users = User.objects.filter(profil__isnull=True)
        for user in users:
            Profil.objects.create(user=user)
            self.stdout.write(f'Profil créé pour {user.username}') 