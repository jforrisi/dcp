"""Generador de PDF para reportes de Licitaciones LRM."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


def crear_pdf_licitacion(datos: dict) -> BytesIO:
    """
    Crea un PDF con el informe de licitación LRM que replica el frontend.
    
    Args:
        datos: Dict con:
            - licitacion_data: datos completos de la licitación
            - bevsa_rate: tasa BEVSA del plazo
            - stats: estadísticas de últimas 5 licitaciones
            - curve_data: curva BEVSA del día
    
    Returns:
        BytesIO con el contenido del PDF
    """
    buffer = BytesIO()
    
    # Configuración del documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=30,
    )
    
    # Contenedor para el contenido
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    ))
    
    # Extraer datos
    licitacion = datos.get('licitacion_data', {})
    bevsa_rate = datos.get('bevsa_rate', {})
    stats = datos.get('stats', {})
    curve_data = datos.get('curve_data', {})
    
    fecha = licitacion.get('fecha', '')
    plazo = licitacion.get('plazo', '')
    
    # Formatear fecha
    try:
        if isinstance(fecha, str):
            fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
            fecha_fmt = fecha_dt.strftime('%d/%m/%Y')
        else:
            fecha_fmt = fecha.strftime('%d/%m/%Y') if hasattr(fecha, 'strftime') else str(fecha)
    except:
        fecha_fmt = str(fecha)
    
    # Título principal
    story.append(Paragraph("Informe de Licitación LRM", styles['CustomTitle']))
    story.append(Spacer(1, 0.1*inch))
    
    # ===== SECCIÓN 1: DATOS PRINCIPALES =====
    story.append(Paragraph(f"Licitación del {fecha_fmt}", styles['SectionTitle']))
    
    # Primera fila: 4 columnas
    monto_licitado = licitacion.get('monto_licitado')
    adjudicado = licitacion.get('adjudicado')
    tasa_corte = licitacion.get('tasa_corte')
    tasa_bevsa = bevsa_rate.get('ultimo_valor')
    
    data_row1 = [
        ['Monto Licitado', 'Adjudicado', f'Tasa Corte {plazo} días', f'Tasa BEVSA {plazo} días'],
        [
            formatear_numero_miles(monto_licitado),
            formatear_porcentaje(adjudicado * 100 if adjudicado else None),
            formatear_porcentaje(tasa_corte),
            formatear_porcentaje(tasa_bevsa)
        ]
    ]
    
    t1 = Table(data_row1, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#6b7280')),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 11),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#1f2937')),
        ('TOPPADDING', (0, 1), (-1, 1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
        
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    
    # Colorear la tasa de corte según diferencia con BEVSA
    if tasa_corte is not None and tasa_bevsa is not None:
        diferencia = abs(tasa_corte - tasa_bevsa)
        if diferencia <= 0.5:
            color_tasa = colors.HexColor('#059669')  # Verde
        elif diferencia <= 1.0:
            color_tasa = colors.HexColor('#d97706')  # Amarillo
        else:
            color_tasa = colors.HexColor('#dc2626')  # Rojo
        t1.setStyle(TableStyle([
            ('TEXTCOLOR', (2, 1), (3, 1), color_tasa),
        ]))
    
    story.append(t1)
    story.append(Spacer(1, 0.3*inch))
    
    # ===== SECCIÓN 2: ESTADÍSTICAS =====
    if stats:
        story.append(Paragraph(f"Estadísticas - Últimas 5 Licitaciones a {plazo} días", styles['SectionTitle']))
        
        # Resumen (3 columnas)
        stats_data = [
            ['Total Licitado', 'Total Adjudicado', '% Adjudicación Ponderado'],
            [
                formatear_numero_miles(stats.get('total_licitado')),
                formatear_numero_miles(stats.get('total_adjudicado')),
                formatear_porcentaje(stats.get('porcentaje_adjudicacion'))
            ]
        ]
        
        t3 = Table(stats_data, colWidths=[2*inch, 2*inch, 2*inch])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#6b7280')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            
            ('FONTNAME', (0, 1), (1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (1, 1), 11),
            ('TEXTCOLOR', (0, 1), (1, 1), colors.HexColor('#1f2937')),
            
            ('FONTNAME', (2, 1), (2, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (2, 1), (2, 1), 11),
            ('TEXTCOLOR', (2, 1), (2, 1), colors.HexColor('#6366f1')),
            
            ('TOPPADDING', (0, 1), (-1, 1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
            
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        
        story.append(t3)
        story.append(Spacer(1, 0.15*inch))
        
        # Tabla detallada
        if stats.get('licitaciones') and len(stats['licitaciones']) > 0:
            story.append(Paragraph("Detalle de licitaciones:", styles['Normal']))
            story.append(Spacer(1, 0.05*inch))
            
            detalle_data = [['Fecha', 'Licitado', '% Adj.', 'Adjudicado', 'Tasa Corte', 'Tasa BEVSA']]
            
            for lic in stats['licitaciones']:
                fecha_lic = lic.get('fecha', '')
                try:
                    if isinstance(fecha_lic, str):
                        fecha_lic_dt = datetime.strptime(fecha_lic, '%Y-%m-%d')
                        fecha_lic_fmt = fecha_lic_dt.strftime('%d/%m/%Y')
                    else:
                        fecha_lic_fmt = fecha_lic.strftime('%d/%m/%Y') if hasattr(fecha_lic, 'strftime') else str(fecha_lic)
                except:
                    fecha_lic_fmt = str(fecha_lic)
                
                # Formatear valores manejando None y NaN
                monto_lic = lic.get('monto_licitado')
                porc_adj = lic.get('porcentaje_adjudicacion')
                monto_adj = lic.get('monto_adjudicado')
                tasa_c = lic.get('tasa_corte')
                tasa_b = lic.get('tasa_bevsa')
                
                detalle_data.append([
                    fecha_lic_fmt,
                    formatear_numero_miles(monto_lic) if monto_lic is not None else '-',
                    formatear_porcentaje(porc_adj) if porc_adj is not None else '-',
                    formatear_numero_miles(monto_adj) if monto_adj is not None else '-',
                    formatear_porcentaje(tasa_c) if tasa_c is not None else '-',
                    formatear_porcentaje(tasa_b) if tasa_b is not None else '-'
                ])
            
            t4 = Table(detalle_data, colWidths=[0.9*inch, 1*inch, 0.7*inch, 1*inch, 0.9*inch, 0.9*inch])
            t4.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f9fafb')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#6b7280')),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ]))
            
            story.append(t4)
    
    story.append(Spacer(1, 0.3*inch))
    
    # ===== SECCIÓN 3: GRÁFICO DE CURVA BEVSA =====
    if curve_data and curve_data.get('data'):
        fecha_curva = curve_data.get('fecha', '')
        try:
            if isinstance(fecha_curva, str):
                fecha_curva_dt = datetime.strptime(fecha_curva, '%Y-%m-%d')
                fecha_curva_fmt = fecha_curva_dt.strftime('%d/%m/%Y')
            else:
                fecha_curva_fmt = fecha_curva.strftime('%d/%m/%Y') if hasattr(fecha_curva, 'strftime') else str(fecha_curva)
        except:
            fecha_curva_fmt = str(fecha_curva)
        
        story.append(PageBreak())
        story.append(Paragraph(f"Curva BEVSA Nominal - {fecha_curva_fmt}", styles['SectionTitle']))
        
        # Generar gráfico de curva
        curve_items = [item for item in curve_data['data'] if item.get('valor') is not None]
        if curve_items:
            labels = [item.get('nombre', '') for item in curve_items]
            valores = [float(item.get('valor')) for item in curve_items]
            
            fig = Figure(figsize=(7, 4))
            ax = fig.add_subplot(111)
            ax.plot(labels, valores, marker='o', linewidth=2, markersize=5, color='#6366f1')
            ax.set_xlabel('Plazo', fontsize=10)
            ax.set_ylabel('Tasa (%)', fontsize=10)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.tick_params(axis='x', rotation=45, labelsize=8)
            ax.tick_params(axis='y', labelsize=9)
            fig.tight_layout()
            
            # Guardar gráfico en buffer
            img_buffer = BytesIO()
            fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close(fig)
            
            # Agregar imagen al PDF
            img = RLImage(img_buffer, width=6.5*inch, height=3.5*inch)
            story.append(img)
    
    story.append(Spacer(1, 0.2*inch))
    
    # ===== SECCIÓN 4: GRÁFICO TEMPORAL (ÚLTIMOS 90 DÍAS) =====
    timeseries_data = datos.get('timeseries_data', [])
    if timeseries_data and len(timeseries_data) > 0:
        story.append(Paragraph(f"Comportamiento de Tasa BEVSA {plazo} días - Últimos 90 días", styles['SectionTitle']))
        
        # Extraer fechas y valores
        fechas = []
        valores_ts = []
        for item in timeseries_data:
            fecha_ts = item.get('fecha', '')
            valor_ts = item.get('valor')
            if fecha_ts and valor_ts is not None:
                try:
                    if isinstance(fecha_ts, str):
                        fecha_ts_dt = datetime.strptime(fecha_ts, '%Y-%m-%d')
                        fechas.append(fecha_ts_dt)
                    else:
                        fechas.append(fecha_ts)
                    valores_ts.append(float(valor_ts))
                except:
                    continue
        
        if fechas and valores_ts:
            fig = Figure(figsize=(7, 4))
            ax = fig.add_subplot(111)
            ax.plot(fechas, valores_ts, linewidth=2, color='#6366f1')
            ax.set_xlabel('Fecha', fontsize=10)
            ax.set_ylabel('Tasa (%)', fontsize=10)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.tick_params(axis='x', rotation=45, labelsize=8)
            ax.tick_params(axis='y', labelsize=9)
            
            # Formatear fechas en el eje x
            import matplotlib.dates as mdates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            
            fig.tight_layout()
            
            # Guardar gráfico en buffer
            img_buffer_ts = BytesIO()
            fig.savefig(img_buffer_ts, format='png', dpi=150, bbox_inches='tight')
            img_buffer_ts.seek(0)
            plt.close(fig)
            
            # Agregar imagen al PDF
            img_ts = RLImage(img_buffer_ts, width=6.5*inch, height=3.5*inch)
            story.append(img_ts)
    
    # Pie de página
    story.append(Spacer(1, 0.4*inch))
    fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
    story.append(Paragraph(
        f"<i>Informe generado el {fecha_generacion}</i>",
        styles['Normal']
    ))
    
    # Construir PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer


def formatear_numero_miles(valor):
    """Formatea un número con separadores de miles."""
    if valor is None:
        return 'N/A'
    try:
        # Formato uruguayo: punto para miles, coma para decimales
        return f"{float(valor):,.0f}".replace(',', '.')
    except:
        return 'N/A'


def formatear_porcentaje(valor):
    """Formatea un valor como porcentaje."""
    if valor is None:
        return 'N/A'
    try:
        return f"{float(valor):.2f}%"
    except:
        return 'N/A'
