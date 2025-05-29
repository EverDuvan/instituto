from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView, FormView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.http import HttpResponse, JsonResponse, FileResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.conf import settings
import csv
import io
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from openpyxl import Workbook
from django.template.loader import get_template
from xhtml2pdf import pisa

from .models import *
from .forms import *

# ========================================================
# Módulo 1: Autenticación y Perfil de Usuario
# ========================================================

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_estudiantes'] = Estudiante.objects.count()
        context['total_docentes'] = Docente.objects.count()
        context['total_grupos'] = Grupo.objects.count()
        context['ingresos_mes'] = Cobro.objects.filter(
            fecha__month=timezone.now().month
        ).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        context['egresos_mes'] = Egreso.objects.filter(
            fecha__month=timezone.now().month
        ).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        context['eventos_proximos'] = Evento.objects.filter(
            fecha_inicio__gte=timezone.now()
        ).order_by('fecha_inicio')[:5]
        context['facturas_pendientes'] = Factura.objects.filter(
            estado='pendiente'
        ).order_by('fecha_vencimiento')[:5]
        return context

class PerfilUsuarioView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = PerfilUsuarioForm
    template_name = 'registration/perfil.html'
    success_url = reverse_lazy('perfil')
    
    def get_object(self):
        return self.request.user

class CambiarPasswordView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'registration/cambiar_password.html'
    success_url = reverse_lazy('perfil')

# ========================================================
# Módulo 2: Gestión de Personas
# ========================================================

# Estudiantes
class EstudianteListView(LoginRequiredMixin, ListView):
    model = Estudiante
    template_name = 'personas/estudiante_list.html'
    context_object_name = 'estudiantes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q')
        estado = self.request.GET.get('estado')
        programa = self.request.GET.get('programa')
        
        if q:
            queryset = queryset.filter(
                Q(primer_nombre__icontains=q) |
                Q(primer_apellido__icontains=q) |
                Q(identificacion__icontains=q)
            )
        if estado:
            queryset = queryset.filter(estado=estado)
        if programa:
            queryset = queryset.filter(programa_actual_id=programa)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['programas'] = Programa.objects.all()
        return context

class EstudianteCreateView(LoginRequiredMixin, CreateView):
    model = Estudiante
    form_class = EstudianteForm
    template_name = 'personas/estudiante_form.html'
    success_url = reverse_lazy('estudiante_list')
    
    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        return super().form_valid(form)

class EstudianteDetailView(LoginRequiredMixin, DetailView):
    model = Estudiante
    template_name = 'personas/estudiante_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['acudientes'] = self.object.acudientes.all()
        context['matriculas'] = self.object.matricula_set.all()
        context['documentos'] = self.object.documentos.all()
        context['facturas'] = Factura.objects.filter(estudiante=self.object)[:10]
        return context

class EstudianteUpdateView(LoginRequiredMixin, UpdateView):
    model = Estudiante
    form_class = EstudianteForm
    template_name = 'personas/estudiante_form.html'
    success_url = reverse_lazy('estudiante_list')

class EstudianteDeleteView(LoginRequiredMixin, DeleteView):
    model = Estudiante
    template_name = 'personas/estudiante_confirm_delete.html'
    success_url = reverse_lazy('estudiante_list')

# Docentes
class DocenteListView(LoginRequiredMixin, ListView):
    model = Docente
    template_name = 'personas/docente_list.html'
    context_object_name = 'docentes'
    paginate_by = 20

class DocenteCreateView(LoginRequiredMixin, CreateView):
    model = Docente
    form_class = DocenteForm
    template_name = 'personas/docente_form.html'
    success_url = reverse_lazy('docente_list')

class DocenteDetailView(LoginRequiredMixin, DetailView):
    model = Docente
    template_name = 'personas/docente_detail.html'

class DocenteUpdateView(LoginRequiredMixin, UpdateView):
    model = Docente
    form_class = DocenteForm
    template_name = 'personas/docente_form.html'
    success_url = reverse_lazy('docente_list')

class DocenteDeleteView(LoginRequiredMixin, DeleteView):
    model = Docente
    template_name = 'personas/docente_confirm_delete.html'
    success_url = reverse_lazy('docente_list')

# Acudientes
class AcudienteListView(LoginRequiredMixin, ListView):
    model = Acudiente
    template_name = 'personas/acudiente_list.html'
    context_object_name = 'acudientes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        estudiante_id = self.request.GET.get('estudiante_id')
        
        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        return queryset

class AcudienteCreateView(LoginRequiredMixin, CreateView):
    model = Acudiente
    form_class = AcudienteForm
    template_name = 'personas/acudiente_form.html'
    
    def get_success_url(self):
        return reverse_lazy('estudiante_detail', kwargs={'pk': self.object.estudiante.id})

class AcudienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Acudiente
    form_class = AcudienteForm
    template_name = 'personas/acudiente_form.html'
    
    def get_success_url(self):
        return reverse_lazy('estudiante_detail', kwargs={'pk': self.object.estudiante.id})

class AcudienteDeleteView(LoginRequiredMixin, DeleteView):
    model = Acudiente
    template_name = 'personas/acudiente_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('estudiante_detail', kwargs={'pk': self.object.estudiante.id})

# ========================================================
# Módulo 3: Gestión Académica
# ========================================================

# Programas Académicos
class ProgramaListView(LoginRequiredMixin, ListView):
    model = Programa
    template_name = 'academicas/programa_list.html'
    context_object_name = 'programas'

class ProgramaCreateView(LoginRequiredMixin, CreateView):
    model = Programa
    form_class = ProgramaForm
    template_name = 'academicas/programa_form.html'
    success_url = reverse_lazy('programa_list')

