"""
Utilidades de auditoría para el motor CRUD (core/audit.py).

Este módulo centraliza:
  - La serialización de valores a tipos JSON-seguros.
  - La construcción del dict de cambios para creaciones y ediciones.
  - La función principal `registrar_cambio` que persiste en ControlCambio.

Mantener esta lógica separada de BaseCrudView permite:
  - Reutilizarla desde cualquier parte del proyecto (vistas, signals, tareas).
  - Testearla de forma aislada.
  - Evitar acoplar el motor con la tabla de auditoría.
"""


def _serializar(valor):
    """
    Convierte un valor a un tipo nativo JSON-serializable.
    Los tipos primitivos (bool, int, float, str, None) se devuelven tal cual.
    Cualquier otro tipo (date, Decimal, FK, etc.) se convierte a str.
    """
    if valor is None or isinstance(valor, (bool, int, float, str)):
        return valor
    return str(valor)


def build_cambios_create(form):
    """
    Construye el dict de cambios para una operación de CREACIÓN.

    Como no existe estado previo, 'anterior' siempre es None.
    Se registra el valor inicial de cada campo presente en el formulario.

    Retorna: {campo: {'anterior': None, 'nuevo': valor}}
    """
    cambios = {}
    for nombre in form.cleaned_data:
        nuevo = form.cleaned_data.get(nombre)
        cambios[nombre] = {'anterior': None, 'nuevo': _serializar(nuevo)}
    return cambios


def build_cambios_edit(form, original):
    """
    Construye el dict de cambios para una operación de EDICIÓN.

    Solo incluye los campos que efectivamente cambiaron según form.changed_data,
    evitando ruido en el historial por campos no modificados.

    Parámetros:
        form     -- formulario validado (con .changed_data y .cleaned_data)
        original -- dict con los valores del objeto ANTES de la edición
                    (resultado de .values().first() antes del POST)

    Retorna: {campo: {'anterior': valor_viejo, 'nuevo': valor_nuevo}}
    """
    cambios = {}
    for nombre in form.changed_data:
        anterior = original.get(nombre) if original else None
        nuevo    = form.cleaned_data.get(nombre)
        cambios[nombre] = {
            'anterior': _serializar(anterior),
            'nuevo':    _serializar(nuevo),
        }
    return cambios


def registrar_cambio(usuario, accion, obj, cambios=None):
    """
    Persiste un registro de auditoría en la tabla ControlCambio.

    La importación de ControlCambio es diferida (dentro de la función)
    para evitar imports circulares: core.audit <- core.models no es un ciclo,
    pero si en el futuro core.models importara algo de audit, lo sería.

    Parámetros:
        usuario -- instancia de User autenticado en el request
        accion  -- string corto: 'CREAR', 'EDITAR', 'ACTIVAR', 'INACTIVAR', 'PUBLICAR'
        obj     -- instancia del modelo auditado; debe tener .pk asignado
        cambios -- dict {campo: {anterior, nuevo}}; si es None se guarda {}
    """
    from core.models import ControlCambio  # Importación diferida intencional

    ControlCambio.objects.create(
        usuario=usuario,
        accion=accion,
        # Identificador legible del modelo: "notes.Anotacion", "blog.Post", etc.
        modelo=f"{obj._meta.app_label}.{obj.__class__.__name__}",
        objeto_id=obj.pk,
        cambios=cambios or {},
    )
