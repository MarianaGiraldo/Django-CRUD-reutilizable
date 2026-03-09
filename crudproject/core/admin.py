from django.contrib import admin
from .models import ControlCambio


@admin.register(ControlCambio)
class ControlCambioAdmin(admin.ModelAdmin):
    """
    Vista del historial de auditoría en el panel de administración.

    El registro es SOLO LECTURA: el historial no debe crearse, modificarse
    ni borrarse manualmente; toda escritura la hace el motor CRUD automáticamente.
    """

    list_display  = ['fecha', 'usuario', 'accion', 'modelo', 'objeto_id']
    list_filter   = ['accion', 'modelo', 'usuario']
    search_fields = ['modelo', 'usuario__username']
    # Todos los campos son solo-lectura para proteger la integridad del historial
    readonly_fields = ['usuario', 'accion', 'modelo', 'objeto_id', 'fecha', 'cambios']

    def has_add_permission(self, request):
        # El historial no se crea manualmente
        return False

    def has_change_permission(self, request, obj=None):
        # El historial no se edita
        return False

    def has_delete_permission(self, request, obj=None):
        # El historial no se borra
        return False