class ProgramaDetailView(LoginRequiredMixin, DetailView):
    model = Programa
    template_name = 'academicas/programa_detail.html'

class ProgramaUpdateView(LoginRequiredMixin, UpdateView):
    model = Programa
    form_class = ProgramaForm
    template_name = 'academicas/programa_form.html'
    success_url = reverse_lazy('programa_list')

class ProgramaDeleteView(LoginRequiredMixin, DeleteView):
    model = Programa
    template_name = 'academicas/programa_confirm_delete.html'
    success_url = reverse_lazy('programa_list')

# Cursos
class CursoListView(LoginRequiredMixin, ListView):
    model = Curso
    template_name = 'academicas/curso_list.html'
    context_object_name = 'cursos'
    
    def get_queryset(self):
        programa_id = self.request.GET.get('programa_id')
        if programa_id:
            return Curso.objects.filter(programa_id=programa_id)
        return Curso.objects.all()

class CursoCreateView(LoginRequiredMixin, CreateView):
    model = Curso
    form_class = CursoForm
    template_name = 'academicas/curso_form.html'
    success_url = reverse_lazy('curso_list')

class CursoDetailView(LoginRequiredMixin, DetailView):
    model = Curso
    template_name = 'academicas/curso_detail.html'

class CursoUpdateView(LoginRequiredMixin, UpdateView):
    model = Curso
    form_class = CursoForm
    template_name = 'academicas/curso_form.html'
    success_url = reverse_lazy('curso_list')

class CursoDeleteView(LoginRequiredMixin, DeleteView):
    model = Curso
    template_name = 'academicas/curso_confirm_delete.html'
    success_url = reverse_lazy('curso_list')

# Grupos
class GrupoListView(LoginRequiredMixin, ListView):
    model = Grupo
    template_name = 'academicas/grupo_list.html'
    context_object_name = 'grupos'
    
    def get_queryset(self):
        curso_id = self.request.GET.get('curso_id')
        estado = self.request.GET.get('estado')
        
        queryset = Grupo.objects.all()
        if curso_id:
            queryset = queryset.filter(curso_id=curso_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset

class GrupoCreateView(LoginRequiredMixin, CreateView):
    model = Grupo
    form_class = GrupoForm
    template_name = 'academicas/grupo_form.html'
    success_url = reverse_lazy('grupo_list')

class GrupoDetailView(LoginRequiredMixin, DetailView):
    model = Grupo
    template_name = 'academicas/grupo_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estudiantes'] = self.object.matricula_set.all().select_related('estudiante')
        return context

class GrupoUpdateView(LoginRequiredMixin, UpdateView):
    model = Grupo
    form_class = GrupoForm
    template_name = 'academicas/grupo_form.html'
    success_url = reverse_lazy('grupo_list')

class GrupoDeleteView(LoginRequiredMixin, DeleteView):
    model = Grupo
    template_name = 'academicas/grupo_confirm_delete.html'
    success_url = reverse_lazy('grupo_list')

# Periodos Académicos
class PeriodoAcademicoListView(LoginRequiredMixin, ListView):
    model = PeriodoAcademico
    template_name = 'academicas/periodo_list.html'
    context_object_name = 'periodos'

class PeriodoAcademicoCreateView(LoginRequiredMixin, CreateView):
    model = PeriodoAcademico
    form_class = PeriodoAcademicoForm
    template_name = 'academicas/periodo_form.html'
    success_url = reverse_lazy('periodo_list')

class PeriodoAcademicoUpdateView(LoginRequiredMixin, UpdateView):
    model = PeriodoAcademico
    form_class = PeriodoAcademicoForm
    template_name = 'academicas/periodo_form.html'
    success_url = reverse_lazy('periodo_list')

class PeriodoAcademicoDeleteView(LoginRequiredMixin, DeleteView):
    model = PeriodoAcademico
    template_name = 'academicas/periodo_confirm_delete.html'
    success_url = reverse_lazy('periodo_list')

# Matrículas
class MatriculaListView(LoginRequiredMixin, ListView):
    model = Matricula
    template_name = 'academicas/matricula_list.html'
    context_object_name = 'matriculas'
    
    def get_queryset(self):
        periodo_id = self.request.GET.get('periodo_id')
        grupo_id = self.request.GET.get('grupo_id')
        
        queryset = Matricula.objects.all()
        if periodo_id:
            queryset = queryset.filter(periodo_id=periodo_id)
        if grupo_id:
            queryset = queryset.filter(grupo_id=grupo_id)
        return queryset

