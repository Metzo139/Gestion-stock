from django import forms
from .models import Produit, Mouvement, Categorie, Fournisseur, Profil
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = ['nom', 'categorie', 'description', 'prix_achat', 'marge', 
                 'prix_unitaire', 'quantite_stock', 'seuil_alerte', 'image',
                 'fournisseur_principal', 'emplacement', 'unite_mesure']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'prix_achat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'marge': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 
                                            'onchange': 'calculerPrixVente()'}),
            'prix_unitaire': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantite_stock': forms.NumberInput(attrs={'min': '0'}),
            'seuil_alerte': forms.NumberInput(attrs={'min': '1'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        prix_achat = cleaned_data.get('prix_achat')
        prix_unitaire = cleaned_data.get('prix_unitaire')
        marge = cleaned_data.get('marge')

        if prix_achat and prix_unitaire and prix_achat > prix_unitaire:
            raise ValidationError("Le prix de vente doit être supérieur au prix d'achat")
        
        if marge and marge < 0:
            raise ValidationError("La marge ne peut pas être négative")

        return cleaned_data

class MouvementForm(forms.ModelForm):
    class Meta:
        model = Mouvement
        fields = ['produit', 'type_mouvement', 'quantite', 'commentaire']
        widgets = {
            'commentaire': forms.Textarea(attrs={'rows': 3}),
            'produit': forms.Select(attrs={'class': 'form-select'}),
            'type_mouvement': forms.Select(attrs={'class': 'form-select'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control'}),
        } 

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

class ProfilUpdateForm(forms.ModelForm):
    class Meta:
        model = Profil
        fields = ['image', 'telephone', 'fonction'] 