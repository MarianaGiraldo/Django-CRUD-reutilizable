import logging
from django.core.exceptions import ValidationError
from core.views import BaseCrudView
from core.audit import registrar_cambio
from .models import Anotacion
from .forms import AnotacionForm

logger = logging.getLogger(__name__)

class AnotacionCrudView(BaseCrudView):
	model = Anotacion
	form_class = AnotacionForm
	template_name = 'notes/list.html'
	form_template = 'notes/form.html'
	list_display = ['titulo', 'estado', 'activo', 'created_by']
	search_fields = ['titulo']
	filter_field = 'estado'

	def get_form(self, request, instance=None):
		form = super().get_form(request, instance)
		# REGLA: Si ya está PUBLICADO, bloqueamos el campo título en el HTML
		if instance and instance.estado == 'PUBLICADO':
			form.fields['titulo'].disabled = True
		return form

	def before_save(self, request, obj, form, is_create, original=None):
		if is_create:
			obj.created_by = request.user

		# REGLA: El título no se puede cambiar una vez publicado
		if original and original['estado'] == 'PUBLICADO':
			if obj.titulo != original['titulo']:
				raise ValidationError(
					'No se puede modificar el título de una anotación publicada.'
				)

	def after_save(self, request, obj, form, is_create, original=None):
		# AUDITORÍA DE DOMINIO: si la anotación acaba de pasar a PUBLICADO,
		# registramos un evento específico además del CREAR/EDITAR que graba la base.
		was_published = original['estado'] == 'PUBLICADO' if original else False
		if obj.estado == 'PUBLICADO' and not was_published:
			logger.info(
				"AUDITORÍA: El usuario %s publicó la anotación ID %s",
				request.user, obj.id,
			)
			# Registro explícito con acción 'PUBLICAR' en la tabla de auditoría
			registrar_cambio(
				request.user,
				'PUBLICAR',
				obj,
				cambios={'estado': {'anterior': original['estado'] if original else None, 'nuevo': 'PUBLICADO'}},
			)
			print(f"--- EVENTO: Anotación '{obj.titulo}' ha sido publicada ---")