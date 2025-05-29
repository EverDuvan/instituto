from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('perfil/', views.PerfilUsuarioView.as_view(), name='perfil'),
    path('cambiar-password/', views.CambiarPasswordView.as_view(), name='cambiar_password'),
    
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/financiero/', views.DashboardFinancieroView.as_view(), name='dashboard_financiero'),
    
    # Personas
    path('estudiantes/', views.EstudianteListView.as_view(), name='estudiante_list'),
    path('estudiantes/nuevo/', views.EstudianteCreateView.as_view(), name='estudiante_create'),
    path('estudiantes/<int:pk>/', views.EstudianteDetailView.as_view(), name='estudiante_detail'),
    path('estudiantes/<int:pk>/editar/', views.EstudianteUpdateView.as_view(), name='estudiante_update'),
    path('estudiantes/<int:pk>/eliminar/', views.EstudianteDeleteView.as_view(), name='estudiante_delete'),
    
    # ... (patrones similares para docentes, acudientes, etc.)
    
    # Financiero
    path('facturas/', views.FacturaListView.as_view(), name='factura_list'),
    path('facturas/nueva/', views.FacturaCreateView.as_view(), name='factura_create'),
    path('facturas/<int:pk>/', views.FacturaDetailView.as_view(), name='factura_detail'),
    path('facturas/<int:pk>/editar/', views.FacturaUpdateView.as_view(), name='factura_update'),
    path('facturas/<int:pk>/eliminar/', views.FacturaDeleteView.as_view(), name='factura_delete'),
    path('facturas/<int:pk>/pdf/', views.FacturaPDFView.as_view(), name='factura_pdf'),
    
    # ... (patrones similares para cobros, egresos, etc.)
    
    # Reportes
    path('reportes/economicos/', views.ReporteEconomicoListView.as_view(), name='reporte_list'),
    path('reportes/economicos/nuevo/', views.ReporteEconomicoCreateView.as_view(), name='reporte_create'),
    path('reportes/economicos/<int:pk>/', views.ReporteEconomicoDetailView.as_view(), name='reporte_detail'),
    path('reportes/economicos/<int:pk>/eliminar/', views.ReporteEconomicoDeleteView.as_view(), name='reporte_delete'),
    path('reportes/economicos/<int:pk>/pdf/', views.ReporteEconomicoPDFView.as_view(), name='reporte_pdf'),
    path('reportes/economicos/<int:pk>/excel/', views.ReporteEconomicoExcelView.as_view(), name='reporte_excel'),
    
    # ... (otros patrones de URL)
    
    # Utilerías
    path('exportar/estudiantes/excel/', views.ExportarEstudiantesExcelView.as_view(), name='exportar_estudiantes_excel'),
    path('importar/estudiantes/', views.ImportarEstudiantesView.as_view(), name='importar_estudiantes'),
    path('generar/facturas-masivas/', views.GenerarFacturasMasivasView.as_view(), name='generar_facturas_masivas'),
]
