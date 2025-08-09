from django.urls import path
from .views import login_view,dashboard_merch
from . import views

urlpatterns = [
    path('', login_view, name='login'),
    path('dashboard/merch/', dashboard_merch, name='dashboard_merch'),

    # Missions merch
    path('missions/<int:mission_id>/start', views.start_visit, name='start_visit'),
    path('missions/<int:mission_id>/realisation', views.mission_realisation, name='mission_realisation'),
    path('missions/<int:mission_id>/upload-photo', views.upload_photo, name='upload_photo'),
    path('missions/<int:mission_id>/save-client', views.save_client_products, name='save_client_products'),
    path('missions/<int:mission_id>/save-concurrents', views.save_concurrent_products, name='save_concurrent_products'),
    path('missions/<int:mission_id>/finish', views.finish_visit, name='finish_visit'),

    # Nouveau endpoint photos (préchargement)
    path('missions/<int:mission_id>/photos', views.list_photos, name='list_photos'),

    # Client area
    path('client/dashboard/', views.client_dashboard, name='client_dashboard'),

    # JSON / AJAX endpoints
    #path('api/pdv/<int:pdv_id>/photos/', views.api_pdv_photos, name='api_pdv_photos'),
    #path('api/realisations/filter/', views.api_filter_realisations, name='api_filter_realisations'),
]