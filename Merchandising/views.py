from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST,require_GET
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from collections import OrderedDict, defaultdict
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.urls import reverse
from django.contrib.auth import authenticate, login
from django.utils import timezone
from django.utils.timezone import localdate
import json
from .models import (
    Mission,
    PhotoMission,
    ProduitClient,
    ProduitConcurrent,
    RealisationClientData,
    RealisationConcurrenceData,
    PointDeVente,
    Client,
)

def login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            # Redirection selon le rôle
            if user.role == 'merchandiser':
                return redirect('dashboard_merch')
            elif user.role == 'superviseur':
                return redirect('dashboard_superviseur')
            elif user.role == 'client':
                return redirect('client_dashboard')
        else:
            messages.error(request, "Email ou mot de passe incorrect.")
    
    return render(request, 'login.html')

@login_required
def dashboard_merch(request):
    if request.user.role != 'merchandiser':
        return redirect('login')  # sécurité simple

    today = localdate()
    missions = Mission.objects.filter(
        merchandiser=request.user,
        date_mission=today
    ).order_by('date_mission')

    return render(request, 'merchandiser.html', {'missions': missions})

@require_POST
@login_required
def start_visit(request, mission_id):
    mission = get_object_or_404(Mission, id=mission_id)
    if mission.merchandiser != request.user:
        return HttpResponseForbidden("Non autorisé")

    begin_latitude = request.POST.get('latitude')
    begin_longitude = request.POST.get('longitude')

    mission.etat = 'in_progress'
    mission.begin_time = timezone.now()
    mission.begin_latitude = begin_latitude
    mission.begin_longitude = begin_longitude
    mission.save()

    return redirect('mission_realisation', mission_id=mission.id)


@login_required
def mission_realisation(request, mission_id):
    mission = get_object_or_404(Mission, id=mission_id)
    if mission.merchandiser != request.user:
        return redirect('dashboard_merch')

    # Produits client (exemple avec client statique; adapte si besoin)
    try:
        client_products_qs = ProduitClient.objects.filter(client='Amir20000')
    except Exception:
        client_products_qs = ProduitClient.objects.all()

    client_products = client_products_qs[:50]
    categories = list(client_products_qs.values_list('categorie', flat=True).distinct())
    concurrent_products = ProduitConcurrent.objects.all()[:50]

    context = {
        'mission': mission,
        'client_products': client_products,
        'concurrent_products': concurrent_products,
        'categories': categories,
    }
    return render(request, 'mission_realisation.html', context)


@login_required
@require_POST
def upload_photo(request, mission_id):
    """
    Upload d'une photo (avant/apres)
    Attend FormData: image, categorie, photo_type ('avant'|'apres')
    Retourne aussi l'URL pour affichage immédiat côté front.
    """
    mission = get_object_or_404(Mission, id=mission_id)
    if mission.merchandiser != request.user:
        return JsonResponse({'error': 'forbidden'}, status=403)

    image = request.FILES.get('image')
    categorie = request.POST.get('categorie')
    photo_type = request.POST.get('photo_type')  # 'avant' ou 'apres'
    if not image or not categorie or photo_type not in ('avant', 'apres'):
        return JsonResponse({'error': 'missing parameters'}, status=400)

    photo = PhotoMission.objects.create(
        mission=mission,
        categorie=categorie,
        image=image,
        type_photo=photo_type,
    )

    return JsonResponse({
        'success': True,
        'photo_id': photo.id,
        'url': request.build_absolute_uri(photo.image.url),  # important pour le front
        'categorie': categorie,
        'type': photo_type,
    })


@login_required
@require_POST
def save_client_products(request, mission_id):
    mission = get_object_or_404(Mission, id=mission_id)
    if mission.merchandiser != request.user:
        return JsonResponse({'error': 'forbidden'}, status=403)

    try:
        payload = json.loads(request.body)
        items = payload.get('items', [])
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    created = 0
    for it in items:
        produit_id = it.get('produit_id')
        try:
            produit = ProduitClient.objects.get(id=produit_id)
        except ProduitClient.DoesNotExist:
            continue

        RealisationClientData.objects.create(
            mission=mission,
            pdv=getattr(mission, 'pdv', None),
            merch=request.user,
            produit=produit,
            disponible=bool(it.get('disponible')),
            handling=bool(it.get('handling')),
            facing_share=it.get('facing_share') or None,
            prix_vente=it.get('prix_vente') or None,
            stock=it.get('stock') or None
        )
        created += 1

    return JsonResponse({'success': True, 'created': created})


