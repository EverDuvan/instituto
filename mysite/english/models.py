from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator
import datetime

##############################
# 1. Modelos Base (Core)
##############################

class Consecutivo(models.Model):
    TIPO_CHOICES = [
        ('cobros', 'Recibos de Cobro'),
        ('egresos', 'Comprobantes de Egreso'),
        ('facturas', 'Facturas'),
        ('matriculas', 'Matrículas'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, unique=True)
    ultimo_numero = models.PositiveIntegerField(default=0)
    prefijo = models.CharField(max_length=10, blank=True, null=True)
    formato = models.CharField(max_length=50, default="{prefijo}{numero:04d}")
    reiniciar_anual = models.BooleanField(default=True)
    
    @classmethod
    def obtener_siguiente(cls, tipo):
        consecutivo, created = cls.objects.get_or_create(tipo=tipo)
        if consecutivo.reiniciar_anual and str(consecutivo.ultimo_numero)[:4] != str(datetime.datetime.now().year)[2:]:
            consecutivo.ultimo_numero = 0
        
        consecutivo.ultimo_numero += 1
        consecutivo.save()
        return consecutivo.formato.format(
            prefijo=consecutivo.prefijo or "",
            numero=consecutivo.ultimo_numero
        )

    def __str__(self):
        return f"Consecutivo {self.get_tipo_display()}"

class ConfiguracionInstituto(models.Model):
    nombre_instituto = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='configuracion/')
    nit = models.CharField(max_length=20)
    direccion = models.TextField()
    telefono_principal = models.CharField(max_length=20)
    telefonos_secundarios = models.CharField(max_length=100, blank=True)
    correo_principal = models.EmailField()
    correos_secundarios = models.CharField(max_length=200, blank=True)
    resolucion_autorizacion = models.CharField(max_length=100)
    terminos_condiciones = models.TextField()
    politica_privacidad = models.TextField()
    porcentaje_descuento_maximo = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    iva = models.DecimalField(max_digits=5, decimal_places=2, default=19.00)
    
    def __str__(self):
        return self.nombre_instituto

##############################
# 2. Modelos Académicos
##############################

class Programa(models.Model):
    AREAS_CHOICES = [
        ('ciencias', 'Ciencias'),
        ('humanidades', 'Humanidades'),
        ('tecnologia', 'Tecnología'),
        ('artes', 'Artes'),
        ('idiomas', 'Idiomas'),
    ]
    
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    area = models.CharField(max_length=20, choices=AREAS_CHOICES)
    descripcion = models.TextField()
    duracion_meses = models.PositiveIntegerField()
    horas_totales = models.PositiveIntegerField()
    costo_total = models.DecimalField(max_digits=12, decimal_places=2)
    activo = models.BooleanField(default=True)
    requisitos_ingreso = models.TextField()
    certificado_otorga = models.CharField(max_length=100)
    imagen = models.ImageField(upload_to='programas/', null=True, blank=True)
    
    class Meta:
        ordering = ['area', 'nombre']
        verbose_name_plural = "Programas"
    
    def __str__(self):
        return f"{self.nombre} ({self.get_area_display()})"

class Curso(models.Model):
    programa = models.ForeignKey(Programa, on_delete=models.CASCADE, related_name='cursos')
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    horas = models.PositiveIntegerField()
    orden = models.PositiveIntegerField()
    prerequisitos = models.ManyToManyField('self', symmetrical=False, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['programa', 'orden']
        unique_together = ('programa', 'codigo')
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class Grupo(models.Model):
    JORNADA_CHOICES = [
        ('mañana', 'Mañana (7:00-12:00)'),
        ('tarde', 'Tarde (13:00-18:00)'),
        ('noche', 'Noche (18:00-22:00)'),
        ('sabados', 'Sábados (8:00-13:00)'),
        ('virtual', 'Virtual'),
        ('personalizado', 'Personalizado'),
    ]
    
    ESTADO_CHOICES = [
        ('planificado', 'Planificado'),
        ('abierto', 'Inscripciones Abiertas'),
        ('proceso', 'En Proceso'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]
    
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=20)
    docente = models.ForeignKey('Docente', on_delete=models.SET_NULL, null=True, blank=True)
    jornada = models.CharField(max_length=20, choices=JORNADA_CHOICES)
    horario = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    aula = models.CharField(max_length=50)
    cupo_maximo = models.PositiveIntegerField()
    cupo_actual = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='planificado')
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    observaciones = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-fecha_inicio', 'curso']
        unique_together = ('curso', 'codigo')
    
    def __str__(self):
        return f"{self.curso} - Grupo {self.codigo}"

