from django.contrib import admin
from .models import *

# Registrar todos los modelos
admin.site.register(Consecutivo)
admin.site.register(ConfiguracionInstituto)
admin.site.register(Programa)
admin.site.register(Curso)
admin.site.register(Grupo)
admin.site.register(PeriodoAcademico)
admin.site.register(Estudiante)
admin.site.register(Docente)
admin.site.register(Acudiente)
admin.site.register(ConceptoCobro)
admin.site.register(Factura)
admin.site.register(ItemFactura)
admin.site.register(Cobro)
admin.site.register(DetallePago)
admin.site.register(Egreso)
admin.site.register(DetalleEgreso)
admin.site.register(Matricula)
admin.site.register(Asistencia)
admin.site.register(Calificacion)
admin.site.register(ObservacionAcademica)
admin.site.register(Evento)
admin.site.register(Comunicado)
admin.site.register(DocumentoInstitucional)
admin.site.register(DocumentoEstudiante)
admin.site.register(Incidencia)
admin.site.register(SeguimientoIncidencia)
admin.site.register(ReporteEconomico)
admin.site.register(ResumenEconomico)
admin.site.register(ConfiguracionReporte)
admin.site.register(PlantillaReporte)
admin.site.register(ReporteProgramado)
admin.site.register(Auditoria)
admin.site.register(Backup)