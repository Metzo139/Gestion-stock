from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F, Sum, Count, Q, Avg, Case, When, DecimalField, IntegerField
from django.db.models.functions import TruncMonth, Cast
from django.utils import timezone
from .models import Categorie, Produit, Mouvement, Commande, Fournisseur, LigneCommande, Inventaire, LigneInventaire
from .forms import ProduitForm, MouvementForm, UserUpdateForm, ProfilUpdateForm
from django.db import models
from datetime import timedelta
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa 
from io import BytesIO
from django.db import transaction
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from django.core.serializers.json import DjangoJSONEncoder
import json
from decimal import Decimal
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

# Créez un encodeur JSON personnalisé
class DecimalEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

@login_required
def dashboard(request):
    # Statistiques générales
    stats = {
        'total_produits': Produit.objects.count(),
        'total_categories': Categorie.objects.count(),
        'total_fournisseurs': Fournisseur.objects.count(),
        'produits_en_alerte': Produit.objects.filter(quantite_stock__lte=F('seuil_alerte')).count(),
    }
    
    # Valeur totale du stock
    valeur_stock = Produit.objects.aggregate(
        total=Sum(F('quantite_stock') * F('prix_unitaire'))
    )['total'] or 0
    
    # Derniers mouvements
    derniers_mouvements = Mouvement.objects.select_related('produit', 'effectue_par').order_by('-date_mouvement')[:5]
    
    # Commandes en cours
    commandes_en_cours = Commande.objects.filter(statut='EN_ATTENTE').order_by('-date_commande')[:5]
    
    # Derniers inventaires
    derniers_inventaires = Inventaire.objects.select_related('effectue_par').order_by('-date_debut')[:3]
    
    context = {
        'stats': stats,
        'valeur_stock': valeur_stock,
        'derniers_mouvements': derniers_mouvements,
        'commandes_en_cours': commandes_en_cours,
        'derniers_inventaires': derniers_inventaires,
    }
    return render(request, 'Sama_Stock/dashboard.html', context)

@login_required
def liste_produits(request):
    produits = Produit.objects.all().order_by('categorie', 'nom')
    return render(request, 'Sama_Stock/liste_produits.html', {'produits': produits})

@login_required
def detail_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    mouvements = Mouvement.objects.filter(produit=produit).order_by('-date_mouvement')[:10]
    return render(request, 'Sama_Stock/detail_produit.html', {
        'produit': produit,
        'mouvements': mouvements
    })

@login_required
def ajouter_produit(request):
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produit ajouté avec succès!')
            return redirect('Sama_Stock:liste_produits')
    else:
        form = ProduitForm()
    return render(request, 'Sama_Stock/form_produit.html', {'form': form, 'titre': 'Ajouter un produit'})

@login_required
def mouvement_stock(request):
    if request.method == 'POST':
        form = MouvementForm(request.POST)
        if form.is_valid():
            mouvement = form.save(commit=False)
            mouvement.effectue_par = request.user
            
            # Vérification du stock pour les sorties
            if mouvement.type_mouvement == 'SORTIE' and mouvement.quantite > mouvement.produit.quantite_stock:
                messages.error(request, 'Stock insuffisant pour cette sortie!')
                return render(request, 'Sama_Stock/form_mouvement.html', {'form': form})
            
            mouvement.save()
            
            # Mise à jour du stock
            produit = mouvement.produit
            if mouvement.type_mouvement == 'ENTREE':
                produit.quantite_stock += mouvement.quantite
            else:  # SORTIE
                produit.quantite_stock -= mouvement.quantite
            produit.save()
            
            messages.success(request, 'Mouvement enregistré avec succès!')
            return redirect('Sama_Stock:liste_produits')
    else:
        form = MouvementForm()
    
    return render(request, 'Sama_Stock/form_mouvement.html', {
        'form': form,
        'titre': 'Enregistrer un mouvement'
    })

@login_required
def modifier_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES, instance=produit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produit modifié avec succès!')
            return redirect('Sama_Stock:liste_produits')
    else:
        form = ProduitForm(instance=produit)
    return render(request, 'Sama_Stock/form_produit.html', {
        'form': form,
        'titre': 'Modifier le produit',
        'produit': produit
    })

@login_required
def supprimer_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        produit.delete()
        messages.success(request, 'Produit supprimé avec succès!')
        return redirect('Sama_Stock:liste_produits')
    return render(request, 'Sama_Stock/confirmer_suppression.html', {'produit': produit})

