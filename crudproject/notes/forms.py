from django import forms
from .models import Anotacion

class AnotacionForm(forms.ModelForm):
	class Meta:
		model = Anotacion
		fields = ['titulo', 'detalle', 'estado']

	def clean_titulo(self):
		titulo = self.cleaned_data.get('titulo')
		if len(titulo) < 5:
			raise forms.ValidationError("El título debe tener al menos 5 caracteres.")
		return titulo

	def clean(self):
		cleaned_data = super().clean()
		estado = cleaned_data.get('estado')
		detalle = cleaned_data.get('detalle')

		if estado == 'PUBLICADO' and not detalle:
			self.add_error('detalle', 'El detalle es obligatorio para publicar.')

		return cleaned_data