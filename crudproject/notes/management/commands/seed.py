from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from notes.models import Anotacion


DATOS = [
    {
        'titulo': 'Entregar ensayo de Cálculo III',
        'detalle': 'Resolver los ejercicios de series de Taylor y subir el PDF al portal antes del viernes a las 11:59 pm.',
        'estado': 'PUBLICADO',
        'activo': True,
    },
    {
        'titulo': 'Estudiar para parcial de Física',
        'detalle': 'Repasar los temas: movimiento ondulatorio, óptica geométrica y termodinámica. El examen es el martes en el aula 304.',
        'estado': 'BORRADOR',
        'activo': True,
    },
    {
        'titulo': 'Renovar carnet universitario',
        'detalle': None,
        'estado': 'BORRADOR',
        'activo': True,
    },
    {
        'titulo': 'Proyecto final de Bases de Datos',
        'detalle': 'Diseñar el modelo ER, implementar en PostgreSQL y documentar las consultas. Entrega: última semana del semestre.',
        'estado': 'PUBLICADO',
        'activo': True,
    },
    {
        'titulo': 'Pagar matrícula segundo semestre',
        'detalle': 'Verificar monto en el portal estudiantil y realizar el pago antes del 15 del mes para evitar recargo.',
        'estado': 'BORRADOR',
        'activo': False,
    },
    {
        'titulo': 'Leer capítulos 4 y 5 de Algoritmos',
        'detalle': 'Cormen, capítulos de ordenamiento por comparación y estructuras de datos avanzadas. Habrá quiz el jueves.',
        'estado': 'ARCHIVADO',
        'activo': True,
    },
    {
        'titulo': 'Conseguir carta de recomendación',
        'detalle': None,
        'estado': 'BORRADOR',
        'activo': False,
    },
    {
        'titulo': 'Inscribir materias del próximo semestre',
        'detalle': 'Revisar el pensum y seleccionar las materias disponibles. Inscripción abre el lunes a las 8 am, cupos limitados.',
        'estado': 'ARCHIVADO',
        'activo': True,
    },
    {
        'titulo': 'Preparar exposición de Redes',
        'detalle': 'Tema asignado: protocolo TCP/IP y modelo OSI. Presentación de 15 minutos con diapositivas. Grupo de 3 personas.',
        'estado': 'BORRADOR',
        'activo': True,
    },
    {
        'titulo': 'Devolver libros a la biblioteca',
        'detalle': 'Tengo prestados: Introducción a la IA (Russell) y Clean Code (Martin). Vencen el próximo miércoles.',
        'estado': 'PUBLICADO',
        'activo': True,
    },
]


class Command(BaseCommand):
    help = 'Carga datos de prueba para el módulo de Anotaciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Elimina todas las anotaciones existentes antes de insertar',
        )

    def handle(self, *args, **options):
        # Obtener o crear el usuario admin para asignar como autor
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_superuser': True, 'is_staff': True}
        )

        if options['flush']:
            count, _ = Anotacion.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'  {count} anotaciones eliminadas.'))

        creadas = 0
        for dato in DATOS:
            Anotacion.objects.create(
                titulo=dato['titulo'],
                detalle=dato['detalle'],
                estado=dato['estado'],
                activo=dato['activo'],
                created_by=user,
            )
            creadas += 1
            self.stdout.write(f"  + {dato['titulo']} [{dato['estado']}]")

        self.stdout.write(self.style.SUCCESS(f'\n{creadas} anotaciones creadas correctamente.'))