@login_required
def statistiques(request):
    # Période
    periode = request.GET.get('periode', '30')  # 30 jours par défaut
    date_debut = timezone.now() - timedelta(days=int(periode))
    
    # Statistiques générales
    stats_generales = {
        'total_produits': Produit.objects.count(),
        'produits_en_alerte': Produit.objects.filter(quantite_stock__lte=F('seuil_alerte')).count(),
        'valeur_stock': Produit.objects.aggregate(
            total=Sum(F('quantite_stock') * F('prix_unitaire'), output_field=DecimalField())
        )['total'] or 0,
        'marge_moyenne': Produit.objects.aggregate(
            marge_avg=Avg('marge')
        )['marge_avg'] or 0,
    }

    # Mouvements de stock
    mouvements = Mouvement.objects.filter(date_mouvement__gte=date_debut)
    stats_mouvements = {
        'entrees': mouvements.filter(type_mouvement='ENTREE').aggregate(
            total=Sum('quantite')
        )['total'] or 0,
        'sorties': mouvements.filter(type_mouvement='SORTIE').aggregate(
            total=Sum('quantite')
        )['total'] or 0,
    }

    # Top produits
    top_produits = Produit.objects.annotate(
        total_sorties=Sum(Case(
            When(
                mouvement__type_mouvement='SORTIE',
                mouvement__date_mouvement__gte=date_debut,
                then='mouvement__quantite'
            ),
            default=0,
            output_field=IntegerField(),
        )),
        chiffre_affaires=Sum(Case(
            When(
                mouvement__type_mouvement='SORTIE',
                mouvement__date_mouvement__gte=date_debut,
                then=F('mouvement__quantite') * F('prix_unitaire')
            ),
            default=0,
            output_field=DecimalField(),
        )),
        benefice=Sum(Case(
            When(
                mouvement__type_mouvement='SORTIE',
                mouvement__date_mouvement__gte=date_debut,
                then=F('mouvement__quantite') * (F('prix_unitaire') - F('prix_achat'))
            ),
            default=0,
            output_field=DecimalField(),
        ))
    ).exclude(total_sorties=None).order_by('-total_sorties')[:5]

    # Statistiques par catégorie
    stats_categories = Categorie.objects.annotate(
        nombre_produits=Count('produit'),
        valeur_stock=Sum(F('produit__quantite_stock') * F('produit__prix_unitaire')),
        nombre_alertes=Count('produit', filter=Q(produit__quantite_stock__lte=F('produit__seuil_alerte')))
    )

    # Données pour le graphique des mouvements
    derniers_mois = []
    for i in range(6):
        date = timezone.now() - timedelta(days=30*i)
        debut_mois = date.replace(day=1, hour=0, minute=0, second=0)
        fin_mois = (debut_mois + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        
        mouvements_mois = Mouvement.objects.filter(date_mouvement__range=(debut_mois, fin_mois))
        derniers_mois.append({
            'mois': debut_mois.strftime('%B %Y'),
            'entrees': int(mouvements_mois.filter(type_mouvement='ENTREE').aggregate(
                total=Sum('quantite'))['total'] or 0),
            'sorties': int(mouvements_mois.filter(type_mouvement='SORTIE').aggregate(
                total=Sum('quantite'))['total'] or 0)
        })
    
    # Données pour le graphique des ventes par catégorie
    ventes_categories = list(Categorie.objects.annotate(
        total_ventes=Sum(Case(
            When(
                produit__mouvement__type_mouvement='SORTIE',
                produit__mouvement__date_mouvement__gte=date_debut,
                then=Cast(F('produit__mouvement__quantite') * F('produit__prix_unitaire'), 
                         output_field=DecimalField())
            ),
            default=0,
            output_field=DecimalField(),
        ))
    ).values('nom', 'total_ventes'))

    # Convertir les Decimal en float pour la sérialisation JSON
    for cat in ventes_categories:
        if cat['total_ventes'] is not None:
            cat['total_ventes'] = float(cat['total_ventes'])

    context = {
        'stats_generales': stats_generales,
        'stats_mouvements': stats_mouvements,
        'top_produits': top_produits,
        'stats_categories': stats_categories,
        'periode': periode,
        'derniers_mois': json.dumps(derniers_mois, cls=DecimalEncoder),
        'ventes_categories': json.dumps(ventes_categories, cls=DecimalEncoder),
    }
    return render(request, 'Sama_Stock/statistiques.html', context)

@login_required
def export_statistiques(request):
    if xlsxwriter is None:
        messages.error(request, "Le module xlsxwriter n'est pas installé. Impossible de générer le fichier Excel.")
        return redirect('Sama_Stock:statistiques')
        
    # Créer un fichier Excel en mémoire
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    
    try:
        # Formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'bg_color': '#4CAF50',
            'font_color': 'white'
        })
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#f5f5f5'
        })
        
        # Feuille des statistiques générales
        ws_general = workbook.add_worksheet("Statistiques générales")
        ws_general.write('A1', 'Statistiques générales', title_format)
        ws_general.write('A3', 'Total produits', header_format)
        ws_general.write('B3', Produit.objects.count())
        
        # Feuille des mouvements
        ws_mouvements = workbook.add_worksheet("Mouvements")
        ws_mouvements.write('A1', 'Mouvements de stock', title_format)
        
        # En-têtes
        headers = ['Date', 'Type', 'Produit', 'Quantité', 'Effectué par']
        for col, header in enumerate(headers):
            ws_mouvements.write(2, col, header, header_format)
            
        # Données des mouvements
        mouvements = Mouvement.objects.select_related('produit', 'effectue_par').order_by('-date_mouvement')
        for row, mvt in enumerate(mouvements, start=3):
            ws_mouvements.write(row, 0, mvt.date_mouvement.strftime('%d/%m/%Y %H:%M'))
            ws_mouvements.write(row, 1, mvt.get_type_mouvement_display())
            ws_mouvements.write(row, 2, mvt.produit.nom)
            ws_mouvements.write(row, 3, mvt.quantite)
            ws_mouvements.write(row, 4, mvt.effectue_par.username if mvt.effectue_par else '')
        
        # Feuille des top produits
        ws_top = workbook.add_worksheet("Top produits")
        ws_top.write('A1', 'Top des produits', title_format)
        
        # En-têtes
        headers = ['Produit', 'Ventes', 'Chiffre d\'affaires', 'Bénéfice']
        for col, header in enumerate(headers):
            ws_top.write(2, col, header, header_format)
            
        # Données des top produits
        top_produits = Produit.objects.annotate(
            total_sorties=Sum('mouvement__quantite', 
                filter=Q(mouvement__type_mouvement='SORTIE')),
            chiffre_affaires=F('total_sorties') * F('prix_unitaire'),
            benefice=F('total_sorties') * (F('prix_unitaire') - F('prix_achat'))
        ).exclude(total_sorties=None).order_by('-total_sorties')[:10]
        
        for row, prod in enumerate(top_produits, start=3):
            ws_top.write(row, 0, prod.nom)
            ws_top.write(row, 1, prod.total_sorties or 0)
            ws_top.write(row, 2, float(prod.chiffre_affaires or 0))
            ws_top.write(row, 3, float(prod.benefice or 0))
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=statistiques.xlsx'
        return response
        
    except Exception as e:
        messages.error(request, f"Erreur lors de la génération du fichier Excel : {str(e)}")
        return redirect('Sama_Stock:statistiques')