@login_required
@require_POST
def save_concurrent_products(request, mission_id):
    mission = get_object_or_404(Mission, id=mission_id)
    if mission.merchandiser != request.user:
        return JsonResponse({'error': 'forbidden'}, status=403)

    try:
        payload = json.loads(request.body)
        items = payload.get('items', [])
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    created = 0
    for it in items:
        produit_id = it.get('produit_id')
        try:
            produit = ProduitConcurrent.objects.get(id=produit_id)
        except ProduitConcurrent.DoesNotExist:
            continue

        RealisationConcurrenceData.objects.create(
            mission=mission,
            pdv=getattr(mission, 'pdv', None),
            merch=request.user,
            produit_concurrent=produit,
            disponible=bool(it.get('disponible')),
            facing_share=it.get('facing_share') or None,
            prix_vente=it.get('prix_vente') or None,
            stock=it.get('stock') or None
        )
        created += 1

    return JsonResponse({'success': True, 'created': created})


@login_required
@require_POST
def finish_visit(request, mission_id):
    mission = get_object_or_404(Mission, id=mission_id)
    if mission.merchandiser != request.user:
        return JsonResponse({'error': 'forbidden'}, status=403)

    mission.etat = 'done'
    mission.save()
    return JsonResponse({'success': True, 'redirect': reverse('dashboard_merch')})


@login_required
@require_GET
def list_photos(request, mission_id):
    """
    Liste paginée des photos d'une mission.
    GET params: type=('avant'|'apres'|None), categorie (opt), page, page_size
    """
    from django.core.paginator import Paginator

    mission = get_object_or_404(Mission, id=mission_id)
    if mission.merchandiser != request.user:
        return JsonResponse({'error': 'forbidden'}, status=403)

    photo_type = request.GET.get('type')      # 'avant' | 'apres' | None
    categorie = request.GET.get('categorie')  # optionnel
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))

    qs = PhotoMission.objects.filter(mission=mission).order_by('-id')
    if photo_type in ('avant', 'apres'):
        qs = qs.filter(type_photo=photo_type)
    if categorie:
        qs = qs.filter(categorie=categorie)

    p = Paginator(qs, page_size)
    page_obj = p.get_page(page)

    items = [{
        'id': ph.id,
        'url': request.build_absolute_uri(ph.image.url),
        'cat': ph.categorie,
        'type': ph.type_photo,
    } for ph in page_obj.object_list]

    return JsonResponse({
        'success': True,
        'items': items,
        'page': page_obj.number,
        'pages': p.num_pages,
        'count': p.count,
    })

# Util : check que l'utilisateur est un "client"
def user_is_client(user):
    return getattr(user, 'role', None) == 'client'

@login_required
def client_dashboard(request):
    client = request.user.client  # user lié au client
    print(f"Client: {client}")

    wilaya_filter = request.GET.get('wilaya')
    region_filter = request.GET.get('region')
    pdv_search = request.GET.get('pdv_search')

    photos_qs = PhotoMission.objects.filter(client=client).select_related(
        'mission', 'pdv', 'mission__merchandiser'
    ).order_by('-timestamp')

    if wilaya_filter:
        photos_qs = photos_qs.filter(wilaya=wilaya_filter)
    if region_filter:
        photos_qs = photos_qs.filter(region=region_filter)
    if pdv_search:
        photos_qs = photos_qs.filter(pdv__nom__icontains=pdv_search)

    grouped = OrderedDict()

    for photo in photos_qs:
        pdv = photo.pdv
        if not pdv:
            continue

        key = (pdv.id, photo.mission.date_mission)

        if key not in grouped:
            merch = photo.mission.merchandiser
            grouped[key] = {
                "pdv": getattr(pdv, 'nom', str(pdv)),
                "wilaya": photo.wilaya,
                "region": photo.region,
                "merch": f"{merch.first_name} {merch.last_name}" if merch else "",
                "date": photo.mission.date_mission.strftime("%d/%m/%Y"),
                "categories": defaultdict(lambda: {"avant": [], "apres": []}),
            }

        grouped[key]["categories"][photo.categorie][photo.type_photo].append(photo.image.url)

    # Convertir les defaultdict en dict pour que Django template puisse itérer correctement
    for val in grouped.values():
        val["categories"] = dict(val["categories"])

    realisation_list = list(grouped.values())

    context = {
        "realisations": realisation_list,
        "filter_wilayas": sorted(set(photo.wilaya for photo in photos_qs if photo.wilaya)),
        "filter_regions": sorted(set(photo.region for photo in photos_qs if photo.region)),
    }

    return render(request, "client_dashboard.html", context)