from django.apps import AppConfig


class UiConfig(AppConfig):
    # App transversal de presentación: únicamente almacena los templates base
    # y los templates de los módulos de negocio.
    # No contiene modelos ni vistas propias.
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ui'
