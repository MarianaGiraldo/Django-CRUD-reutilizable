import logging
from django.core.exceptions import ValidationError
from core.views import BaseCrudView
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
		# AUDITORÍA: Registrar evento si pasa a PUBLICADO
		was_published = original['estado'] == 'PUBLICADO' if original else False
		if obj.estado == 'PUBLICADO' and not was_published:
			logger.info(f"AUDITORÍA: El usuario {request.user} publicó la anotación ID {obj.id}")
			print(f"--- EVENTO: Anotación '{obj.titulo}' ha sido publicada ---")