class MatriculaCreateView(LoginRequiredMixin, CreateView):
    model = Matricula
    form_class = MatriculaForm
    template_name = 'academicas/matricula_form.html'
    
    def get_success_url(self):
        return reverse_lazy('matricula_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.creada_por = self.request.user
        return super().form_valid(form)

class MatriculaDetailView(LoginRequiredMixin, DetailView):
    model = Matricula
    template_name = 'academicas/matricula_detail.html'

class MatriculaUpdateView(LoginRequiredMixin, UpdateView):
    model = Matricula
    form_class = MatriculaForm
    template_name = 'academicas/matricula_form.html'
    
    def get_success_url(self):
        return reverse_lazy('matricula_detail', kwargs={'pk': self.object.pk})

class MatriculaDeleteView(LoginRequiredMixin, DeleteView):
    model = Matricula
    template_name = 'academicas/matricula_confirm_delete.html'
    success_url = reverse_lazy('matricula_list')

# Asistencias
class AsistenciaListView(LoginRequiredMixin, ListView):
    model = Asistencia
    template_name = 'academicas/asistencia_list.html'
    context_object_name = 'asistencias'
    
    def get_queryset(self):
        grupo_id = self.request.GET.get('grupo_id')
        fecha = self.request.GET.get('fecha')
        
        queryset = Asistencia.objects.all()
        if grupo_id:
            queryset = queryset.filter(grupo_id=grupo_id)
        if fecha:
            queryset = queryset.filter(fecha=fecha)
        return queryset

class AsistenciaCreateView(LoginRequiredMixin, CreateView):
    model = Asistencia
    form_class = AsistenciaForm
    template_name = 'academicas/asistencia_form.html'
    success_url = reverse_lazy('asistencia_list')
    
    def get_initial(self):
        return {
            'fecha': timezone.now().date(),
            'registrado_por': self.request.user
        }

class AsistenciaUpdateView(LoginRequiredMixin, UpdateView):
    model = Asistencia
    form_class = AsistenciaForm
    template_name = 'academicas/asistencia_form.html'
    success_url = reverse_lazy('asistencia_list')

class AsistenciaDeleteView(LoginRequiredMixin, DeleteView):
    model = Asistencia
    template_name = 'academicas/asistencia_confirm_delete.html'
    success_url = reverse_lazy('asistencia_list')

class AsistenciaMasivaCreateView(LoginRequiredMixin, FormView):
    template_name = 'academicas/asistencia_masiva_form.html'
    form_class = AsistenciaMasivaForm
    success_url = reverse_lazy('grupo_list')
    
    def form_valid(self, form):
        grupo = form.cleaned_data['grupo']
        fecha = form.cleaned_data['fecha']
        estudiantes = grupo.matricula_set.values_list('estudiante', flat=True)
        
        for estudiante_id in estudiantes:
            Asistencia.objects.create(
                estudiante_id=estudiante_id,
                grupo=grupo,
                fecha=fecha,
                estado='asistio',
                registrado_por=self.request.user
            )
        
        messages.success(self.request, f"Asistencia registrada para {len(estudiantes)} estudiantes")
        return super().form_valid(form)

# Calificaciones
class CalificacionListView(LoginRequiredMixin, ListView):
    model = Calificacion
    template_name = 'academicas/calificacion_list.html'
    context_object_name = 'calificaciones'
    
    def get_queryset(self):
        grupo_id = self.request.GET.get('grupo_id')
        periodo_id = self.request.GET.get('periodo_id')
        
        queryset = Calificacion.objects.all()
        if grupo_id:
            queryset = queryset.filter(grupo_id=grupo_id)
        if periodo_id:
            queryset = queryset.filter(periodo_id=periodo_id)
        return queryset

class CalificacionCreateView(LoginRequiredMixin, CreateView):
    model = Calificacion
    form_class = CalificacionForm
    template_name = 'academicas/calificacion_form.html'
    success_url = reverse_lazy('calificacion_list')

class CalificacionUpdateView(LoginRequiredMixin, UpdateView):
    model = Calificacion
    form_class = CalificacionForm
    template_name = 'academicas/calificacion_form.html'
    success_url = reverse_lazy('calificacion_list')

class CalificacionDeleteView(LoginRequiredMixin, DeleteView):
    model = Calificacion
    template_name = 'academicas/calificacion_confirm_delete.html'
    success_url = reverse_lazy('calificacion_list')

# Observaciones Académicas
class ObservacionAcademicaListView(LoginRequiredMixin, ListView):
    model = ObservacionAcademica
    template_name = 'academicas/observacion_list.html'
    context_object_name = 'observaciones'

class ObservacionAcademicaCreateView(LoginRequiredMixin, CreateView):
    model = ObservacionAcademica
    form_class = ObservacionAcademicaForm
    template_name = 'academicas/observacion_form.html'
    success_url = reverse_lazy('observacion_list')

class ObservacionAcademicaUpdateView(LoginRequiredMixin, UpdateView):
    model = ObservacionAcademica
    form_class = ObservacionAcademicaForm
    template_name = 'academicas/observacion_form.html'
    success_url = reverse_lazy('observacion_list')

class ObservacionAcademicaDeleteView(LoginRequiredMixin, DeleteView):
    model = ObservacionAcademica
    template_name = 'academicas/observacion_confirm_delete.html'
    success_url = reverse_lazy('observacion_list')

# ========================================================
# Módulo 4: Gestión Financiera
# ========================================================

# Conceptos de Cobro
class ConceptoCobroListView(LoginRequiredMixin, ListView):
    model = ConceptoCobro
    template_name = 'financieras/conceptocobro_list.html'
    context_object_name = 'conceptos'

class ConceptoCobroCreateView(LoginRequiredMixin, CreateView):
    model = ConceptoCobro
    form_class = ConceptoCobroForm
    template_name = 'financieras/conceptocobro_form.html'
    success_url = reverse_lazy('conceptocobro_list')

class ConceptoCobroUpdateView(LoginRequiredMixin, UpdateView):
    model = ConceptoCobro
    form_class = ConceptoCobroForm
    template_name = 'financieras/conceptocobro_form.html'
    success_url = reverse_lazy('conceptocobro_list')

class ConceptoCobroDeleteView(LoginRequiredMixin, DeleteView):
    model = ConceptoCobro
    template_name = 'financieras/conceptocobro_confirm_delete.html'
    success_url = reverse_lazy('conceptocobro_list')

# Facturas
class FacturaListView(LoginRequiredMixin, ListView):
    model = Factura
    template_name = 'financieras/factura_list.html'
    context_object_name = 'facturas'
    
    def get_queryset(self):
        estado = self.request.GET.get('estado')
        estudiante_id = self.request.GET.get('estudiante_id')
        
        queryset = Factura.objects.all()
        if estado:
            queryset = queryset.filter(estado=estado)
        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        return queryset

class FacturaCreateView(LoginRequiredMixin, CreateView):
    model = Factura
    form_class = FacturaForm
    template_name = 'financieras/factura_form.html'
    success_url = reverse_lazy('factura_list')
    
    def form_valid(self, form):
        form.instance.creada_por = self.request.user
        return super().form_valid(form)

class FacturaDetailView(LoginRequiredMixin, DetailView):
    model = Factura
    template_name = 'financieras/factura_detail.html'

class FacturaUpdateView(LoginRequiredMixin, UpdateView):
    model = Factura
    form_class = FacturaForm
    template_name = 'financieras/factura_form.html'
    success_url = reverse_lazy('factura_list')

class FacturaDeleteView(LoginRequiredMixin, DeleteView):
    model = Factura
    template_name = 'financieras/factura_confirm_delete.html'
    success_url = reverse_lazy('factura_list')

class FacturaPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        factura = get_object_or_404(Factura, pk=pk)
        
        # Crear respuesta PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="factura_{factura.consecutivo}.pdf"'
        
        # Crear PDF
        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter
        
        # Configuración
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, height - 100, f"FACTURA: {factura.consecutivo}")
        p.setFont("Helvetica", 12)
        p.drawString(100, height - 130, f"Estudiante: {factura.estudiante.nombre_completo}")
        p.drawString(100, height - 150, f"Fecha Emisión: {factura.fecha_emision}")
        p.drawString(100, height - 170, f"Fecha Vencimiento: {factura.fecha_vencimiento}")
        
        # Tabla de ítems
        p.drawString(100, height - 200, "Concepto")
        p.drawString(300, height - 200, "Valor")
        
        y = height - 220
        for item in factura.items.all():
            p.drawString(100, y, item.concepto.nombre)
            p.drawString(300, y, f"${item.valor_total:,.2f}")
            y -= 20
        
        # Totales
        p.drawString(100, y - 40, f"Subtotal: ${factura.subtotal:,.2f}")
        p.drawString(100, y - 60, f"Descuento: ${factura.descuento:,.2f}")
        p.drawString(100, y - 80, f"IVA: ${factura.iva:,.2f}")
        p.drawString(100, y - 100, f"TOTAL: ${factura.total:,.2f}")
        p.drawString(100, y - 120, f"Saldo: ${factura.saldo:,.2f}")
        
        p.showPage()
        p.save()
        return response

