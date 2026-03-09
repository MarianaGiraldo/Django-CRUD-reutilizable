from django.contrib import admin
from .models import Anotacion

@admin.register(Anotacion)
class AnotacionAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'estado', 'activo', 'created_by', 'created_at']
    list_filter = ['estado', 'activo']
    search_fields = ['titulo']
