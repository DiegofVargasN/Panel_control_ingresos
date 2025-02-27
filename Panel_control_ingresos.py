import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import datetime
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import json

# 🔹 Activar modo wide
st.set_page_config(layout="wide")

# 🔹 Agregar título
#st.title("💰Panel de control de Ingresos - Internet y Combazos")

# 🔹 Configurar las credenciales desde Streamlit Secrets
credentials_data = st.secrets["google"]["credentials"]
credentials_dict = json.loads(credentials_data)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# 🔹 Autenticación con Google Sheets
creds = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(creds)

# 🔹 Abrir la hoja de cálculo
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1144jZxmPrd9Vt_zTB5ZY4KljHEZ3eFlmJlpPP5uN85g"
spreadsheet = client.open_by_url(spreadsheet_url)

# 🔹 Barra lateral con opciones de navegación
st.sidebar.title("Menú de Navegación")
option = st.sidebar.selectbox("Selecciona una opción:", ["INICIO", "POSTPAGO", "PREPAGO"])

# 🔹 Función para obtener datos de una hoja específica
def get_sheet_data(sheet_index):
    sheet = spreadsheet.get_worksheet(sheet_index)  # Obtener la hoja por índice
    data = sheet.get_all_records()  # Obtener datos
    return pd.DataFrame(data)  # Convertir a DataFrame

# 🔹 Mostrar contenido según la opción seleccionada
if option == "INICIO":
    st.title("📊 Bienvenido al Panel de Control")
    st.write("Selecciona una opción en el menú lateral para ver los datos.")