# Cobros
class CobroListView(LoginRequiredMixin, ListView):
    model = Cobro
    template_name = 'financieras/cobro_list.html'
    context_object_name = 'cobros'
    
    def get_queryset(self):
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        
        queryset = Cobro.objects.all()
        if fecha_inicio and fecha_fin:
            queryset = queryset.filter(fecha__range=[fecha_inicio, fecha_fin])
        return queryset

class CobroCreateView(LoginRequiredMixin, CreateView):
    model = Cobro
    form_class = CobroForm
    template_name = 'financieras/cobro_form.html'
    success_url = reverse_lazy('cobro_list')
    
    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        return super().form_valid(form)

class CobroDetailView(LoginRequiredMixin, DetailView):
    model = Cobro
    template_name = 'financieras/cobro_detail.html'

class CobroUpdateView(LoginRequiredMixin, UpdateView):
    model = Cobro
    form_class = CobroForm
    template_name = 'financieras/cobro_form.html'
    success_url = reverse_lazy('cobro_list')

class CobroDeleteView(LoginRequiredMixin, DeleteView):
    model = Cobro
    template_name = 'financieras/cobro_confirm_delete.html'
    success_url = reverse_lazy('cobro_list')

class CobroPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        cobro = get_object_or_404(Cobro, pk=pk)
        
        # Crear respuesta PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="recibo_{cobro.consecutivo}.pdf"'
        
        # Crear PDF
        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter
        
        # Configuración
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, height - 100, f"RECIBO DE COBRO: {cobro.consecutivo}")
        p.setFont("Helvetica", 12)
        p.drawString(100, height - 130, f"Factura: {cobro.factura.consecutivo}")
        p.drawString(100, height - 150, f"Estudiante: {cobro.factura.estudiante.nombre_completo}")
        p.drawString(100, height - 170, f"Fecha: {cobro.fecha}")
        
        # Totales
        p.drawString(100, height - 200, f"Valor Total: ${cobro.valor_total:,.2f}")
        p.drawString(100, height - 220, f"Saldo: ${cobro.saldo:,.2f}")
        
        # Detalles de pago
        p.drawString(100, height - 250, "Detalles de Pagos:")
        y = height - 270
        for pago in cobro.pagos.all():
            p.drawString(120, y, f"{pago.get_metodo_pago_display()}: ${pago.valor:,.2f}")
            y -= 20
        
        p.showPage()
        p.save()
        return response

# Detalles de Pago
class DetallePagoCreateView(LoginRequiredMixin, CreateView):
    model = DetallePago
    form_class = DetallePagoForm
    template_name = 'financieras/detallepago_form.html'
    
    def get_success_url(self):
        return reverse_lazy('cobro_detail', kwargs={'pk': self.object.cobro.pk})
    
    def form_valid(self, form):
        form.instance.registrado_por = self.request.user
        return super().form_valid(form)

class DetallePagoUpdateView(LoginRequiredMixin, UpdateView):
    model = DetallePago
    form_class = DetallePagoForm
    template_name = 'financieras/detallepago_form.html'
    
    def get_success_url(self):
        return reverse_lazy('cobro_detail', kwargs={'pk': self.object.cobro.pk})

