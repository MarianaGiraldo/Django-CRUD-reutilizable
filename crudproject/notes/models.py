from django.db import models
from django.contrib.auth.models import User

class Anotacion(models.Model):
	ESTADOS = (
		('BORRADOR', 'Borrador'),
		('PUBLICADO', 'Publicado'),
		('ARCHIVADO', 'Archivado'),
	)

	titulo = models.CharField(max_length=200)
	detalle = models.TextField(blank=True, null=True)
	estado = models.CharField(max_length=20, choices=ESTADOS, default='BORRADOR')
	activo = models.BooleanField(default=True)
	created_by = models.ForeignKey(User, on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = 'Anotación'
		verbose_name_plural = 'Anotaciones'

	def __str__(self):
		return str(self.titulo) if self.titulo else ""