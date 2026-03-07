from django import forms
from .models import Anotacion

class AnotacionForm(forms.ModelForm):
    class Meta:
        model = Anotacion
        fields = ['titulo', 'detalle', 'estado', 'activo']