class DetallePagoDeleteView(LoginRequiredMixin, DeleteView):
    model = DetallePago
    template_name = 'financieras/detallepago_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('cobro_detail', kwargs={'pk': self.object.cobro.pk})

# Egresos
class EgresoListView(LoginRequiredMixin, ListView):
    model = Egreso
    template_name = 'financieras/egreso_list.html'
    context_object_name = 'egresos'
    
    def get_queryset(self):
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        tipo = self.request.GET.get('tipo')
        
        queryset = Egreso.objects.all()
        if fecha_inicio and fecha_fin:
            queryset = queryset.filter(fecha__range=[fecha_inicio, fecha_fin])
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        return queryset

class EgresoCreateView(LoginRequiredMixin, CreateView):
    model = Egreso
    form_class = EgresoForm
    template_name = 'financieras/egreso_form.html'
    success_url = reverse_lazy('egreso_list')
    
    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        form.instance.aprobado_por = self.request.user
        return super().form_valid(form)

class EgresoDetailView(LoginRequiredMixin, DetailView):
    model = Egreso
    template_name = 'financieras/egreso_detail.html'

class EgresoUpdateView(LoginRequiredMixin, UpdateView):
    model = Egreso
    form_class = EgresoForm
    template_name = 'financieras/egreso_form.html'
    success_url = reverse_lazy('egreso_list')

class EgresoDeleteView(LoginRequiredMixin, DeleteView):
    model = Egreso
    template_name = 'financieras/egreso_confirm_delete.html'
    success_url = reverse_lazy('egreso_list')

class EgresoPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        egreso = get_object_or_404(Egreso, pk=pk)
        
        # Crear respuesta PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="egreso_{egreso.consecutivo}.pdf"'
        
        # Crear PDF
        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter
        
        # Configuración
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, height - 100, f"COMPROBANTE DE EGRESO: {egreso.consecutivo}")
        p.setFont("Helvetica", 12)
        p.drawString(100, height - 130, f"Concepto: {egreso.concepto}")
        p.drawString(100, height - 150, f"Beneficiario: {egreso.beneficiario}")
        p.drawString(100, height - 170, f"Fecha: {egreso.fecha}")
        p.drawString(100, height - 190, f"Valor Total: ${egreso.valor_total:,.2f}")
        
        # Detalles
        p.drawString(100, height - 220, "Detalles:")
        y = height - 240
        for detalle in egreso.detalles.all():
            p.drawString(120, y, f"{detalle.descripcion}: {detalle.cantidad} x ${detalle.valor_unitario:,.2f} = ${detalle.valor_total:,.2f}")
            y -= 20
        
        p.showPage()
        p.save()
        return response

# ========================================================
# Módulo 5: Gestión Institucional
# ========================================================

# Eventos
class EventoListView(LoginRequiredMixin, ListView):
    model = Evento
    template_name = 'institucionales/evento_list.html'
    context_object_name = 'eventos'
    
    def get_queryset(self):
        tipo = self.request.GET.get('tipo')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        
        queryset = Evento.objects.all()
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if fecha_inicio and fecha_fin:
            queryset = queryset.filter(fecha_inicio__date__range=[fecha_inicio, fecha_fin])
        return queryset

class EventoCreateView(LoginRequiredMixin, CreateView):
    model = Evento
    form_class = EventoForm
    template_name = 'institucionales/evento_form.html'
    success_url = reverse_lazy('evento_list')
    
    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        return super().form_valid(form)

class EventoDetailView(LoginRequiredMixin, DetailView):
    model = Evento
    template_name = 'institucionales/evento_detail.html'

class EventoUpdateView(LoginRequiredMixin, UpdateView):
    model = Evento
    form_class = EventoForm
    template_name = 'institucionales/evento_form.html'
    success_url = reverse_lazy('evento_list')

class EventoDeleteView(LoginRequiredMixin, DeleteView):
    model = Evento
    template_name = 'institucionales/evento_confirm_delete.html'
    success_url = reverse_lazy('evento_list')

class EventoCalendarView(LoginRequiredMixin, TemplateView):
    template_name = 'institucionales/evento_calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        eventos = Evento.objects.all()
        context['eventos_json'] = [
            {
                'title': e.titulo,
                'start': e.fecha_inicio.isoformat(),
                'end': e.fecha_fin.isoformat(),
                'url': reverse('evento_detail', args=[e.id])
            }
            for e in eventos
        ]
        return context

# Comunicados
class ComunicadoListView(LoginRequiredMixin, ListView):
    model = Comunicado
    template_name = 'institucionales/comunicado_list.html'
    context_object_name = 'comunicados'

class ComunicadoCreateView(LoginRequiredMixin, CreateView):
    model = Comunicado
    form_class = ComunicadoForm
    template_name = 'institucionales/comunicado_form.html'
    success_url = reverse_lazy('comunicado_list')
    
    def form_valid(self, form):
        form.instance.publicado_por = self.request.user
        return super().form_valid(form)

class ComunicadoDetailView(LoginRequiredMixin, DetailView):
    model = Comunicado
    template_name = 'institucionales/comunicado_detail.html'

class ComunicadoUpdateView(LoginRequiredMixin, UpdateView):
    model = Comunicado
    form_class = ComunicadoForm
    template_name = 'institucionales/comunicado_form.html'
    success_url = reverse_lazy('comunicado_list')

class ComunicadoDeleteView(LoginRequiredMixin, DeleteView):
    model = Comunicado
    template_name = 'institucionales/comunicado_confirm_delete.html'
    success_url = reverse_lazy('comunicado_list')

# Documentos Institucionales
class DocumentoInstitucionalListView(LoginRequiredMixin, ListView):
    model = DocumentoInstitucional
    template_name = 'institucionales/documentoinstitucional_list.html'
    context_object_name = 'documentos'