class PeriodoAcademico(models.Model):
    nombre = models.CharField(max_length=50)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)
    matricula_abierta = models.BooleanField(default=False)
    
    def __str__(self):
        return self.nombre

##############################
# 3. Modelos de Personas
##############################

class Estudiante(models.Model):
    TIPO_ID_CHOICES = [
        ('cc', 'Cédula de Ciudadanía'),
        ('ti', 'Tarjeta de Identidad'),
        ('ce', 'Cédula de Extranjería'),
        ('pasaporte', 'Pasaporte'),
    ]
    
    GENERO_CHOICES = [
        ('masculino', 'Masculino'),
        ('femenino', 'Femenino'),
        ('otro', 'Otro'),
        ('no_indica', 'Prefiero no indicar'),
    ]
    
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('graduado', 'Graduado'),
        ('retirado', 'Retirado'),
        ('suspendido', 'Suspendido'),
    ]
    
    # Información básica
    tipo_identificacion = models.CharField(max_length=20, choices=TIPO_ID_CHOICES)
    identificacion = models.CharField(max_length=20, unique=True)
    primer_nombre = models.CharField(max_length=100)
    segundo_nombre = models.CharField(max_length=100, blank=True, null=True)
    primer_apellido = models.CharField(max_length=100)
    segundo_apellido = models.CharField(max_length=100, blank=True, null=True)
    fecha_nacimiento = models.DateField()
    genero = models.CharField(max_length=20, choices=GENERO_CHOICES)
    lugar_nacimiento = models.CharField(max_length=100, blank=True, null=True)
    
    # Información de contacto
    direccion = models.TextField()
    barrio = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)
    departamento = models.CharField(max_length=100)
    telefono_principal = models.CharField(max_length=20)
    telefono_alterno = models.CharField(max_length=20, blank=True, null=True)
    correo = models.EmailField()
    
    # Información académica
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    fecha_ingreso = models.DateField()
    programa_actual = models.ForeignKey(Programa, on_delete=models.SET_NULL, null=True, blank=True)
    grupo_actual = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Información de salud
    eps = models.CharField(max_length=100, blank=True, null=True)
    grupo_sanguineo = models.CharField(max_length=10, blank=True, null=True)
    alergias = models.TextField(blank=True, null=True)
    condiciones_especiales = models.TextField(blank=True, null=True)
    
    # Documentos y permisos
    foto = models.ImageField(upload_to='estudiantes/fotos/', null=True, blank=True)
    contrato_firmado = models.BooleanField(default=False)
    fecha_contrato = models.DateField(null=True, blank=True)
    consentimiento_datos = models.BooleanField(default=False)
    autorizacion_imagen = models.BooleanField(default=False)
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['primer_apellido', 'primer_nombre']
        verbose_name_plural = "Estudiantes"
    
    @property
    def nombre_completo(self):
        return f"{self.primer_nombre} {self.segundo_nombre or ''} {self.primer_apellido} {self.segundo_apellido or ''}".replace("  ", " ")
    
    @property
    def edad(self):
        today = datetime.date.today()
        return today.year - self.fecha_nacimiento.year - ((today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))
    
    def __str__(self):
        return f"{self.nombre_completo} ({self.identificacion})"

class Docente(models.Model):
    TIPO_CONTRATO_CHOICES = [
        ('planta', 'Planta'),
        ('contratista', 'Contratista'),
        ('ocasional', 'Ocasional'),
        ('catedra', 'Cátedra'),
    ]
    
    # Información básica
    tipo_identificacion = models.CharField(max_length=20, choices=Estudiante.TIPO_ID_CHOICES)
    identificacion = models.CharField(max_length=20, unique=True)
    nombres = models.CharField(max_length=200)
    apellidos = models.CharField(max_length=200)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    genero = models.CharField(max_length=20, choices=Estudiante.GENERO_CHOICES)
    
    # Información profesional
    titulo_academico = models.CharField(max_length=100)
    especialidad = models.CharField(max_length=100)
    tipo_contrato = models.CharField(max_length=20, choices=TIPO_CONTRATO_CHOICES)
    fecha_vinculacion = models.DateField()
    activo = models.BooleanField(default=True)
    
    # Información de contacto
    direccion = models.TextField()
    telefono = models.CharField(max_length=20)
    telefono_alterno = models.CharField(max_length=20, blank=True, null=True)
    correo = models.EmailField()
    correo_institucional = models.EmailField(blank=True, null=True)
    
    # Documentos
    hoja_vida = models.FileField(upload_to='docentes/hojas_vida/', null=True, blank=True)
    foto = models.ImageField(upload_to='docentes/fotos/', null=True, blank=True)
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['apellidos', 'nombres']
        verbose_name_plural = "Docentes"
    
    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"
    
    def __str__(self):
        return f"{self.nombre_completo} - {self.especialidad}"