@login_required
def gestion_commandes(request):
    commandes = Commande.objects.all().order_by('-date_commande')
    return render(request, 'Sama_Stock/commandes/liste.html', {'commandes': commandes})

@login_required
def nouvelle_commande(request):
    if request.method == 'POST':
        try:
            # Récupération des données du formulaire
            fournisseur_id = request.POST.get('fournisseur')
            date_livraison = request.POST.get('date_livraison')
            commentaire = request.POST.get('commentaire')
            
            # Création de la commande
            commande = Commande.objects.create(
                fournisseur_id=fournisseur_id,
                date_livraison_prevue=date_livraison,
                commentaire=commentaire,
                creee_par=request.user,
                statut='EN_ATTENTE'
            )
            
            # Traitement des lignes de commande
            produits = Produit.objects.all()
            lignes_creees = False
            
            for produit in produits:
                quantite = request.POST.get(f'quantite_{produit.id}')
                if quantite and int(quantite) > 0:
                    LigneCommande.objects.create(
                        commande=commande,
                        produit=produit,
                        quantite=int(quantite),
                        prix_unitaire=produit.prix_achat
                    )
                    lignes_creees = True
            
            if not lignes_creees:
                commande.delete()
                messages.error(request, 'Veuillez spécifier au moins une quantité à commander.')
                return redirect('Sama_Stock:nouvelle_commande')
            
            messages.success(request, 'Commande créée avec succès!')
            return redirect('Sama_Stock:gestion_commandes')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création de la commande: {str(e)}')
            return redirect('Sama_Stock:nouvelle_commande')
    else:
        produits_a_commander = Produit.objects.filter(
            Q(quantite_stock__lte=F('seuil_alerte')) |
            Q(quantite_stock=0)
        ).order_by('categorie', 'nom')
        
        context = {
            'produits': produits_a_commander,
            'fournisseurs': Fournisseur.objects.all()
        }
        return render(request, 'Sama_Stock/commandes/nouvelle.html', context)

