from django.urls import path
from .views import AnotacionCrudView

# get_urls() genera automáticamente: list, json, add, edit, toggle
# Este patrón evita definir rutas manualmente en cada módulo de negocio
app_name = 'notes'
urlpatterns = AnotacionCrudView.get_urls()
