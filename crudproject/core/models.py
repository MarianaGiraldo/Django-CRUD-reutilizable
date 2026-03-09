from django.db import models
from django.contrib.auth.models import User


class ControlCambio(models.Model):
    """
    Tabla de auditoría transversal del motor CRUD.

    Registra cada operación significativa (crear, editar, activar/inactivar)
    indicando quién la realizó, sobre qué objeto, cuándo y qué valores cambiaron.

    Es genérica: funciona para cualquier modelo gestionado por BaseCrudView.
    """

    ACCIONES = (
        ('CREAR',     'Crear'),
        ('EDITAR',    'Editar'),
        ('ACTIVAR',   'Activar'),
        ('INACTIVAR', 'Inactivar'),
        ('PUBLICAR',  'Publicar'),   # Acción de dominio específica usada por notas
    )

    # FK al usuario; SET_NULL para no perder el historial si el usuario se elimina
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='control_cambios',
        verbose_name='Usuario',
    )
    # Acción corta que identifica la operación realizada
    accion = models.CharField(max_length=20, choices=ACCIONES, verbose_name='Acción')
    # Identificador textual del modelo auditado: "app_label.ClassName"
    modelo = models.CharField(max_length=100, verbose_name='Modelo')
    # PK del objeto auditado (se guarda como entero genérico)
    objeto_id = models.PositiveIntegerField(verbose_name='ID objeto')
    # Fecha/hora de la operación; se asigna automáticamente al crear el registro
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
    # Diccionario de cambios: {campo: {anterior: valor_viejo, nuevo: valor_nuevo}}
    # Vacío ({}) en operaciones de creación donde no hay estado previo que comparar
    cambios = models.JSONField(default=dict, blank=True, verbose_name='Cambios')

    class Meta:
        verbose_name = 'Control de Cambio'
        verbose_name_plural = 'Control de Cambios'
        ordering = ['-fecha']   # Los registros más recientes primero

    def __str__(self):
        ts = self.fecha.strftime('%d/%m/%Y %H:%M') if self.fecha else '—'
        return f"{ts} | {self.usuario} | {self.accion} | {self.modelo} #{self.objeto_id}"