class DocumentoInstitucionalCreateView(LoginRequiredMixin, CreateView):
    model = DocumentoInstitucional
    form_class = DocumentoInstitucionalForm
    template_name = 'institucionales/documentoinstitucional_form.html'
    success_url = reverse_lazy('documentoinstitucional_list')
    
    def form_valid(self, form):
        form.instance.publicado_por = self.request.user
        return super().form_valid(form)

class DocumentoInstitucionalDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        documento = get_object_or_404(DocumentoInstitucional, pk=pk)
        file_path = documento.archivo.path
        return FileResponse(open(file_path, 'rb'), as_attachment=True)

class DocumentoInstitucionalDeleteView(LoginRequiredMixin, DeleteView):
    model = DocumentoInstitucional
    template_name = 'institucionales/documentoinstitucional_confirm_delete.html'
    success_url = reverse_lazy('documentoinstitucional_list')

# ========================================================
# Módulo 6: Soporte y Documentos
# ========================================================

# Documentos de Estudiantes
class DocumentoEstudianteListView(LoginRequiredMixin, ListView):
    model = DocumentoEstudiante
    template_name = 'soporte/documentoestudiante_list.html'
    context_object_name = 'documentos'
    
    def get_queryset(self):
        estudiante_id = self.request.GET.get('estudiante_id')
        tipo = self.request.GET.get('tipo')
        
        queryset = DocumentoEstudiante.objects.all()
        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        return queryset

class DocumentoEstudianteCreateView(LoginRequiredMixin, CreateView):
    model = DocumentoEstudiante
    form_class = DocumentoEstudianteForm
    template_name = 'soporte/documentoestudiante_form.html'
    success_url = reverse_lazy('documentoestudiante_list')
    
    def form_valid(self, form):
        form.instance.subido_por = self.request.user
        return super().form_valid(form)

class DocumentoEstudianteDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        documento = get_object_or_404(DocumentoEstudiante, pk=pk)
        file_path = documento.archivo.path
        return FileResponse(open(file_path, 'rb'), as_attachment=True)

class DocumentoEstudianteDeleteView(LoginRequiredMixin, DeleteView):
    model = DocumentoEstudiante
    template_name = 'soporte/documentoestudiante_confirm_delete.html'
    success_url = reverse_lazy('documentoestudiante_list')

# Incidencias
class IncidenciaListView(LoginRequiredMixin, ListView):
    model = Incidencia
    template_name = 'soporte/incidencia_list.html'
    context_object_name = 'incidencias'
    
    def get_queryset(self):
        estado = self.request.GET.get('estado')
        tipo = self.request.GET.get('tipo')
        responsable = self.request.GET.get('responsable')
        
        queryset = Incidencia.objects.all()
        if estado:
            queryset = queryset.filter(estado=estado)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if responsable:
            queryset = queryset.filter(responsable_id=responsable)
        return queryset

class IncidenciaCreateView(LoginRequiredMixin, CreateView):
    model = Incidencia
    form_class = IncidenciaForm
    template_name = 'soporte/incidencia_form.html'
    success_url = reverse_lazy('incidencia_list')
    
    def form_valid(self, form):
        form.instance.reportado_por = self.request.user
        return super().form_valid(form)

class IncidenciaDetailView(LoginRequiredMixin, DetailView):
    model = Incidencia
    template_name = 'soporte/incidencia_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['seguimientos'] = self.object.seguimientos.all()
        return context

class IncidenciaUpdateView(LoginRequiredMixin, UpdateView):
    model = Incidencia
    form_class = IncidenciaForm
    template_name = 'soporte/incidencia_form.html'
    success_url = reverse_lazy('incidencia_list')

class IncidenciaDeleteView(LoginRequiredMixin, DeleteView):
    model = Incidencia
    template_name = 'soporte/incidencia_confirm_delete.html'
    success_url = reverse_lazy('incidencia_list')

class IncidenciaCerrarView(LoginRequiredMixin, View):
    def post(self, request, pk):
        incidencia = get_object_or_404(Incidencia, pk=pk)
        incidencia.estado = 'cerrada'
        incidencia.fecha_cierre = timezone.now()
        incidencia.save()
        messages.success(request, "Incidencia marcada como cerrada")
        return redirect('incidencia_detail', pk=pk)

# Seguimiento de Incidencias
class SeguimientoIncidenciaCreateView(LoginRequiredMixin, CreateView):
    model = SeguimientoIncidencia
    form_class = SeguimientoIncidenciaForm
    template_name = 'soporte/seguimiento_form.html'
    
    def form_valid(self, form):
        form.instance.incidencia = get_object_or_404(Incidencia, pk=self.kwargs['pk'])
        form.instance.usuario = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('incidencia_detail', kwargs={'pk': self.kwargs['pk']})

class SeguimientoIncidenciaDeleteView(LoginRequiredMixin, DeleteView):
    model = SeguimientoIncidencia
    template_name = 'soporte/seguimiento_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('incidencia_detail', kwargs={'pk': self.object.incidencia.pk})

# ========================================================
# Módulo 7: Reportes Económicos
# ========================================================

class ReporteEconomicoListView(LoginRequiredMixin, ListView):
    model = ReporteEconomico
    template_name = 'reportes/reporte_list.html'
    context_object_name = 'reportes'

class ReporteEconomicoCreateView(LoginRequiredMixin, CreateView):
    model = ReporteEconomico
    form_class = ReporteEconomicoForm
    template_name = 'reportes/reporte_form.html'
    success_url = reverse_lazy('reporte_list')
    
    def form_valid(self, form):
        form.instance.generado_por = self.request.user
        return super().form_valid(form)

