from django.contrib import admin
from .models import Business, User, Client

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'document', 'active', 'created_at')
    search_fields = ('name', 'document')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'business', 'is_staff')
    list_filter = ('business',)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'business', 'created_at')
    list_filter = ('business',)
    search_fields = ('name', 'email', 'document')