class Acudiente(models.Model):
    PARENTESCO_CHOICES = [
        ('padre', 'Padre'),
        ('madre', 'Madre'),
        ('abuelo', 'Abuelo/a'),
        ('tio', 'Tío/a'),
        ('hermano', 'Hermano/a'),
        ('tutor', 'Tutor Legal'),
        ('otro', 'Otro'),
    ]
    
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='acudientes')
    tipo_identificacion = models.CharField(max_length=20, choices=Estudiante.TIPO_ID_CHOICES)
    identificacion = models.CharField(max_length=20)
    nombre_completo = models.CharField(max_length=200)
    parentesco = models.CharField(max_length=50, choices=PARENTESCO_CHOICES)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20)
    telefono_alterno = models.CharField(max_length=20, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    ocupacion = models.CharField(max_length=100, blank=True, null=True)
    responsable_pago = models.BooleanField(default=False)
    responsable_academico = models.BooleanField(default=False)
    emergencia = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Acudientes"
        unique_together = ('estudiante', 'identificacion')
    
    def __str__(self):
        return f"{self.nombre_completo} ({self.get_parentesco_display()}) - {self.estudiante}"

##############################
# 4. Modelos Financieros
##############################

class ConceptoCobro(models.Model):
    TIPO_CHOICES = [
        ('matricula', 'Matrícula'),
        ('pension', 'Pensión'),
        ('materiales', 'Materiales'),
        ('certificado', 'Certificados'),
        ('otros', 'Otros'),
    ]
    
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    aplica_iva = models.BooleanField(default=False)
    aplica_descuento = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    descripcion = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['tipo', 'nombre']
        verbose_name_plural = "Conceptos de Cobro"
    
    def __str__(self):
        return f"{self.nombre} (${self.valor:,.2f})"

class Factura(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('parcial', 'Parcialmente Pagada'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
        ('vencida', 'Vencida'),
    ]
    
    consecutivo = models.CharField(max_length=20, unique=True, editable=False)
    estudiante = models.ForeignKey(Estudiante, on_delete=models.PROTECT)
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    saldo = models.DecimalField(max_digits=12, decimal_places=2)
    observaciones = models.TextField(blank=True, null=True)
    creada_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='facturas_creadas')
    
    class Meta:
        ordering = ['-fecha_emision']
        verbose_name_plural = "Facturas"
    
    def save(self, *args, **kwargs):
        if not self.consecutivo:
            self.consecutivo = Consecutivo.obtener_siguiente('facturas')
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Factura {self.consecutivo} - {self.estudiante} (${self.total:,.2f})"

class ItemFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='items')
    concepto = models.ForeignKey(ConceptoCobro, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name_plural = "Ítems de Factura"
    
    def __str__(self):
        return f"{self.concepto} x {self.cantidad}"

class Cobro(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('parcial', 'Parcial'),
        ('completo', 'Completo'),
        ('anulado', 'Anulado'),
    ]
    
    TIPO_INGRESO_CHOICES = [
        ('matricula', 'Matrícula'),
        ('pension', 'Pensión'),
        ('material', 'Material'),
        ('certificado', 'Certificado'),
        ('otros', 'Otros'),
    ]
    
    consecutivo = models.CharField(max_length=20, unique=True, editable=False)
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, related_name='cobros')
    fecha = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    saldo = models.DecimalField(max_digits=12, decimal_places=2)
    tipo_ingreso = models.CharField(max_length=20, choices=TIPO_INGRESO_CHOICES, default='pension')
    periodo_academico = models.ForeignKey(PeriodoAcademico, on_delete=models.SET_NULL, null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='cobros_creados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']
        verbose_name_plural = "Recibos de Cobro"
    
    def save(self, *args, **kwargs):
        if not self.consecutivo:
            self.consecutivo = Consecutivo.obtener_siguiente('cobros')
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Recibo {self.consecutivo} - {self.factura.estudiante}"