elif option == "POSTPAGO":
    st.title("💰 Panel de Control - POSTPAGO")
    df = get_sheet_data(0)  # Primera hoja (Postpago)

    # 🔹 Convertir "FECHA DE REVISION" a formato de fecha
    df["FECHA DE REVISION"] = pd.to_datetime(df["FECHA DE REVISION"], errors="coerce")
    
    # 🔹 Obtener la fecha más reciente
    fecha_maxima = df["FECHA DE REVISION"].max()
    
    # 🔹 Mostrar la fecha máxima en st.info() debajo del título
    if pd.notna(fecha_maxima):
        st.info(f"📅 Reporte actualizado al: **{fecha_maxima.strftime('%d-%m-%Y')}**")
    else:
        st.warning("⚠️ No se encontraron fechas válidas en la columna 'FECHA DE REVISION'.")
    
    # 🔹 Filtros en el lienzo principal (usando st.expander)
    with st.expander("🧩 Mostrar/Ocultar Filtros", expanded=False):  # expanded=False para que esté colapsado por defecto
        st.header("Filtros")
    
        # 1. Filtro por CONTRATO
        if 'CONTRATO' in df.columns:
            contratos = df['CONTRATO'].unique().tolist()
            selected_contratos = st.multiselect(
                'CONTRATO',
                options=contratos,
                default=None,
                help="Selecciona uno o varios contratos"
            )
            if selected_contratos:
                df = df[df['CONTRATO'].isin(selected_contratos)]
    
        # 2. Filtro por FECHA DE ENVIO DE INFORME (versión mejorada)
        if 'FECHA ENVIO' in df.columns:
            try:
                # Convertir a formato fecha y extraer únicas
                df['FECHA_TS'] = pd.to_datetime(df['FECHA ENVIO'])
                fechas_unicas = df['FECHA_TS'].dt.date.unique().tolist()
                fechas_ordenadas = sorted(fechas_unicas, reverse=True)
                
                selected_fechas = st.multiselect(
                    'FECHA ENVIO',
                    options=['Seleccionar todas'] + fechas_ordenadas,
                    default=['Seleccionar todas'],
                    format_func=lambda x: x.strftime('%d/%m/%Y') if isinstance(x, datetime.date) else x
                )
                
                if 'Seleccionar todas' not in selected_fechas:
                    df = df[df['FECHA_TS'].dt.date.isin(selected_fechas)]
            except Exception as e:
                st.error(f"Formato de fecha no reconocido: {str(e)}")
                st.write("Valores únicos en la columna:", df['FECHA ENVIO'].unique())
    
        # 3. Filtro por TIPO DE SERVICIO
        if 'TIPO DE SERVICIO' in df.columns:
            servicios = df['TIPO DE SERVICIO'].unique().tolist()
            selected_servicios = st.multiselect(
                'TIPO DE SERVICIO',
                options=servicios,
                default=None,
                help="Filtra por tipo de servicio"
            )
            if selected_servicios:
                df = df[df['TIPO DE SERVICIO'].isin(selected_servicios)]
    
        # 4. Filtro por ESTADO
        if 'ESTADO' in df.columns:
            estados = df['ESTADO'].unique().tolist()
            selected_estados = st.multiselect(
                'ESTADO',
                options=estados,
                default=None,
                help="Filtra por estado del caso"
            )
            if selected_estados:
                df = df[df['ESTADO'].isin(selected_estados)]
    
        # 5. Filtro por RESPONSABLE
        if 'RESPONSABLE' in df.columns:
            responsables = df['RESPONSABLE'].unique().tolist()
            selected_responsables = st.multiselect(
                'RESPONSABLE',
                options=responsables,
                default=None,
                help="Filtra por responsable asignado"
            )
            if selected_responsables:
                df = df[df['RESPONSABLE'].isin(selected_responsables)]
    
        # 6. Filtro por TIPO DE ERROR
        if 'TIPO DE ERROR' in df.columns:
            errores = df['TIPO DE ERROR'].unique().tolist()
            selected_errores = st.multiselect(
                'TIPO DE ERROR',
                options=errores,
                default=None,
                help="Filtra por tipo de error reportado"
            )
            if selected_errores:
                df = df[df['TIPO DE ERROR'].isin(selected_errores)]
    
    # 🔹 Cálculo de métricas principales
    total_contratos = df["CONTRATO"].count()
    monto_recuperado = df["MONTO RECUPERADO"].sum()
    monto_no_recuperado = df["MONTO NO RECUPERADO"].sum()
    promedio_periodos_no_facturados = df["PERIODOS NO FACTURADO"].mean()
    
    # 🔹 Lista de tarjetas con métricas personalizadas
    tarjetas = [
        {"titulo": "Contratos Reportados", "valor": total_contratos, "color": "#3b5465", "hover": "#99311a"},
        {"titulo": "Monto Recuperado", "valor": f"Bs {monto_recuperado:,.2f}", "color": "#274029", "hover": "#1f4a04"},
        {"titulo": "Monto No Recuperado", "valor": f"Bs {monto_no_recuperado:,.2f}", "color": "#11181d", "hover": "#3b0610"},
    ]
    
    # 🔹 Generar el CSS dinámico
    css_tarjetas = ""
    for i, tarjeta in enumerate(tarjetas):
        css_tarjetas += f"""
            .card-{i} {{
                background-color: {tarjeta['color']};
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 150px;
                width: 100%;
                padding: 20px;
                border-radius: 20px;
                box-shadow: 4px 4px 10px rgba(0, 0, 0, 0.2);
                transition: background-color 0.3s, transform 0.2s, box-shadow 0.3s;
            }}
            .card-{i}:hover {{
                background-color: {tarjeta['hover']};
                transform: scale(1.05);
                box-shadow: 6px 6px 15px rgba(0, 0, 0, 0.3);
            }}
        """
    
    # 🔹 Aplicar CSS en Streamlit
    st.markdown(f"""
        <style>
            .custom-card {{
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                width: 100%;
                height: 150px;
                padding: 20px;
                border-radius: 20px;
                border: 2px solid #ffffff;
            }}
            {css_tarjetas}
    
            /* Asegurarse de que todos los valores estén alineados de la misma forma */
            .custom-card p {{
                font-size: 34px;
                font-weight: bold;
                color: white;
                margin: 0;
                text-align: center;
            }}
            
            /* Estilo para centrar las nuevas métricas */
            .centered-metrics {{
                display: flex;
                justify-content: center;
                margin-top: 40px;
            }}
            .metric-box {{
                padding: 20px;
                margin: 10px;
                border-radius: 10px;
                background-color: #f0f2f6;
                box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.1);
                min-width: 250px;
                text-align: center;
            }}
        </style>
    """, unsafe_allow_html=True)
    
    # 🔹 Mostrar tarjetas principales en columnas
    num_columnas = len(tarjetas)
    columnas = st.columns(num_columnas)
    
    for i, tarjeta in enumerate(tarjetas):
        with columnas[i]:  
            metric_placeholder = st.empty()
            
            # Animación solo para Contratos Reportados
            if tarjeta["titulo"] == "Contratos Reportados":
                valor_final = tarjeta["valor"]
                for j in range(valor_final + 1):
                    metric_placeholder.markdown(
                        f"""
                        <div class="custom-card card-{i}">
                            <h3 style="color: white; margin-bottom: 10px; text-align: center;">{tarjeta['titulo']}</h3>
                            <p>{j}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                    time.sleep(0.01)
            else:
                metric_placeholder.markdown(
                    f"""
                    <div class="custom-card card-{i}">
                        <h3 style="color: white; margin-bottom: 10px; text-align: center;">{tarjeta['titulo']}</h3>
                        <p>{tarjeta['valor']}</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
    
    # 🔹 Nueva sección de métricas centradas
    st.markdown("""
    <style>
        .metric-spacer {
            margin-top: 0px !important;
        }
        [data-testid="stMetric"] {
            width: 80% !important;
            padding: 0 15px !important;
        }
        [data-testid="stMetricLabel"] {
            width: 100% !important;
            
            font-size: 14px !important;
            text-align: center !important;
            margin-bottom: 8px !important;
            display: block !important;
            padding: 0 !important;
        }
        [data-testid="stMetricValue"] {
            width: 100% !important;
            color: #FF5733 !important;
            font-size: 42px !important;
            text-align: center !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        [data-testid="column"] {
            align-items: center !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Calcular nuevas métricas
    try:
        # Casos Resueltos (cuenta de ESTADO = RESUELTO)
        casos_resueltos = df[df['ESTADO'] == 'RESUELTO'].shape[0]
    except KeyError:
        casos_resueltos = 0
    
    try:
        # Casos Pendientes (cuenta de ESTADO = PENDIENTE)
        casos_pendientes = df[df['ESTADO'] == 'PENDIENTE'].shape[0]
    except KeyError:
        casos_pendientes = 0
    
    try:
        promedio_dias_demora = df["DIAS DE DEMORA"].mean()
    except KeyError:
        promedio_dias_demora = 0
    
    # Espaciado superior y contenedor centrado
    st.markdown("<div class='metric-spacer'></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([0.1, 3, 0.1])
    
    with center_col:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="CASOS RESUELTOS",
                value=casos_resueltos
            )
        
        with col2:
            st.metric(
                label="CASOS PENDIENTES",
                value=casos_pendientes
            )
        
        with col3:
            st.metric(
                label="PROMEDIO DE RESPUESTA DE OBSERVACIONES",
                value=f"{promedio_dias_demora:.2f} días"  # Formato con 2 decimales
            )
    
    
    
    
    st.markdown(
        '<p style="background-color:#001a2c; color:whithe; padding:10px; border-radius:5px;">'
        '📊 <b>Area de graficos</b>'
        '</p>',
        unsafe_allow_html=True
    )
    # 🔹 Sección NO FACTURADO MENSUAL OBSERVADO
    #st.header("📊 Observacion Mensual no facturado")
    
    # 🔹 Filtros en el lienzo principal (usando st.expander)
    with st.expander("🧩 Monto no recuperado filtrado por fecha del envio de la observacion", expanded=False):  # expanded=False para que esté colapsado por defecto
        #st.header("Filtros")
    
        # Selector de tipo de gráfico
        tipo_grafico = st.radio("Selecciona el tipo de gráfico:", ["Línea", "Barras"], horizontal=True)
    
        if 'TARIFA PLAN' in df.columns and 'FECHA_TS' in df.columns:
            # Convertir a tipo numérico y limpiar datos
            df['TARIFA PLAN'] = pd.to_numeric(df['TARIFA PLAN'], errors='coerce')
            df['FECHA_TS'] = pd.to_datetime(df['FECHA_TS'], errors='coerce')
            df_valid = df.dropna(subset=['TARIFA PLAN', 'FECHA_TS'])
            
            if not df_valid.empty:
                # Agrupar y sumar por fecha
                df_sum = df_valid.groupby('FECHA_TS', as_index=False)['TARIFA PLAN'].sum()
                
                # Crear gráfico
                fig = go.Figure()
                
                if tipo_grafico == "Línea":
                    # Línea principal
                    fig.add_trace(go.Scatter(
                        x=df_sum['FECHA_TS'], 
                        y=df_sum['TARIFA PLAN'], 
                        mode='lines+markers',
                        name='Suma Tarifa Plan',
                        line=dict(color='#04514f', width=6),
                        marker=dict(size=8, color='darkblue', line=dict(width=1, color='white'))
                    ))
    
                    # Línea de tendencia (Media móvil de 7 días)
                    df_sum['Tendencia'] = df_sum['TARIFA PLAN'].rolling(window=7, min_periods=1).mean()
                    fig.add_trace(go.Scatter(
                        x=df_sum['FECHA_TS'], 
                        y=df_sum['Tendencia'], 
                        mode='lines',
                        name='Tendencia (Media 7 días)',
                        line=dict(color='red', dash='dot', width=2)
                    ))
                
                else:
                    # Agregar un selector de color
                    color_barras = st.color_picker("Elige el color de las barras", "#04514f")
    
                    fig.add_trace(go.Bar(
                        x=df_sum['FECHA_TS'], 
                        y=df_sum['TARIFA PLAN'], 
                        name='Suma Tarifa Plan',
                        marker=dict(color=color_barras)  # Aplica el color elegido
                    ))
    
    
                # Configuración del diseño
                fig.update_layout(
                    title='📊 Monto no recuperado por Fecha de Envío',
                    xaxis_title='Fecha de Envío',
                    yaxis_title='Suma Acumulada (Bs)',
                    template='plotly_white',
                    hovermode='x unified',
                    xaxis=dict(showgrid=True, gridcolor='lightgray', tickangle=-45),
                    yaxis=dict(showgrid=True, gridcolor='lightgray'),
                    legend=dict(title='Indicadores', x=0.01, y=1.15, orientation='h')
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ No hay datos válidos para mostrar el gráfico.")
        elif 'TARIFA PLAN' not in df.columns:
            st.warning("⚠️ La columna 'TARIFA PLAN' no existe en el dataset.")
        else:
            st.warning("⚠️ Problema con las fechas: verifique la columna 'FECHA_TS'.")
    
    # 🔹 Filtros en el lienzo principal (usando st.expander)
    with st.expander("🧩 Monto recuperado filtrado por fecha del envio de la observacion ", expanded=False):  # expanded=False para que esté colapsado por defecto
        #st.header("Filtros")
    
        # Selector de tipo de gráfico
        tipo_grafico = st.radio("Selecciona el tipo de gráfico:", ["Línea", "Barras"], horizontal=True,key="boton1")
    
        if 'MONTO RECUPERADO' in df.columns and 'FECHA ENVIO' in df.columns:
            # Convertir a tipo numérico y limpiar datos
            df['MONTO RECUPERADO'] = pd.to_numeric(df['MONTO RECUPERADO'], errors='coerce')
            df['FECHA ENVIO'] = pd.to_datetime(df['FECHA ENVIO'], errors='coerce')
            df_valid = df.dropna(subset=['MONTO RECUPERADO', 'FECHA ENVIO'])
            
            if not df_valid.empty:
                # Agrupar y sumar por fecha
                df_sum = df_valid.groupby('FECHA ENVIO', as_index=False)['MONTO RECUPERADO'].sum()
                
                # Crear gráfico
                fig = go.Figure()
                
                if tipo_grafico == "Línea":
                    # Línea principal
                    fig.add_trace(go.Scatter(
                        x=df_sum['FECHA ENVIO'], 
                        y=df_sum['MONTO RECUPERADO'], 
                        mode='lines+markers',
                        name='Suma Monto Recuperado',
                        line=dict(color='#04514f', width=6),
                        marker=dict(size=8, color='darkblue', line=dict(width=1, color='white'))
                    ))
    
                    # Línea de tendencia (Media móvil de 7 días)
                    df_sum['Tendencia'] = df_sum['MONTO RECUPERADO'].rolling(window=7, min_periods=1).mean()
                    fig.add_trace(go.Scatter(
                        x=df_sum['FECHA ENVIO'], 
                        y=df_sum['Tendencia'], 
                        mode='lines',
                        name='Tendencia (Media 7 días)',
                        line=dict(color='red', dash='dot', width=2)
                    ))
                
                else:
                    # Agregar un selector de color
                    color_barras = st.color_picker("Elige el color de las barras", "#04514f",key="color1")
    
                    fig.add_trace(go.Bar(
                        x=df_sum['FECHA ENVIO'], 
                        y=df_sum['MONTO RECUPERADO'], 
                        name='Suma Monto Recuperado',
                        marker=dict(color=color_barras)  # Aplica el color elegido
                    ))
    
    
                # Configuración del diseño
                fig.update_layout(
                    title='📊 Evolución de Monto Recuperado por Fecha de Envío',
                    xaxis_title='Fecha de Envío',
                    yaxis_title='Monto Recuperado (Bs)',
                    template='plotly_white',
                    hovermode='x unified',
                    xaxis=dict(showgrid=True, gridcolor='lightgray', tickangle=-45),
                    yaxis=dict(showgrid=True, gridcolor='lightgray'),
                    legend=dict(title='Indicadores', x=0.01, y=1.15, orientation='h')
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ No hay datos válidos para mostrar el gráfico.")
        elif 'MONTO RECUPERADO' not in df.columns:
            st.warning("⚠️ La columna 'MONTO RECUPERADO' no existe en el dataset.")
        else:
            st.warning("⚠️ Problema con las fechas: verifique la columna 'FECHA ENVIO'.")
    
    st.markdown(
        '<p style="background-color:#001a2c; color:whithe; padding:10px; border-radius:5px;">'
        '📊 <b>Area de reporte</b>'
        '</p>',
        unsafe_allow_html=True
    )
    with st.expander("🧩 Descargar Reporte", expanded=False):  # expanded=False para que esté colapsado por defecto
    # 🔹 Título atractivo para la sección
        #st.title("🔄 Automatizar Reporte")
    
        # Agregar un toque visual con un subtítulo y estilo
        st.markdown("""
            <style>
            .reportview-container {
                background-color: #f4f6f9;
                font-family: 'Arial', sans-serif;
            }
            .sidebar .sidebar-content {
                background-color: #2E4053;
            }
            .css-1d391kg {
                color: #2D3436;
            }
            </style>
            """, unsafe_allow_html=True)
        st.subheader("Filtros de datos y opciones de descarga")
    
        # Mostrar el DataFrame filtrado con st.dataframe
        st.dataframe(df)
    
        # 🔹 Opción para descargar el archivo filtrado
    # 🔹 Opción para descargar el archivo filtrado automáticamente
    @st.cache_data
    def to_excel(df):
        """Convierte el DataFrame a un archivo Excel en formato bytes."""
        towrite = BytesIO()
        with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Datos Filtrados")
            writer._save()  # Guardar el archivo Excel
        return towrite.getvalue()
    
    # Convertir el DataFrame filtrado a Excel
    excel_file = to_excel(df)
    
    # Descargar automáticamente el archivo Excel
    st.download_button(
        label="📥 Descargar archivo Excel",
        data=excel_file,
        file_name="reporte_filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
elif option == "PREPAGO":
    st.title("💰 Panel de Control - PREPAGO")
    df = get_sheet_data(1)  # Segunda hoja (Prepago)

  

    
        # 🔹 Convertir "FECHA DE REVISION" a formato de fecha
    df["FECHA DE REVISION"] = pd.to_datetime(df["FECHA DE REVISION"], errors="coerce")

    # 🔹 Obtener la fecha más reciente
    fecha_maxima = df["FECHA DE REVISION"].max()

    # 🔹 Mostrar la fecha máxima en st.info() debajo del título
    if pd.notna(fecha_maxima):
        st.info(f"📅 Reporte actualizado al: **{fecha_maxima.strftime('%d-%m-%Y')}**")
    else:
        st.warning("⚠️ No se encontraron fechas válidas en la columna 'FECHA DE REVISION'.")


    # 🔹 Filtros en el lienzo principal (usando st.expander)
    with st.expander("🧩 Mostrar/Ocultar Filtros", expanded=False):  # expanded=False para que esté colapsado por defecto
        st.header("Filtros")

        # 1. Filtro por CONTRATO
        if 'CONTRATO' in df.columns:
            contratos = df['CONTRATO'].unique().tolist()
            selected_contratos = st.multiselect(
                'CONTRATO',
                options=contratos,
                default=None,
                help="Selecciona uno o varios contratos"
            )
            if selected_contratos:
                df = df[df['CONTRATO'].isin(selected_contratos)]

        # 2. Filtro por FECHA DE ENVIO DE INFORME (versión mejorada)
        if 'FECHA ENVIO' in df.columns:
            try:
                # Convertir a formato fecha con el formato correcto
                df['FECHA_TS'] = pd.to_datetime(df['FECHA ENVIO'], format='%d/%m/%Y', errors='coerce')
                
                # Verificar si hay valores nulos (fechas no convertidas)
                if df['FECHA_TS'].isnull().any():
                    st.warning("⚠️ Algunas fechas no pudieron ser convertidas. Verifica el formato de 'FECHA ENVIO'.")
                    st.write("Valores problemáticos:", df[df['FECHA_TS'].isnull()]['FECHA ENVIO'].unique())
                
                # Extraer fechas únicas
                fechas_unicas = df['FECHA_TS'].dt.date.unique().tolist()
                fechas_ordenadas = sorted(fechas_unicas, reverse=True)
                
                # Selector de fechas
                selected_fechas = st.multiselect(
                    'FECHA ENVIO',
                    options=['Seleccionar todas'] + fechas_ordenadas,
                    default=['Seleccionar todas'],
                    format_func=lambda x: x.strftime('%d/%m/%Y') if isinstance(x, datetime.date) else x
                )
                
                # Filtrar por fechas seleccionadas
                if 'Seleccionar todas' not in selected_fechas:
                    df = df[df['FECHA_TS'].dt.date.isin(selected_fechas)]
            except Exception as e:
                st.error(f"Error al procesar las fechas: {str(e)}")
                st.write("Valores únicos en la columna 'FECHA ENVIO':", df['FECHA ENVIO'].unique())
        else:
            st.error("⚠️ La columna 'FECHA ENVIO' no existe en el DataFrame.")
            st.write("Columnas disponibles:", df.columns.tolist())

        # 3. Filtro por TIPO DE SERVICIO
        if 'TIPO DE SERVICIO' in df.columns:
            servicios = df['TIPO DE SERVICIO'].unique().tolist()
            selected_servicios = st.multiselect(
                'TIPO DE SERVICIO',
                options=servicios,
                default=None,
                help="Filtra por tipo de servicio"
            )
            if selected_servicios:
                df = df[df['TIPO DE SERVICIO'].isin(selected_servicios)]

        # 4. Filtro por ESTADO
        if 'ESTADO' in df.columns:
            estados = df['ESTADO'].unique().tolist()
            selected_estados = st.multiselect(
                'ESTADO',
                options=estados,
                default=None,
                help="Filtra por estado del caso"
            )
            if selected_estados:
                df = df[df['ESTADO'].isin(selected_estados)]

        # 5. Filtro por RESPONSABLE
        if 'RESPONSABLE' in df.columns:
            responsables = df['RESPONSABLE'].unique().tolist()
            selected_responsables = st.multiselect(
                'RESPONSABLE',
                options=responsables,
                default=None,
                help="Filtra por responsable asignado"
            )
            if selected_responsables:
                df = df[df['RESPONSABLE'].isin(selected_responsables)]

        # 6. Filtro por TIPO DE ERROR
        if 'TIPO DE ERROR' in df.columns:
            errores = df['TIPO DE ERROR'].unique().tolist()
            selected_errores = st.multiselect(
                'TIPO DE ERROR',
                options=errores,
                default=None,
                help="Filtra por tipo de error reportado"
            )
            if selected_errores:
                df = df[df['TIPO DE ERROR'].isin(selected_errores)]

    # 🔹 Cálculo de métricas principales
    total_contratos = df["CONTRATO"].count()
    monto_recuperado = df.loc[df["PAGO DESPUES DE LA OBSERVACION"] == "SI", "TARIFA PLAN"].sum()
    monto_no_recuperado = df["MONTO NO FACTURADO"].sum()
    promedio_periodos_no_facturados = df["PERIODOS NO FACTURADO"].mean()

    # 🔹 Lista de tarjetas con métricas personalizadas
    tarjetas = [
        {"titulo": "Contratos Reportados", "valor": total_contratos, "color": "#3b5465", "hover": "#99311a"},
        {"titulo": "Monto Recuperado", "valor": f"Bs {monto_recuperado:,.2f}", "color": "#274029", "hover": "#1f4a04"},
        {"titulo": "Monto No Recuperado", "valor": f"Bs {monto_no_recuperado:,.2f}", "color": "#11181d", "hover": "#4e0923"},
    ]

    # 🔹 Generar el CSS dinámico
    css_tarjetas = ""
    for i, tarjeta in enumerate(tarjetas):
        css_tarjetas += f"""
            .card-{i} {{
                background-color: {tarjeta['color']};
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 150px;
                width: 100%;
                padding: 20px;
                border-radius: 20px;
                box-shadow: 4px 4px 10px rgba(0, 0, 0, 0.2);
                transition: background-color 0.3s, transform 0.2s, box-shadow 0.3s;
            }}
            .card-{i}:hover {{
                background-color: {tarjeta['hover']};
                transform: scale(1.05);
                box-shadow: 6px 6px 15px rgba(0, 0, 0, 0.3);
            }}
        """

    # 🔹 Aplicar CSS en Streamlit
    st.markdown(f"""
        <style>
            .custom-card {{
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                width: 100%;
                height: 150px;
                padding: 20px;
                border-radius: 20px;
                border: 4px solid #003049;
            }}
            {css_tarjetas}

            /* Asegurarse de que todos los valores estén alineados de la misma forma */
            .custom-card p {{
                font-size: 34px;
                font-weight: bold;
                color: white;
                margin: 0;
                text-align: center;
            }}
            
            /* Estilo para centrar las nuevas métricas */
            .centered-metrics {{
                display: flex;
                justify-content: center;
                margin-top: 40px;
            }}
            .metric-box {{
                padding: 20px;
                margin: 10px;
                border-radius: 10px;
                background-color: #f0f2f6;
                box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.1);
                min-width: 250px;
                text-align: center;
            }}
        </style>
    """, unsafe_allow_html=True)

    # 🔹 Mostrar tarjetas principales en columnas
    num_columnas = len(tarjetas)
    columnas = st.columns(num_columnas)

    for i, tarjeta in enumerate(tarjetas):
        with columnas[i]:  
            metric_placeholder = st.empty()
            
            # Animación solo para Contratos Reportados
            if tarjeta["titulo"] == "Contratos Reportados":
                valor_final = tarjeta["valor"]
                for j in range(valor_final + 1):
                    metric_placeholder.markdown(
                        f"""
                        <div class="custom-card card-{i}">
                            <h3 style="color: white; margin-bottom: 10px; text-align: center;">{tarjeta['titulo']}</h3>
                            <p>{j}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                    time.sleep(0.01)
            else:
                metric_placeholder.markdown(
                    f"""
                    <div class="custom-card card-{i}">
                        <h3 style="color: white; margin-bottom: 10px; text-align: center;">{tarjeta['titulo']}</h3>
                        <p>{tarjeta['valor']}</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

    # 🔹 Nueva sección de métricas centradas
    st.markdown("""
    <style>
        .metric-spacer {
            margin-top: 0px !important;
        }
        [data-testid="stMetric"] {
            width: 80% !important;
            padding: 0 15px !important;
        }
        [data-testid="stMetricLabel"] {
            width: 100% !important;
            
            font-size: 14px !important;
            text-align: center !important;
            margin-bottom: 8px !important;
            display: block !important;
            padding: 0 !important;
        }
        [data-testid="stMetricValue"] {
            width: 100% !important;
            color: #FF5733 !important;
            font-size: 42px !important;
            text-align: center !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        [data-testid="column"] {
            align-items: center !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Calcular nuevas métricas
    try:
        # Casos Resueltos (cuenta de ESTADO = RESUELTO)
        casos_resueltos = df[df['ESTADO'] == 'RESUELTO'].shape[0]
    except KeyError:
        casos_resueltos = 0

    try:
        # Casos Pendientes (cuenta de ESTADO = PENDIENTE)
        casos_pendientes = df[df['ESTADO'] == 'PENDIENTE'].shape[0]
    except KeyError:
        casos_pendientes = 0

    try:
        promedio_dias_demora = df["DIAS DE DEMORA"].mean()
    except KeyError:
        promedio_dias_demora = 0

    # Espaciado superior y contenedor centrado
    st.markdown("<div class='metric-spacer'></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([0.1, 3, 0.1])

    with center_col:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="CASOS RESUELTOS",
                value=casos_resueltos
            )
        
        with col2:
            st.metric(
                label="CASOS PENDIENTES",
                value=casos_pendientes
            )
        
        with col3:
            st.metric(
                label="PROMEDIO DE RESPUESTA DE OBSERVACIONES",
                value=f"{promedio_dias_demora:.2f} días"  # Formato con 2 decimales
            )



    st.markdown(
        '<p style="background-color:#00111c; color:whithe; padding:10px; border-radius:5px;">'
        '📊 <b>Area de graficos</b>'
        '</p>',
        unsafe_allow_html=True
    )

    # 🔹 Sección NO FACTURADO MENSUAL OBSERVADO
    #st.header("📊 Observacion Mensual no facturado")

    # 🔹 Filtros en el lienzo principal (usando st.expander)
    with st.expander("🧩 Monto no recuperado filtrado por fecha del envio de la observacion", expanded=False):  # expanded=False para que esté colapsado por defecto
        #st.header("Filtros")

        # Selector de tipo de gráfico
        tipo_grafico = st.radio("Selecciona el tipo de gráfico:", ["Línea", "Barras"], horizontal=True)

        if 'TARIFA PLAN' in df.columns and 'FECHA_TS' in df.columns:
            # Convertir a tipo numérico y limpiar datos
            df['TARIFA PLAN'] = pd.to_numeric(df['TARIFA PLAN'], errors='coerce')
            df['FECHA_TS'] = pd.to_datetime(df['FECHA_TS'], errors='coerce')
            df_valid = df.dropna(subset=['TARIFA PLAN', 'FECHA_TS'])
            
            if not df_valid.empty:
                # Agrupar y sumar por fecha
                df_sum = df_valid.groupby('FECHA_TS', as_index=False)['TARIFA PLAN'].sum()
                
                # Crear gráfico
                fig = go.Figure()
                
                if tipo_grafico == "Línea":
                    # Línea principal
                    fig.add_trace(go.Scatter(
                        x=df_sum['FECHA_TS'], 
                        y=df_sum['TARIFA PLAN'], 
                        mode='lines+markers',
                        name='Suma Tarifa Plan',
                        line=dict(color='#04514f', width=6),
                        marker=dict(size=8, color='darkblue', line=dict(width=1, color='white'))
                    ))

                    # Línea de tendencia (Media móvil de 7 días)
                    df_sum['Tendencia'] = df_sum['TARIFA PLAN'].rolling(window=7, min_periods=1).mean()
                    fig.add_trace(go.Scatter(
                        x=df_sum['FECHA_TS'], 
                        y=df_sum['Tendencia'], 
                        mode='lines',
                        name='Tendencia (Media 7 días)',
                        line=dict(color='red', dash='dot', width=2)
                    ))
                
                else:
                    # Agregar un selector de color
                    color_barras = st.color_picker("Elige el color de las barras", "#04514f")

                    fig.add_trace(go.Bar(
                        x=df_sum['FECHA_TS'], 
                        y=df_sum['TARIFA PLAN'], 
                        name='Suma Tarifa Plan',
                        marker=dict(color=color_barras)  # Aplica el color elegido
                    ))


                # Configuración del diseño
                fig.update_layout(
                    title='📊 Monto no recuperado por Fecha de Envío',
                    xaxis_title='Fecha de Envío',
                    yaxis_title='Suma Acumulada (Bs)',
                    template='plotly_white',
                    hovermode='x unified',
                    xaxis=dict(showgrid=True, gridcolor='lightgray', tickangle=-45),
                    yaxis=dict(showgrid=True, gridcolor='lightgray'),
                    legend=dict(title='Indicadores', x=0.01, y=1.15, orientation='h')
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ No hay datos válidos para mostrar el gráfico.")
        elif 'TARIFA PLAN' not in df.columns:
            st.warning("⚠️ La columna 'TARIFA PLAN' no existe en el dataset.")
        else:
            st.warning("⚠️ Problema con las fechas: verifique la columna 'FECHA_TS'.")

    # 🔹 Filtros en el lienzo principal (usando st.expander)
    with st.expander("🧩 Monto recuperado filtrado por fecha del envio de la observacion", expanded=False):  # expanded=False para que esté colapsado por defecto
        #st.header("Filtros")

        # Selector de tipo de gráfico
        tipo_grafico = st.radio("Selecciona el tipo de gráfico:", ["Línea", "Barras"], horizontal=True,key="boton1")

        # Calcular el monto recuperado
        df['MONTO RECUPERADO'] = df.loc[df["PAGO DESPUES DE LA OBSERVACION"] == "SI", "TARIFA PLAN"]

        # Verificar si las columnas necesarias existen
        if 'MONTO RECUPERADO' in df.columns and 'FECHA_TS' in df.columns:
            # Convertir a tipo numérico y limpiar datos
            df['MONTO RECUPERADO'] = pd.to_numeric(df['MONTO RECUPERADO'], errors='coerce')
            df['FECHA_TS'] = pd.to_datetime(df['FECHA_TS'], errors='coerce')
            df_valid = df.dropna(subset=['MONTO RECUPERADO', 'FECHA_TS'])
            
            if not df_valid.empty:
                # Agrupar y sumar por fecha
                df_sum = df_valid.groupby('FECHA_TS', as_index=False)['MONTO RECUPERADO'].sum()
                
                # Crear gráfico
                fig = go.Figure()
                
                if tipo_grafico == "Línea":
                    # Línea principal
                    fig.add_trace(go.Scatter(
                        x=df_sum['FECHA_TS'], 
                        y=df_sum['MONTO RECUPERADO'], 
                        mode='lines+markers',
                        name='Suma Monto Recuperado',
                        line=dict(color='#04514f', width=6),
                        marker=dict(size=8, color='darkblue', line=dict(width=1, color='white'))
                    ))

                    # Línea de tendencia (Media móvil de 7 días)
                    df_sum['Tendencia'] = df_sum['MONTO RECUPERADO'].rolling(window=7, min_periods=1).mean()
                    fig.add_trace(go.Scatter(
                        x=df_sum['FECHA_TS'], 
                        y=df_sum['Tendencia'], 
                        mode='lines',
                        name='Tendencia (Media 7 días)',
                        line=dict(color='red', dash='dot', width=2)
                    ))
                
                else:
                    # Agregar un selector de color
                    color_barras = st.color_picker("Elige el color de las barras", "#04514f", key="color1")

                    fig.add_trace(go.Bar(
                        x=df_sum['FECHA_TS'], 
                        y=df_sum['MONTO RECUPERADO'], 
                        name='Suma Monto Recuperado',
                        marker=dict(color=color_barras)  # Aplica el color elegido
                    ))

                # Configuración del diseño
                fig.update_layout(
                    title='📊 Monto Recuperado por Fecha de Envío',
                    xaxis_title='Fecha de Envío',
                    yaxis_title='Monto Recuperado (Bs)',
                    template='plotly_white',
                    hovermode='x unified',
                    xaxis=dict(showgrid=True, gridcolor='lightgray', tickangle=-45),
                    yaxis=dict(showgrid=True, gridcolor='lightgray'),
                    legend=dict(title='Indicadores', x=0.01, y=1.15, orientation='h')
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ No hay datos válidos para mostrar el gráfico.")
        elif 'MONTO RECUPERADO' not in df.columns:
            st.warning("⚠️ La columna 'MONTO RECUPERADO' no existe en el dataset.")
        else:
            st.warning("⚠️ Problema con las fechas: verifique la columna 'FECHA_TS'.")

        st.markdown(
            '<p style="background-color:#00111c; color:white; padding:10px; border-radius:5px;">'
            '📊 <b>Área de reporte</b>'
            '</p>',
            unsafe_allow_html=True
        )
    with st.expander("🧩 Descargar Reporte", expanded=False):  # expanded=False para que esté colapsado por defecto
    # 🔹 Título atractivo para la sección
        #st.title("🔄 Automatizar Reporte")

        # Agregar un toque visual con un subtítulo y estilo
        st.markdown("""
            <style>
            .reportview-container {
                background-color: #f4f6f9;
                font-family: 'Arial', sans-serif;
            }
            .sidebar .sidebar-content {
                background-color: #2E4053;
            }
            .css-1d391kg {
                color: #2D3436;
            }
            </style>
            """, unsafe_allow_html=True)
        st.subheader("Filtros de datos y opciones de descarga")

        # Mostrar el DataFrame filtrado con st.dataframe
        st.dataframe(df)

        # 🔹 Opción para descargar el archivo filtrado
    # 🔹 Opción para descargar el archivo filtrado automáticamente
    @st.cache_data
    def to_excel(df):
        """Convierte el DataFrame a un archivo Excel en formato bytes."""
        towrite = BytesIO()
        with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Datos Filtrados")
            writer._save()  # Guardar el archivo Excel
        return towrite.getvalue()

    # Convertir el DataFrame filtrado a Excel
    excel_file = to_excel(df)

    # Descargar automáticamente el archivo Excel
    st.download_button(
        label="📥 Descargar archivo Excel",
        data=excel_file,
        file_name="reporte_filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    
