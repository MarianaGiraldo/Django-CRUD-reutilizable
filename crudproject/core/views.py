from django.views import View
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin
from core.audit import registrar_cambio, build_cambios_create, build_cambios_edit

class BaseCrudView(LoginRequiredMixin, View):
	"""
	Motor CRUD reutilizable basado en herencia.

	Funcionalidades:
	- Listado
	- Endpoint JSON
	- Crear / Editar
	- Activar / Inactivar
	- Filtros y búsqueda

	Arquitectura:
	UI -> BaseCrudView -> Hooks negocio -> Model/Form

	Características:
	- Stateless por request: no se almacena estado de sesión/usuario en atributos
	  de la clase. Toda la información fluye por parámetros del método (request, kwargs).
	- Hooks para personalización: before_save, after_save, before_toggle, after_toggle,
	  get_queryset, get_context_data permiten extender el flujo sin sobreescribir el motor.
	- Configuración por atributos de clase (model, form_class, template_name, etc.)

	Uso:
	    Subclasificar, configurar los atributos y registrar rutas con get_urls().
	"""

	# Atributos de clase que las subclases DEBEN sobreescribir
	model = None        # Modelo Django que este CRUD gestiona
	form_class = None   # ModelForm asociado al modelo

	template_name = None   # Template del listado
	form_template = None   # Template del formulario crear/editar

	# Columnas a mostrar en el listado y en el JSON; si es None se usan todos los campos
	list_display = None

	# Campos del modelo donde se realiza la búsqueda por texto (icontains)
	search_fields = None
	# Nombre del campo que se usa como filtro único (ej: 'estado')
	filter_field = None

	# Nombre del campo booleano que representa activo/inactivo
	active_field = "activo"

	# Nombre de la URL de éxito (no se usa directamente; se delega a get_success_url)
	success_url_name = None

	def dispatch(self, request, *args, **kwargs):
		"""
		Valida que los atributos obligatorios estén configurados antes de despachar.
		Esto previene errores silenciosos cuando se olvida configurar la subclase.
		"""
		required = [
			"model",
			"form_class",
			"template_name",
			"form_template",
		]
		for attr in required:
			if getattr(self, attr) is None:
				raise ImproperlyConfigured(
					f"{self.__class__.__name__} requiere '{attr}'"
				)
		return super().dispatch(request, *args, **kwargs)

	def get_list_display(self):
		"""Devuelve las columnas a mostrar. Si no están configuradas, usa todos los campos del modelo."""
		if self.list_display:
			return list(self.list_display)
		# Fallback: introspección de los campos del modelo
		return [f.name for f in self.model._meta.fields]

	def get_search_fields(self):
		"""Devuelve los campos configurados para búsqueda de texto."""
		return self.search_fields or []

	def get_filter_field(self):
		"""Devuelve el campo configurado para el filtro por valor exacto."""
		return self.filter_field

	def get_active_field(self):
		"""Devuelve el nombre del campo booleano activo/inactivo."""
		return self.active_field

	def get_queryset(self, request):
		"""
		Hook sobreescribible: devuelve el queryset base del listado.
		Por defecto retorna todos los objetos del modelo.
		Las subclases pueden filtrar por usuario, tenant, etc.
		"""
		return self.model.objects.all()

	def apply_filters(self, request, queryset):
		"""
		Aplica los filtros de la barra de búsqueda al queryset.
		Lee los parámetros GET: 'q' (texto libre), filter_field (valor exacto) y 'activo'.
		"""
		# Filtro por filter_field (ej: estado=PUBLICADO)
		if self.filter_field and request.GET.get(self.filter_field):
			queryset = queryset.filter(**{self.filter_field: request.GET[self.filter_field]})

		# Filtro por activo (booleano): convierte el string 'True'/'False' a bool
		activo_param = request.GET.get(self.active_field)
		if activo_param in ('True', 'False'):
			queryset = queryset.filter(**{self.active_field: activo_param == 'True'})

		# Búsqueda por texto: construye un OR entre todos los search_fields
		q = request.GET.get('q')
		if q and self.search_fields:
			from django.db.models import Q
			query = Q()
			for field in self.search_fields:
				query |= Q(**{f"{field}__icontains": q})
			queryset = queryset.filter(query)
		return queryset

	def get_filtered_queryset(self, request):
		"""
		Combina get_queryset + apply_filters. Punto de extensión alternativo
		si la subclase necesita modificar el resultado final antes del render.
		"""
		qs = self.get_queryset(request)
		return self.apply_filters(request, qs)

	# -----------------------------
    # Form handling
    # -----------------------------
	def get_form_kwargs(self, request, instance=None):
		"""
		Prepara los kwargs que se pasan al constructor del formulario.
		Si el request es POST, incluye request.POST como 'data' para validar.
		"""
		kwargs = {
			"instance": instance   # None en creación, objeto existente en edición
		}
		if request.method == "POST":
			kwargs["data"] = request.POST
		return kwargs

	def get_form(self, request, instance=None):
		"""
		Instancia el formulario. Sobreescribible en la subclase para agregar
		lógica de negocio sobre los campos (ej: deshabilitar campos según estado).
		"""
		kwargs = self.get_form_kwargs(request, instance)
		return self.form_class(**kwargs)

	def get_context_data(self, request, **kwargs):
		"""
		Hook: permite agregar variables extra al contexto del template.
		Las subclases deben llamar super() y luego añadir sus propias claves.
		"""
		return kwargs

	# -----------------------------
    # Hooks de ciclo de vida
    # -----------------------------
	def before_save(self, request, obj, form, is_create, original=None):
		"""
		Hook ejecutado ANTES de obj.save().
		Ideal para asignar campos calculados (ej: created_by = request.user)
		o para lanzar ValidationError si una regla de negocio impide guardar.

		Parámetros:
		    obj      -- instancia del modelo (aún no persistida)
		    form     -- formulario validado
		    is_create-- True si es una creación nueva
		    original -- dict con los valores anteriores del objeto (útil para detectar cambios)
		"""
		pass

	def after_save(self, request, obj, form, is_create, original=None):
		"""
		Hook ejecutado DESPUÉS de obj.save().
		Ideal para auditoría, notificaciones, o cualquier efecto colateral.

		Parámetros: igual que before_save, pero obj ya tiene PK asignado.
		"""
		pass

	def before_toggle(self, request, obj):
		"""Hook ejecutado antes de cambiar el campo activo/inactivo."""
		pass

	def after_toggle(self, request, obj):
		"""Hook ejecutado después de cambiar el campo activo/inactivo."""
		pass

	def serialize_row(self, obj):
		"""
		Convierte un objeto del modelo en un dict serializable a JSON.
		Omite campos relacionales (ManyToMany) y convierte el resto a str.
		Usado por el endpoint /json/.
		"""
		fields = self.get_list_display()
		data = {}

		for field in fields:
			value = getattr(obj, field)
			# Omitir relaciones ManyToMany (tienen .all())
			if hasattr(value, "all"):
				continue
			# Convertir a str todo excepto int y bool, que son JSON-nativos
			if hasattr(value, "__str__") and not isinstance(value, (int, bool)):
				value = str(value)
			data[field] = value

		return data

	# -----------------------------
    # Handlers HTTP principales
    # -----------------------------
	def get(self, request, *args, **kwargs):
		"""
		GET: si viene 'pk' en la URL -> formulario de edición.
		     de lo contrario          -> listado paginado/filtrado.
		"""
		if 'pk' in kwargs:
			# Formulario editar: carga el objeto existente
			obj = get_object_or_404(self.model, pk=kwargs['pk'])
			form = self.get_form(request, obj)

			context = self.get_context_data(
       			request,
          		form=form,
            	object=obj,
             	is_create=False
            )
			return render(request, self.form_template, context)

		# Listado: aplica búsqueda y filtros definidos en los parámetros GET
		queryset = self.get_filtered_queryset(request)
		context = self.get_context_data(
      		request,
        	object_list=queryset
        )
		return render(request, self.template_name, context)

	def post(self, request, *args, **kwargs):
		"""
		POST: crear o editar un objeto.
		  - Si hay 'pk' en la URL: edición de un objeto existente.
		  - Si no: creación de un objeto nuevo.
		El flujo es: validar form -> before_save hook -> save -> after_save hook -> redirect.
		Si before_save lanza ValidationError, el error se muestra en el formulario.
		"""
		if 'pk' in kwargs:
			# Edición: obtener el objeto y capturar su estado original
			obj = get_object_or_404(self.model, pk=kwargs['pk'])
			original = None
			if obj.pk:
				# Snapshot del estado previo para detectar cambios en los hooks
				original = self.model.objects.filter(pk=obj.pk).values().first()
			form = self.get_form(request, obj)
			is_create = False
		else:
			# Creación: no hay objeto previo
			obj = None
			original = None
			form = self.get_form(request)
			is_create = True

		if form.is_valid():
			# commit=False: obtenemos la instancia sin persistirla todavía
			# para que before_save pueda modificarla o rechazarla
			instance = form.save(commit=False)
			try:
				self.before_save(request, instance, form, is_create, original=original)
			except ValidationError as e:
				# El hook de negocio rechazó la operación: mostrar el error en el formulario
				form.add_error(None, e)
				context = self.get_context_data(request, form=form, object=obj, is_create=is_create)
				return render(request, self.form_template, context)

			instance.save()
			form.save_m2m()  # Guardar relaciones ManyToMany si las hubiera

			self.after_save(request, instance, form, is_create, original=original)

			# Auditoría automática: registrar CREAR o EDITAR en ControlCambio
			if is_create:
				cambios = build_cambios_create(form)
				accion  = 'CREAR'
			else:
				cambios = build_cambios_edit(form, original)
				accion  = 'EDITAR'
			registrar_cambio(request.user, accion, instance, cambios)

			return redirect(self.get_success_url(instance))

		# Formulario inválido: re-renderizar con errores
		context = self.get_context_data(request, form=form, object=obj, is_create=is_create)
		return render(request, self.form_template, context)

	def delete(self, request, pk):
		"""
		Elimina el objeto identificado por 'pk' tras recibir un POST de confirmación.
		Registra el evento ELIMINAR en auditoría y redirige al listado.
		"""
		obj = get_object_or_404(self.model, pk=pk)

		# Capturar datos para auditoría ANTES de borrar el objeto
		obj_id    = obj.pk
		obj_repr  = str(obj)
		modelo_id = f"{self.model._meta.app_label}.{self.model.__name__}"

		obj.delete()

		# Registrar en auditoría usando los kwargs directos (obj ya no existe en BD)
		registrar_cambio(
			request.user,
			'ELIMINAR',
			cambios={'objeto_eliminado': obj_repr},
			modelo=modelo_id,
			objeto_id=obj_id,
		)

		# Usar get_success_url para respetar cualquier override de la subclase.
		# Se pasa None porque el objeto ya fue eliminado y no existe en BD.
		return redirect(self.get_success_url(None))

	def toggle(self, request, pk):
		"""
		Activa o desactiva el objeto identificado por 'pk'.
		Invierte el valor del campo booleano configurado en active_field.
		Retorna JSON { success: true, <field>: <nuevo_valor> }.
		"""
		obj = get_object_or_404(self.model, pk=pk)

		field = self.get_active_field()
		# Verificar que el modelo realmente tiene el campo configurado
		if not hasattr(obj, field):
			return HttpResponseForbidden()

		self.before_toggle(request, obj)
		current = getattr(obj, field)
		setattr(obj, field, not current)  # Invertir el valor booleano
		obj.save()

		self.after_toggle(request, obj)

		# Auditoría automática: ACTIVAR o INACTIVAR según el nuevo valor
		nuevo_valor = getattr(obj, field)
		accion = 'ACTIVAR' if nuevo_valor else 'INACTIVAR'
		registrar_cambio(
			request.user,
			accion,
			obj,
			cambios={field: {'anterior': current, 'nuevo': nuevo_valor}},
		)

		return JsonResponse({
			"success": True,
			field: nuevo_valor
		})

	@classmethod
	def get_urls(cls):
		"""
		Genera y retorna la lista de URL patterns del módulo.
		Centraliza el registro de rutas para evitar que la subclase tenga que
		definir paths manualmente en su urls.py.

		Rutas generadas:
		  ''              -> ListView   (GET listado)
		  'json/'         -> JsonView   (GET datos JSON con filtros)
		  'add/'          -> AddView    (GET/POST crear)
		  '<pk>/'         -> cls        (GET/POST editar)
		  '<pk>/toggle/'  -> ToggleView (POST activar/inactivar)

		Patrón: cada vista interna hereda de cls para reutilizar toda la configuración.
		"""
		from django.urls import path

		class ListView(cls):
			"""Vista de listado; no requiere override específico."""
			pass

		class JsonView(cls):
			"""Endpoint JSON: devuelve el queryset filtrado serializado."""
			def get(self, request, *args, **kwargs):
				queryset = self.get_filtered_queryset(request)
				data = [
					self.serialize_row(obj)
					for obj in queryset
				]
				return JsonResponse(data, safe=False)

		class AddView(cls):
			"""Vista dedicada a crear. GET siempre muestra el formulario vacío."""
			def get(self, request, *args, **kwargs):
				form = self.get_form(request)
				context = self.get_context_data(request, form=form, object=None, is_create=True)
				return render(request, self.form_template, context)

		class ToggleView(cls):
			"""Vista del endpoint toggle activo/inactivo. Solo acepta POST."""
			def post(self, request, pk, *args, **kwargs):
				return self.toggle(request, pk)

		class DeleteView(cls):
			"""Vista de eliminación. Solo acepta POST para evitar borrados por GET."""
			def post(self, request, pk, *args, **kwargs):
				return self.delete(request, pk)

		return [
			path('', ListView.as_view(), name='list'),
			path('json/', JsonView.as_view(), name='json'),
			path('add/', AddView.as_view(), name='add'),
			path('<int:pk>/', cls.as_view(), name='edit'),
			path('<int:pk>/toggle/', ToggleView.as_view(), name='toggle'),
			path('<int:pk>/delete/', DeleteView.as_view(), name='delete'),
		]

	def get_success_url(self, obj):
		"""URL a la que redirigir tras guardar. Por defecto va al listado del módulo."""
		return reverse(f'{self.model._meta.app_label}:list')