class DetallePago(models.Model):
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
        ('tarjeta_credito', 'Tarjeta Crédito'),
        ('tarjeta_debito', 'Tarjeta Débito'),
        ('nequi', 'Nequi'),
        ('daviplata', 'Daviplata'),
        ('bancolombia', 'Bancolombia'),
        ('otro', 'Otro'),
    ]
    
    cobro = models.ForeignKey(Cobro, on_delete=models.CASCADE, related_name='pagos')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    banco = models.CharField(max_length=50, blank=True, null=True)
    numero_comprobante = models.CharField(max_length=50, blank=True, null=True)
    fecha = models.DateField()
    observaciones = models.TextField(blank=True, null=True)
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='pagos_registrados')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']
        verbose_name_plural = "Detalles de Pago"
    
    def __str__(self):
        return f"Pago {self.id} - {self.get_metodo_pago_display()} (${self.valor:,.2f})"

class Egreso(models.Model):
    TIPO_CHOICES = [
        ('nomina', 'Nómina'),
        ('arriendo', 'Arriendo'),
        ('servicios', 'Servicios Públicos'),
        ('materiales', 'Materiales'),
        ('equipos', 'Equipos'),
        ('mantenimiento', 'Mantenimiento'),
        ('otros', 'Otros Gastos'),
    ]
    
    CATEGORIA_DETALLADA_CHOICES = [
        ('docente', 'Pago Docentes'),
        ('administrativo', 'Pago Administrativos'),
        ('arriendo_sede', 'Arriendo Sede'),
        ('servicios_publicos', 'Servicios Públicos'),
        ('material_oficina', 'Material de Oficina'),
        ('material_enseñanza', 'Material de Enseñanza'),
        ('equipos_computo', 'Equipos de Cómputo'),
        ('mantenimiento_edificio', 'Mantenimiento Edificio'),
        ('mantenimiento_equipos', 'Mantenimiento Equipos'),
        ('publicidad', 'Publicidad y Marketing'),
        ('capacitacion', 'Capacitación'),
        ('impuestos', 'Impuestos'),
        ('seguros', 'Seguros'),
        ('otros', 'Otros'),
    ]
    
    consecutivo = models.CharField(max_length=20, unique=True, editable=False)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    concepto = models.CharField(max_length=255)
    beneficiario = models.CharField(max_length=255)
    documento_soporte = models.CharField(max_length=50)
    fecha = models.DateField()
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    forma_pago = models.CharField(max_length=20, choices=DetallePago.METODO_PAGO_CHOICES)
    categoria_detallada = models.CharField(max_length=100, choices=CATEGORIA_DETALLADA_CHOICES, default='otros')
    observaciones = models.TextField(blank=True, null=True)
    aprobado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='egresos_aprobados')
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='egresos_creados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']
        verbose_name_plural = "Comprobantes de Egreso"
    
    def save(self, *args, **kwargs):
        if not self.consecutivo:
            self.consecutivo = Consecutivo.obtener_siguiente('egresos')
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Egreso {self.consecutivo} - {self.concepto} (${self.valor_total:,.2f})"

class DetalleEgreso(models.Model):
    egreso = models.ForeignKey(Egreso, on_delete=models.CASCADE, related_name='detalles')
    descripcion = models.CharField(max_length=255)
    cantidad = models.PositiveIntegerField(default=1)
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        verbose_name_plural = "Detalles de Egreso"
    
    def __str__(self):
        return f"{self.descripcion} x {self.cantidad}"

##############################
# 5. Modelos Académicos (Cont.)
##############################

