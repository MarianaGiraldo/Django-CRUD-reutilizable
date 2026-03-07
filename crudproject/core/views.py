from django.views import View
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured

import copy

class BaseCrudView(View):
	"""
	Vista base CRUD reutilizable y extensible.
	Provee:
	- Listado (GET)
	- Crear/Editar (GET/POST)
	- Activar/Inactivar (POST, hookeable)
	Parámetros configurables:
		model: Modelo a usar (obligatorio)
		form_class: Formulario a usar
		list_display: columnas a mostrar en listado y JSON
		template_name: template para listado
		form_template: template para formulario
		search_fields: campos para búsqueda
		filter_field: campo para filtro
		active_field: campo booleano para activar/inactivar (por defecto 'activo')
	Métodos hook para personalización:
		get_queryset, before_save, after_save, get_context_data, before_toggle, after_toggle
	"""
	model = None
	form_class = None
	list_display = None
	template_name = None
	form_template = None
	search_fields = None  # Mejor None que lista mutable
	filter_field = None
	active_field = "activo"

	def dispatch(self, request, *args, **kwargs):
		required = ["model", "form_class", "template_name", "form_template"]
		for attr in required:
			if getattr(self, attr) is None:
				raise ImproperlyConfigured(f"{self.__class__.__name__} requires {attr}")
		return super().dispatch(request, *args, **kwargs)

	def get_queryset(self, request):
		"""Hook: permite personalizar el queryset."""
		return self.model.objects.all()

	def apply_filters(self, request, queryset):
		"""Aplica búsqueda y filtro al queryset."""
		# Filtro
		if self.filter_field and request.GET.get(self.filter_field):
			queryset = queryset.filter(**{self.filter_field: request.GET[self.filter_field]})
		# Búsqueda
		q = request.GET.get('q')
		if q and self.search_fields:
			from django.db.models import Q
			query = Q()
			for field in self.search_fields:
				query |= Q(**{f"{field}__icontains": q})
			queryset = queryset.filter(query)
		return queryset

	def get_filtered_queryset(self, request):
		"""Permite override para modificar el queryset filtrado antes del render."""
		qs = self.get_queryset(request)
		return self.apply_filters(request, qs)

	def get_context_data(self, request, **kwargs):
		"""Hook: permite agregar datos al contexto."""
		return kwargs

	def before_save(self, request, obj, form, is_create, original=None):
		"""Hook: lógica antes de guardar. Recibe el valor original para detectar cambios."""
		pass

	def after_save(self, request, obj, form, is_create, original=None):
		"""Hook: lógica después de guardar. Recibe el valor original para detectar cambios."""
		pass

	def before_toggle(self, request, obj):
		"""Hook: lógica antes de activar/inactivar."""
		pass

	def after_toggle(self, request, obj):
		"""Hook: lógica después de activar/inactivar."""
		pass

	def get(self, request, *args, **kwargs):
		"""GET: listado o formulario."""
		if 'pk' in kwargs:
			# Formulario editar
			obj = get_object_or_404(self.model, pk=kwargs['pk'])
			form = self.form_class(instance=obj)
			context = self.get_context_data(request, form=form, object=obj, is_create=False)
			return render(request, self.form_template, context)
		else:
			# Listado
			queryset = self.get_filtered_queryset(request)
			context = self.get_context_data(request, object_list=queryset)
			return render(request, self.template_name, context)

	def post(self, request, *args, **kwargs):
		"""POST: crear/editar."""
		if 'pk' in kwargs:
			obj = get_object_or_404(self.model, pk=kwargs['pk'])
			form = self.form_class(request.POST, instance=obj)
			is_create = False
			# Usar deepcopy para snapshot del original
			original = copy.deepcopy(obj)
		else:
			obj = None
			form = self.form_class(request.POST)
			is_create = True
			original = None

		if form.is_valid():
			instance = form.save(commit=False)
			self.before_save(request, instance, form, is_create, original=original)
			instance.save()
			form.save_m2m()
			self.after_save(request, instance, form, is_create, original=original)
			return redirect(self.get_success_url(instance))
		context = self.get_context_data(request, form=form, object=obj, is_create=is_create)
		return render(request, self.form_template, context)


	@classmethod
	def get_urls(cls):
		from django.urls import path

		class ListView(cls):
			pass

		class JsonView(cls):
			def get(self, request, *args, **kwargs):
				queryset = self.get_filtered_queryset(request)
				fields = self.list_display or [f.name for f in self.model._meta.fields]
				data = list(queryset.values(*fields))
				return JsonResponse(data, safe=False)

		class ToggleView(cls):
			def post(self, request, *args, **kwargs):
				if 'pk' not in kwargs:
					return HttpResponseForbidden()
				obj = get_object_or_404(self.model, pk=kwargs['pk'])
				self.before_toggle(request, obj)
				field = self.active_field
				current = getattr(obj, field, None)
				if current is None:
					return HttpResponseForbidden()
				setattr(obj, field, not current)
				obj.save()
				self.after_toggle(request, obj)
				return JsonResponse({
					"success": True,
					field: getattr(obj, field)
				})

		return [
			path('', ListView.as_view(), name='list'),
			path('json/', JsonView.as_view(), name='json'),
			path('add/', cls.as_view(), name='add'),
			path('<int:pk>/', cls.as_view(), name='edit'),
			path('<int:pk>/toggle/', ToggleView.as_view(), name='toggle'),
		]

	def get_success_url(self, obj):
		"""URL a la que redirigir tras guardar."""
		return reverse(f'{self.model._meta.app_label}:list')