class ReporteEconomicoDetailView(LoginRequiredMixin, DetailView):
    model = ReporteEconomico
    template_name = 'reportes/reporte_detail.html'

class ReporteEconomicoDeleteView(LoginRequiredMixin, DeleteView):
    model = ReporteEconomico
    template_name = 'reportes/reporte_confirm_delete.html'
    success_url = reverse_lazy('reporte_list')

class ReporteEconomicoPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        reporte = get_object_or_404(ReporteEconomico, pk=pk)
        
        # Crear respuesta PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_{reporte.nombre}.pdf"'
        
        # Crear PDF
        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter
        
        # Encabezado
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, height - 50, f"Reporte Económico: {reporte.nombre}")
        p.setFont("Helvetica", 12)
        p.drawString(100, height - 80, f"Período: {reporte.fecha_inicio} a {reporte.fecha_fin}")
        p.drawString(100, height - 100, f"Generado por: {reporte.generado_por.get_full_name()}")
        p.drawString(100, height - 120, f"Fecha generación: {reporte.fecha_generacion}")
        
        # Obtener datos
        cobros = Cobro.objects.filter(fecha__range=[reporte.fecha_inicio, reporte.fecha_fin])
        egresos = Egreso.objects.filter(fecha__range=[reporte.fecha_inicio, reporte.fecha_fin])
        
        # Resumen
        total_ingresos = cobros.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        total_egresos = egresos.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        balance = total_ingresos - total_egresos
        
        p.drawString(100, height - 160, "Resumen Financiero:")
        p.drawString(120, height - 180, f"Ingresos Totales: ${total_ingresos:,.2f}")
        p.drawString(120, height - 200, f"Egresos Totales: ${total_egresos:,.2f}")
        p.drawString(120, height - 220, f"Balance: ${balance:,.2f}")
        
        # Detalle ingresos por tipo
        p.drawString(100, height - 260, "Detalle de Ingresos:")
        y = height - 280
        for tipo, nombre in Cobro.TIPO_INGRESO_CHOICES:
            total_tipo = cobros.filter(tipo_ingreso=tipo).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
            if total_tipo > 0:
                p.drawString(120, y, f"{nombre}: ${total_tipo:,.2f}")
                y -= 20
        
        # Detalle egresos por categoría
        p.drawString(100, y - 40, "Detalle de Egresos:")
        y -= 60
        for categoria, nombre in Egreso.CATEGORIA_DETALLADA_CHOICES:
            total_categoria = egresos.filter(categoria_detallada=categoria).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
            if total_categoria > 0:
                p.drawString(120, y, f"{nombre}: ${total_categoria:,.2f}")
                y -= 20
        
        p.showPage()
        p.save()
        return response

class ReporteEconomicoExcelView(LoginRequiredMixin, View):
    def get(self, request, pk):
        reporte = get_object_or_404(ReporteEconomico, pk=pk)
        
        # Crear libro de Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte Económico"
        
        # Encabezados
        ws.append(['Reporte Económico', reporte.nombre])
        ws.append(['Período', f"{reporte.fecha_inicio} a {reporte.fecha_fin}"])
        ws.append(['Generado por', reporte.generado_por.get_full_name()])
        ws.append(['Fecha generación', reporte.fecha_generacion.strftime("%Y-%m-%d %H:%M")])
        ws.append([])
        
        # Obtener datos
        cobros = Cobro.objects.filter(fecha__range=[reporte.fecha_inicio, reporte.fecha_fin])
        egresos = Egreso.objects.filter(fecha__range=[reporte.fecha_inicio, reporte.fecha_fin])
        
        # Resumen
        total_ingresos = cobros.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        total_egresos = egresos.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        balance = total_ingresos - total_egresos
        
        ws.append(['Resumen Financiero'])
        ws.append(['Ingresos Totales', total_ingresos])
        ws.append(['Egresos Totales', total_egresos])
        ws.append(['Balance', balance])
        ws.append([])
        
        # Detalle ingresos
        ws.append(['Detalle de Ingresos'])
        ws.append(['Tipo', 'Valor'])
        for tipo, nombre in Cobro.TIPO_INGRESO_CHOICES:
            total_tipo = cobros.filter(tipo_ingreso=tipo).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
            if total_tipo > 0:
                ws.append([nombre, total_tipo])
        
        ws.append([])
        
        # Detalle egresos
        ws.append(['Detalle de Egresos'])
        ws.append(['Categoría', 'Valor'])
        for categoria, nombre in Egreso.CATEGORIA_DETALLADA_CHOICES:
            total_categoria = egresos.filter(categoria_detallada=categoria).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
            if total_categoria > 0:
                ws.append([nombre, total_categoria])
        
        # Guardar respuesta
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="reporte_{reporte.nombre}.xlsx"'
        wb.save(response)
        return response

class ReporteProgramadoListView(LoginRequiredMixin, ListView):
    model = ReporteProgramado
    template_name = 'reportes/reporteprogramado_list.html'
    context_object_name = 'reportes_programados'

class ReporteProgramadoCreateView(LoginRequiredMixin, CreateView):
    model = ReporteProgramado
    form_class = ReporteProgramadoForm
    template_name = 'reportes/reporteprogramado_form.html'
    success_url = reverse_lazy('reporteprogramado_list')
    
    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        return super().form_valid(form)

class ReporteProgramadoUpdateView(LoginRequiredMixin, UpdateView):
    model = ReporteProgramado
    form_class = ReporteProgramadoForm
    template_name = 'reportes/reporteprogramado_form.html'
    success_url = reverse_lazy('reporteprogramado_list')

