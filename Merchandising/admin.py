from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Client, Projet,PointDeVente,Concurrent,ProduitClient,ProduitConcurrent,Mission,RealisationClientData,RealisationConcurrenceData,PhotoMission

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Infos personnelles', {'fields': ('client','first_name', 'last_name', 'region', 'wilaya', 'phone_number', 'role')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('client','email', 'first_name', 'last_name', 'region', 'wilaya', 'phone_number', 'role', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email',)
    ordering = ('email',)

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Client)
admin.site.register(Projet)
admin.site.register(Concurrent)
admin.site.register(PointDeVente)
admin.site.register(ProduitClient)
admin.site.register(ProduitConcurrent)
admin.site.register(Mission)
admin.site.register(RealisationClientData)
admin.site.register(RealisationConcurrenceData)
admin.site.register(PhotoMission)