class Matricula(models.Model):
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('retirada', 'Retirada'),
        ('finalizada', 'Finalizada'),
        ('suspendida', 'Suspendida'),
    ]
    
    consecutivo = models.CharField(max_length=20, unique=True, editable=False)
    estudiante = models.ForeignKey(Estudiante, on_delete=models.PROTECT)
    programa = models.ForeignKey(Programa, on_delete=models.PROTECT)
    grupo = models.ForeignKey(Grupo, on_delete=models.PROTECT)
    periodo = models.ForeignKey(PeriodoAcademico, on_delete=models.PROTECT)
    fecha_matricula = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activa')
    observaciones = models.TextField(blank=True, null=True)
    creada_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='matriculas_creadas')
    
    class Meta:
        ordering = ['-fecha_matricula']
        verbose_name_plural = "Matrículas"
        unique_together = ('estudiante', 'periodo', 'programa')
    
    def save(self, *args, **kwargs):
        if not self.consecutivo:
            self.consecutivo = Consecutivo.obtener_siguiente('matriculas')
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Matrícula {self.consecutivo} - {self.estudiante}"

class Asistencia(models.Model):
    ESTADO_CHOICES = [
        ('asistio', 'Asistió'),
        ('falto', 'Faltó'),
        ('tardanza', 'Llegó tarde'),
        ('justificado', 'Justificado'),
    ]
    
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora_llegada = models.TimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    observaciones = models.TextField(blank=True, null=True)
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='asistencias_registradas')
    
    class Meta:
        ordering = ['-fecha', 'estudiante']
        verbose_name_plural = "Asistencias"
        unique_together = ('estudiante', 'grupo', 'fecha')
    
    def __str__(self):
        return f"Asistencia {self.estudiante} - {self.fecha}"

class Calificacion(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    periodo = models.ForeignKey(PeriodoAcademico, on_delete=models.CASCADE)
    nota1 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    nota2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    nota3 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    nota_final = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)
    docente = models.ForeignKey(Docente, on_delete=models.PROTECT)
    
    class Meta:
        ordering = ['periodo', 'curso', 'estudiante']
        verbose_name_plural = "Calificaciones"
        unique_together = ('estudiante', 'curso', 'grupo', 'periodo')
    
    def __str__(self):
        return f"Calificación {self.estudiante} - {self.curso}"

class ObservacionAcademica(models.Model):
    TIPO_CHOICES = [
        ('academica', 'Académica'),
        ('comportamiento', 'Comportamiento'),
        ('recomendacion', 'Recomendación'),
        ('felicitacion', 'Felicitación'),
    ]
    
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    fecha = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.TextField()
    acciones = models.TextField(blank=True, null=True)
    seguimiento = models.TextField(blank=True, null=True)
    docente = models.ForeignKey(Docente, on_delete=models.PROTECT)
    
    class Meta:
        ordering = ['-fecha', 'estudiante']
        verbose_name_plural = "Observaciones Académicas"
    
    def __str__(self):
        return f"Observación {self.get_tipo_display()} - {self.estudiante}"

##############################
# 6. Modelos de Gestión Institucional
##############################

class Evento(models.Model):
    TIPO_CHOICES = [
        ('academico', 'Académico'),
        ('administrativo', 'Administrativo'),
        ('cultural', 'Cultural'),
        ('reunion', 'Reunión'),
        ('capacitacion', 'Capacitación'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.TextField()
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    lugar = models.CharField(max_length=100)
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='media')
    participantes = models.ManyToManyField(User, blank=True)
    grupos = models.ManyToManyField(Grupo, blank=True)
    recordatorio = models.BooleanField(default=False)
    recordatorio_fecha = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='eventos_creados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name_plural = "Eventos"
    
    def __str__(self):
        return f"{self.titulo} - {self.fecha_inicio}"

class Comunicado(models.Model):
    DESTINATARIO_CHOICES = [
        ('estudiantes', 'Estudiantes'),
        ('docentes', 'Docentes'),
        ('todos', 'Todos'),
        ('personalizado', 'Personalizado'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('normal', 'Normal'),
        ('importante', 'Importante'),
        ('urgente', 'Urgente'),
    ]
    
    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateField()
    destinatarios = models.CharField(max_length=20, choices=DESTINATARIO_CHOICES)
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='normal')
    grupos_destino = models.ManyToManyField(Grupo, blank=True)
    usuarios_destino = models.ManyToManyField(User, blank=True, related_name='comunicados_recibidos')
    publicado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='comunicados_publicados')
    
    class Meta:
        ordering = ['-fecha_publicacion']
        verbose_name_plural = "Comunicados"
    
    def __str__(self):
        return f"{self.titulo} - {self.fecha_publicacion}"