class ReporteProgramadoDeleteView(LoginRequiredMixin, DeleteView):
    model = ReporteProgramado
    template_name = 'reportes/reporteprogramado_confirm_delete.html'
    success_url = reverse_lazy('reporteprogramado_list')

# ========================================================
# Módulo 8: Configuración y Auditoría
# ========================================================

class ConfiguracionInstitutoUpdateView(LoginRequiredMixin, UpdateView):
    model = ConfiguracionInstituto
    form_class = ConfiguracionInstitutoForm
    template_name = 'configuracion/configuracion_form.html'
    success_url = reverse_lazy('dashboard')
    
    def get_object(self):
        return ConfiguracionInstituto.objects.first()

class ConsecutivoListView(LoginRequiredMixin, ListView):
    model = Consecutivo
    template_name = 'configuracion/consecutivo_list.html'
    context_object_name = 'consecutivos'

class ConsecutivoUpdateView(LoginRequiredMixin, UpdateView):
    model = Consecutivo
    form_class = ConsecutivoForm
    template_name = 'configuracion/consecutivo_form.html'
    success_url = reverse_lazy('consecutivo_list')

class AuditoriaListView(LoginRequiredMixin, ListView):
    model = Auditoria
    template_name = 'auditoria/auditoria_list.html'
    context_object_name = 'registros_auditoria'
    paginate_by = 50

class AuditoriaDetailView(LoginRequiredMixin, DetailView):
    model = Auditoria
    template_name = 'auditoria/auditoria_detail.html'

class BackupListView(LoginRequiredMixin, ListView):
    model = Backup
    template_name = 'backup/backup_list.html'
    context_object_name = 'backups'

class BackupCreateView(LoginRequiredMixin, View):
    def post(self, request):
        # Lógica para crear backup
        # ...
        messages.success(request, "Copia de seguridad creada exitosamente")
        return redirect('backup_list')

class BackupDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        backup = get_object_or_404(Backup, pk=pk)
        return FileResponse(open(backup.archivo.path, 'rb'), as_attachment=True)

class BackupDeleteView(LoginRequiredMixin, DeleteView):
    model = Backup
    template_name = 'backup/backup_confirm_delete.html'
    success_url = reverse_lazy('backup_list')

# ========================================================
# Módulo 9: Vistas Adicionales
# ========================================================

class ExportarEstudiantesExcelView(LoginRequiredMixin, View):
    def get(self, request):
        # Crear libro de Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Estudiantes"
        
        # Encabezados
        headers = [
            'ID', 'Identificación', 'Nombres', 'Apellidos', 'Fecha Nacimiento', 'Edad',
            'Estado', 'Programa', 'Grupo', 'Dirección', 'Teléfono', 'Correo'
        ]
        ws.append(headers)
        
        # Datos
        estudiantes = Estudiante.objects.all().select_related('programa_actual', 'grupo_actual')
        for e in estudiantes:
            ws.append([
                e.id,
                e.identificacion,
                f"{e.primer_nombre} {e.segundo_nombre or ''}",
                f"{e.primer_apellido} {e.segundo_apellido or ''}",
                e.fecha_nacimiento,
                e.edad,
                e.get_estado_display(),
                e.programa_actual.nombre if e.programa_actual else '',
                e.grupo_actual.codigo if e.grupo_actual else '',
                e.direccion,
                e.telefono_principal,
                e.correo
            ])
        
        # Guardar respuesta
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="estudiantes.xlsx"'
        wb.save(response)
        return response

class ImportarEstudiantesView(LoginRequiredMixin, FormView):
    template_name = 'importar/estudiantes_form.html'
    form_class = ImportarEstudiantesForm
    success_url = reverse_lazy('estudiante_list')
    
    def form_valid(self, form):
        archivo = form.cleaned_data['archivo']
        # Lógica para procesar el archivo e importar estudiantes
        # ...
        messages.success(self.request, "Estudiantes importados exitosamente")
        return super().form_valid(form)

class GenerarFacturasMasivasView(LoginRequiredMixin, View):
    def post(self, request):
        periodo_id = request.POST.get('periodo_id')
        concepto_id = request.POST.get('concepto_id')
        
        periodo = get_object_or_404(PeriodoAcademico, pk=periodo_id)
        concepto = get_object_or_404(ConceptoCobro, pk=concepto_id)
        
        # Lógica para generar facturas masivas
        # ...
        messages.success(request, "Facturas generadas exitosamente")
        return redirect('factura_list')

class DashboardFinancieroView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/financiero.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Resumen mensual
        hoy = timezone.now()
        primer_dia_mes = hoy.replace(day=1)
        ultimo_dia_mes = hoy.replace(day=28) + timezone.timedelta(days=4)
        ultimo_dia_mes = ultimo_dia_mes - timezone.timedelta(days=ultimo_dia_mes.day)
        
        ingresos = Cobro.objects.filter(
            fecha__range=[primer_dia_mes, ultimo_dia_mes]
        ).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        
        egresos = Egreso.objects.filter(
            fecha__range=[primer_dia_mes, ultimo_dia_mes]
        ).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        
        balance = ingresos - egresos
        
        context['ingresos_mes'] = ingresos
        context['egresos_mes'] = egresos
        context['balance_mes'] = balance
        
        # Últimos cobros
        context['ultimos_cobros'] = Cobro.objects.order_by('-fecha')[:5]
        
        # Últimos egresos
        context['ultimos_egresos'] = Egreso.objects.order_by('-fecha')[:5]
        
        # Facturas pendientes
        context['facturas_pendientes'] = Factura.objects.filter(
            estado='pendiente'
        ).order_by('fecha_vencimiento')[:10]
        
        return context