@login_required
def nouvel_inventaire(request):
    if request.method == 'POST':
        inventaire = Inventaire.objects.create(
            date_debut=timezone.now(),
            effectue_par=request.user
        )
        # Créer les lignes d'inventaire pour tous les produits
        for produit in Produit.objects.all():
            LigneInventaire.objects.create(
                inventaire=inventaire,
                produit=produit,
                quantite_theorique=produit.quantite_stock,
                quantite_reelle=0
            )
        return redirect('Sama_Stock:inventaire_en_cours', pk=inventaire.pk)
    return render(request, 'Sama_Stock/inventaire/nouveau.html')

@login_required
def inventaire_en_cours(request, pk):
    inventaire = get_object_or_404(Inventaire, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Mise à jour des quantités
        for ligne in inventaire.ligneinventaire_set.all():
            quantite = request.POST.get(f'reelle_{ligne.id}')
            commentaire = request.POST.get(f'commentaire_{ligne.id}')
            
            if quantite is not None:
                ligne.quantite_reelle = int(quantite)
                ligne.commentaire = commentaire
                ligne.save()
        
        if action == 'terminate':
            # Terminer l'inventaire
            inventaire.statut = 'TERMINE'
            inventaire.date_fin = timezone.now()
            inventaire.save()
            
            # Mettre à jour les stocks
            for ligne in inventaire.ligneinventaire_set.all():
                if ligne.ecart() != 0:
                    ligne.produit.quantite_stock = ligne.quantite_reelle
                    ligne.produit.save()
            
            messages.success(request, "L'inventaire a été terminé avec succès!")
            return redirect('Sama_Stock:dashboard')
        else:
            messages.success(request, "L'inventaire a été sauvegardé!")
    
    lignes = inventaire.ligneinventaire_set.select_related('produit', 'produit__categorie').all()
    return render(request, 'Sama_Stock/inventaire/en_cours.html', {
        'inventaire': inventaire,
        'lignes': lignes
    })

@login_required
def tableau_bord_avance(request):
    # Statistiques avancées
    produits = Produit.objects.annotate(
        rotation=F('mouvement__quantite') / F('quantite_stock'),
        valeur_stock=F('quantite_stock') * F('prix_unitaire')
    )
    
    # Top produits par rotation
    top_rotation = produits.order_by('-rotation')[:5]
    
    # Produits sans mouvement depuis 30 jours
    date_limite = timezone.now() - timedelta(days=30)
    produits_sans_mouvement = Produit.objects.filter(
        mouvement__date_mouvement__lt=date_limite
    ).distinct()
    
    context = {
        'top_rotation': top_rotation,
        'produits_sans_mouvement': produits_sans_mouvement,
        # Autres statistiques...
    }
    return render(request, 'Sama_Stock/tableau_bord_avance.html', context)

@login_required
def valider_commande(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    if commande.statut == 'EN_ATTENTE':
        commande.statut = 'VALIDEE'
        commande.save()
        messages.success(request, 'Commande validée avec succès!')
    return redirect('Sama_Stock:gestion_commandes')

@login_required
def livrer_commande(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    if commande.statut == 'VALIDEE':
        try:
            with transaction.atomic():
                commande.statut = 'LIVREE'
                commande.save()
                
                # Créer les mouvements de stock
                for ligne in commande.lignecommande_set.all():
                    if commande.type_commande == 'ACHAT':
                        # Entrée en stock pour les commandes fournisseur
                        Mouvement.objects.create(
                            produit=ligne.produit,
                            type_mouvement='ENTREE',
                            quantite=ligne.quantite,
                            effectue_par=request.user,
                            commentaire=f"Livraison commande fournisseur #{commande.id}"
                        )
                        ligne.produit.quantite_stock += ligne.quantite
                    else:
                        # Sortie de stock pour les commandes client
                        if ligne.quantite > ligne.produit.quantite_stock:
                            raise ValueError(f"Stock insuffisant pour {ligne.produit.nom}")
                        
                        Mouvement.objects.create(
                            produit=ligne.produit,
                            type_mouvement='SORTIE',
                            quantite=ligne.quantite,
                            effectue_par=request.user,
                            commentaire=f"Livraison commande client #{commande.id}"
                        )
                        ligne.produit.quantite_stock -= ligne.quantite
                    
                    ligne.produit.save()
                
                messages.success(request, 'Commande livrée avec succès!')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Erreur lors de la livraison: {str(e)}')
    return redirect('Sama_Stock:gestion_commandes')

@login_required
def annuler_commande(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    if commande.statut in ['EN_ATTENTE', 'VALIDEE']:
        commande.statut = 'ANNULEE'
        commande.save()
        messages.success(request, 'Commande annulée avec succès!')
    return redirect('Sama_Stock:gestion_commandes')

def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

@login_required
def generer_bon_commande(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    is_original = request.GET.get('type') != 'copy'
    
    qr_data = f"""
    Commande N°: {commande.id}
    Date: {commande.date_commande.strftime('%d/%m/%Y')}
    {'Client: ' + commande.client if hasattr(commande, 'client') else 'Fournisseur: ' + commande.fournisseur.nom}
    Total TTC: {commande.get_total_ttc()} FCFA
    """
    
    context = {
        'commande': commande,
        'lignes': commande.lignecommande_set.all(),
        'total': commande.get_total(),
        'date': timezone.now(),
        'is_original': is_original,
        'qr_data': qr_data,
        'entreprise': {
            'nom': 'Votre Entreprise',
            'adresse': 'Adresse de l\'entreprise',
            'telephone': 'Téléphone',
            'email': 'email@entreprise.com',
        }
    }
    
    pdf = render_to_pdf('Sama_Stock/pdf/bon_commande.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"bon_commande_{commande.id}_{'original' if is_original else 'copie'}.pdf"
        content = f"inline; filename={filename}"
        response['Content-Disposition'] = content
        return response
    return HttpResponse("Erreur lors de la génération du PDF")

@login_required
def nouvelle_commande_client(request):
    if request.method == 'POST':
        try:
            # Création de la commande client
            commande = Commande.objects.create(
                type_commande='VENTE',  # C'est une vente
                client=request.POST.get('client'),  # Nom du client
                telephone_client=request.POST.get('telephone_client'),
                adresse_livraison=request.POST.get('adresse_livraison'),
                date_livraison_prevue=request.POST.get('date_livraison'),
                commentaire=request.POST.get('commentaire'),
                creee_par=request.user,
                statut='EN_ATTENTE'
            )
            
            # Vérification du stock disponible
            produits = Produit.objects.all()
            lignes_creees = False
            
            for produit in produits:
                quantite = request.POST.get(f'quantite_{produit.id}')
                if quantite and int(quantite) > 0:
                    # Vérifier si assez de stock
                    if int(quantite) > produit.quantite_stock:
                        commande.delete()
                        messages.error(request, f'Stock insuffisant pour {produit.nom}')
                        return redirect('Sama_Stock:nouvelle_commande_client')
                        
                    LigneCommande.objects.create(
                        commande=commande,
                        produit=produit,
                        quantite=int(quantite),
                        prix_unitaire=produit.prix_unitaire  # Prix de vente
                    )
                    lignes_creees = True
            
            if not lignes_creees:
                commande.delete()
                messages.error(request, 'Veuillez spécifier au moins une quantité.')
                return redirect('Sama_Stock:nouvelle_commande_client')
            
            messages.success(request, 'Commande client créée avec succès!')
            return redirect('Sama_Stock:gestion_commandes')
            
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
            return redirect('Sama_Stock:nouvelle_commande_client')
    else:
        # Afficher uniquement les produits en stock
        produits_disponibles = Produit.objects.filter(quantite_stock__gt=0)
        return render(request, 'Sama_Stock/commandes/nouvelle_client.html', {
            'produits': produits_disponibles
        })

@login_required
def profil(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfilUpdateForm(request.POST, request.FILES, instance=request.user.profil)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Votre profil a été mis à jour avec succès!')
            return redirect('Sama_Stock:profil')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfilUpdateForm(instance=request.user.profil)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'Sama_Stock/profil.html', context)