class DocumentoInstitucional(models.Model):
    TIPO_CHOICES = [
        ('manual', 'Manual'),
        ('reglamento', 'Reglamento'),
        ('informe', 'Informe'),
        ('contrato', 'Contrato'),
        ('otro', 'Otro'),
    ]
    
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.TextField(blank=True, null=True)
    archivo = models.FileField(upload_to='documentos_institucionales/')
    fecha_publicacion = models.DateField(auto_now_add=True)
    fecha_actualizacion = models.DateField(auto_now=True)
    publicado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='documentos_publicados')
    
    class Meta:
        ordering = ['-fecha_publicacion']
        verbose_name_plural = "Documentos Institucionales"
    
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

##############################
# 7. Modelos de Soporte
##############################

class DocumentoEstudiante(models.Model):
    TIPO_CHOICES = [
        ('identidad', 'Documento de Identidad'),
        ('registro', 'Registro Civil'),
        ('certificado', 'Certificado Estudios'),
        ('medico', 'Certificado Médico'),
        ('contrato', 'Contrato'),
        ('foto', 'Fotografía'),
        ('otros', 'Otros'),
    ]
    
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='documentos')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    archivo = models.FileField(upload_to='documentos/estudiantes/')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True, null=True)
    subido_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='documentos_subidos')
    
    class Meta:
        ordering = ['estudiante', '-fecha_subida']
        verbose_name_plural = "Documentos de Estudiantes"
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.estudiante}"

class Incidencia(models.Model):
    TIPO_CHOICES = [
        ('academica', 'Académica'),
        ('conducta', 'Conducta'),
        ('salud', 'Salud'),
        ('administrativa', 'Administrativa'),
        ('tecnica', 'Técnica'),
        ('otra', 'Otra'),
    ]
    
    ESTADO_CHOICES = [
        ('abierta', 'Abierta'),
        ('en_proceso', 'En Proceso'),
        ('resuelta', 'Resuelta'),
        ('cerrada', 'Cerrada'),
    ]
    
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.TextField()
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, null=True, blank=True)
    grupo = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True, blank=True)
    docente = models.ForeignKey(Docente, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='abierta')
    medidas = models.TextField(blank=True, null=True)
    seguimiento = models.TextField(blank=True, null=True)
    reportado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='incidencias_reportadas')
    responsable = models.ForeignKey(User, on_delete=models.PROTECT, related_name='incidencias_asignadas', null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_reporte']
        verbose_name_plural = "Incidencias"
    
    def __str__(self):
        return f"Incidencia {self.id} - {self.get_tipo_display()}"

class SeguimientoIncidencia(models.Model):
    incidencia = models.ForeignKey(Incidencia, on_delete=models.CASCADE, related_name='seguimientos')
    descripcion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='seguimientos_incidencias')
    
    class Meta:
        ordering = ['fecha']
        verbose_name_plural = "Seguimientos de Incidencias"
    
    def __str__(self):
        return f"Seguimiento {self.id} - Incidencia {self.incidencia.id}"

##############################
# 8. Reportes Económicos
##############################

class ReporteEconomico(models.Model):
    TIPO_REPORTE_CHOICES = [
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
        ('trimestral', 'Trimestral'),
        ('anual', 'Anual'),
        ('personalizado', 'Personalizado'),
    ]
    
    TIPO_MOVIMIENTO_CHOICES = [
        ('ingresos', 'Ingresos'),
        ('egresos', 'Egresos'),
        ('ambos', 'Ambos'),
    ]
    
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    tipo_reporte = models.CharField(max_length=20, choices=TIPO_REPORTE_CHOICES)
    tipo_movimiento = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO_CHOICES)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    generado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='reportes_generados')
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    archivo = models.FileField(upload_to='reportes_economicos/')
    parametros = models.JSONField(default=dict)  # Para almacenar filtros adicionales
    
    class Meta:
        ordering = ['-fecha_generacion']
        verbose_name = "Reporte Económico"
        verbose_name_plural = "Reportes Económicos"
    
    def __str__(self):
        return f"{self.nombre} - {self.get_tipo_reporte_display()}"

class ResumenEconomico(models.Model):
    reporte = models.OneToOneField(ReporteEconomico, on_delete=models.CASCADE, related_name='resumen')
    
    # Totales
    total_ingresos = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_egresos = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Desglose de ingresos
    ingresos_matriculas = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ingresos_pensiones = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ingresos_materiales = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ingresos_certificados = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ingresos_otros = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Desglose de egresos
    egresos_nomina = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    egresos_arriendos = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    egresos_servicios = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    egresos_materiales = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    egresos_equipos = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    egresos_mantenimiento = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    egresos_otros = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Métodos de pago
    efectivo_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    transferencias_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tarjetas_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    billeteras_digitales_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = "Resumen Económico"
        verbose_name_plural = "Resúmenes Económicos"
    
    def __str__(self):
        return f"Resumen de {self.reporte}"

class ConfiguracionReporte(models.Model):
    nombre = models.CharField(max_length=100)
    tipo_reporte = models.CharField(max_length=20, choices=ReporteEconomico.TIPO_REPORTE_CHOICES)
    formato_salida = models.CharField(max_length=20, choices=[
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('html', 'HTML'),
        ('ambos', 'PDF y Excel'),
    ], default='pdf')
    incluir_desglose = models.BooleanField(default=True)
    incluir_graficas = models.BooleanField(default=True)
    agrupar_por = models.CharField(max_length=50, choices=[
        ('dia', 'Día'),
        ('semana', 'Semana'),
        ('mes', 'Mes'),
        ('tipo', 'Tipo de Movimiento'),
        ('categoria', 'Categoría'),
        ('metodo_pago', 'Método de Pago'),
    ], default='tipo')
    parametros_personalizados = models.JSONField(default=dict)
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='config_reportes_creados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Configuración de Reporte"
        verbose_name_plural = "Configuraciones de Reporte"
    
    def __str__(self):
        return self.nombre

class PlantillaReporte(models.Model):
    nombre = models.CharField(max_length=100)
    tipo_reporte = models.CharField(max_length=20, choices=ReporteEconomico.TIPO_REPORTE_CHOICES)
    archivo = models.FileField(upload_to='plantillas_reportes/')
    es_default = models.BooleanField(default=False)
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='plantillas_creadas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Plantilla de Reporte"
        verbose_name_plural = "Plantillas de Reporte"
    
    def __str__(self):
        return self.nombre
    
    def save(self, *args, **kwargs):
        if self.es_default:
            PlantillaReporte.objects.filter(
                tipo_reporte=self.tipo_reporte
            ).update(es_default=False)
        super().save(*args, **kwargs)

class ReporteProgramado(models.Model):
    FRECUENCIA_CHOICES = [
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
        ('trimestral', 'Trimestral'),
        ('anual', 'Anual'),
    ]
    
    configuracion = models.ForeignKey(ConfiguracionReporte, on_delete=models.CASCADE)
    frecuencia = models.CharField(max_length=20, choices=FRECUENCIA_CHOICES)
    proxima_ejecucion = models.DateTimeField()
    ultima_ejecucion = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    destinatarios = models.TextField()  # Lista de correos separados por coma
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='reportes_programados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Reporte Programado"
        verbose_name_plural = "Reportes Programados"
    
    def __str__(self):
        return f"Reporte {self.configuracion} - {self.get_frecuencia_display()}"

##############################
# 9. Auditoría y Seguridad
##############################

class Auditoria(models.Model):
    TIPO_CHOICES = [
        ('creacion', 'Creación'),
        ('modificacion', 'Modificación'),
        ('eliminacion', 'Eliminación'),
        ('login', 'Inicio de Sesión'),
        ('logout', 'Cierre de Sesión'),
        ('otro', 'Otro'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='auditorias_realizadas')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    modelo = models.CharField(max_length=100)
    objeto_id = models.PositiveIntegerField(null=True, blank=True)
    descripcion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField()
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha']
        verbose_name_plural = "Registros de Auditoría"
    
    def __str__(self):
        return f"Auditoría {self.id} - {self.usuario} - {self.get_tipo_display()}"

class Backup(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.CharField(max_length=255)
    archivo = models.FileField(upload_to='backups/')
    realizado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='backups_realizados')
    tipo = models.CharField(max_length=20, choices=[
        ('completo', 'Completo'),
        ('parcial', 'Parcial'),
        ('automatico', 'Automático'),
    ])
    
    class Meta:
        ordering = ['-fecha']
        verbose_name_plural = "Copias de Seguridad"
    
    def __str__(self):
        return f"Backup {self.fecha} - {self.tipo}"