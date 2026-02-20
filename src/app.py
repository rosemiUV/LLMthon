import streamlit as st
import pandas as pd
import os
import time
import altair as alt 

# Importamos tu orquestador
from core.orchestrator import Orchestrator

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="TP Benchmark AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        height: 3em;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    </style>
""", unsafe_allow_html=True)



# --- FUNCIÓN DE ESTILOS PARA LA TABLA ---
def highlight_row_low_confidence(row):
    """
    Pinta TODA la fila de naranja si 'Nivel de Confianza' < 80.
    """
    # Color de fondo para filas de baja confianza
    bg_color = 'background-color: #ffeeba; color: black;' # Amarillo suave
    default = ''
    
    try:
        # Buscamos el valor en la columna específica
        val = row.get('Nivel de Confianza', 0)
        score = float(val)
        
        if score < 80:
            # Devolvemos el estilo para CADA celda de la fila
            return [bg_color] * len(row)
    except:
        pass 
    
    # Si no cumple, estilo por defecto
    return [default] * len(row)



def main():
    
    # --- SIDEBAR: CONTROLES ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2103/2103633.png", width=45)
        st.title("TP Benchmark")
        st.caption("v1.0.0 - Datathon Edition")
        
        st.markdown('---')
        st.info("💡 **Tip:** Asegúrate de que el Excel tiene una columna llamada 'Sitio web'.")
        
        
    # --- PÁGINA PRINCIPAL ---
    st.title("🤖 Auditoría Automática de Precios de Transferencia")
    st.markdown("""
    Esta herramienta automatiza la búsqueda de comparables utilizando **Agentes de IA** y **Navegación Web Autónoma**.
    """)
    
    # Layout de columnas para inputs
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader('1. Definición del cliente')
        client_desc = st.text_area(
            'Descripción de la Actividad:',
            value='Servicios de apoyo a la gestión (administrativos, nóminas, contabilidad, IT básico)',
            height=95,
            help="El LLM usará esto para comparar cada empresa."
        )
        
    with col2: 
        st.subheader('2. Dataset')
        uploaded_file = st.file_uploader("Subir Matriz AR (.xlsx)", type=["xlsx"])
        
        if uploaded_file:
            try:
                df_preview = pd.read_excel(uploaded_file)
                df = df_preview.dropna(subset=['Sitio web']) # O la columna clave que uses
                st.success(f"✅ Archivo cargado: {len(df)} empresas.")
            except Exception as e:
                st.error("❌ Error al leer el Excel.")
                
    
    # --- BOTÓN DE EJECUCIÓN ---
    st.markdown('---')
    
    # Usamos session_state para guardar resultados si recargamos la página
    if "results" not in st.session_state:
        st.session_state.results = None
        
    start_btn = st.button("🚀 EJECUTAR ANÁLISIS COMPLETO", type="primary", disabled=(not uploaded_file))
    
    if start_btn:
        if not uploaded_file:
            st.error("Por favor, sube un archivo primero.")
        else:
            
            # Rebobinamos el archivo (FIX DE LECTURA)
            uploaded_file.seek(0)
            
            # --- INICIO DEL PROCESO ---
            try:
                orchestrator = Orchestrator()
            except Exception as e:
                st.error(f"Error al iniciar el orquestador: {e}")
                st.stop()
            
            # Contenedores para feedback visual
            progress_bar = st.progress(0)
            status_text = st.empty()
            logs_expander = st.expander("Ver Logs del Sistema", expanded=True)
            
            with logs_expander:
                log_area = st.empty()
                logs = []
                
            # Callback que conecta el backend con el frontend
            def ui_callback(current, total, message):
                percent = int((current/total)*100)
                progress_bar.progress(percent)
                status_text.markdown(f"**Procesando {current}/{total}:** `{message}`")
                
                # Logs tipo consola
                logs.append(f"[{time.strftime('%H:%M:%S')}] {message}")
                # Mostramos solo los últimos 5 logs para no saturar
                log_area.code("\n".join(logs[-5:]), language="text")
                
            try:
                # Llamada al orquestador
                with st.spinner("Los agentes están trabajando..."):
                    result = orchestrator.run_benchmark(
                        client_description=client_desc,
                        upload_file_obj=uploaded_file,
                        progress_callback=ui_callback
                    )
                    
                if result['status'] == 'success':
                    st.session_state.results = result # Guardamos en memoria
                    st.balloons()
                else:
                    st.error(f"Error crítico: {result['message']}")
                    
            except Exception as e:
                st.error(f"Ocurrió un error inesperado: {str(e)}")
                
            
    # --- MOSTRAR RESULTADOS (Si existen en memoria) ---
    if st.session_state.results:
        result = st.session_state.results
        final_df = result['dataframe']
        file_path = result['file_path']
        
        st.markdown("### 📊 Resultados del Benchmark")
        
        # 1. LIMPIEZA DE DATOS (Vital para evitar errores de visualización)
        display_df = final_df.astype(str).replace("nan", "")        
        
        # MÉTRICAS (KPIs)
        total = len(final_df)
        # Buscamos 'R' de forma segura (case insensitive)
        rejected = len(display_df[display_df['A/R'].str.contains('R', case=False, na=False)])
        accepted = total - rejected
        
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        col_kpi1.metric("Total Empresas", total)
        col_kpi2.metric("Aceptadas (Comparables)", accepted, delta_color="normal")
        col_kpi3.metric("Rechazadas", rejected, delta_color="inverse")
        
        # PESTAÑAS DE DETALLE
        tab1, tab2 = st.tabs(["📂 Tabla de Datos", "📈 Análisis Gráfico"])
        
        with tab1:
            st.markdown("💡 *Las **filas completas** con Nivel de Confianza < 80% se resaltan en amarillo.*")
            
            # --- CORRECCIÓN CRÍTICA DE TIPOS (ARROW INVALID FIX) ---
            # 1. Creamos una copia para visualización
            display_df = final_df.copy()
            
            # 2. Aseguramos que 'Nivel de Confianza' sea numérico para que la lógica de color funcione
            if 'Nivel de Confianza' in display_df.columns:
                display_df['Nivel de Confianza'] = pd.to_numeric(
                    display_df['Nivel de Confianza'], errors='coerce'
                ).fillna(0)
            
            # 3. FORZAMOS TODO LO DEMÁS A TEXTO (Esto evita que explote con 'n.d.')
            for col in display_df.columns:
                if col != 'Nivel de Confianza':
                    # Convertimos a string y reemplazamos 'nan' literal
                    display_df[col] = display_df[col].astype(str).replace('nan', '')

            # 4. APLICAMOS EL ESTILO Y MOSTRAMOS
            if 'Nivel de Confianza' in display_df.columns:
                st.dataframe(
                    display_df.style.apply(highlight_row_low_confidence, axis=1)
                    .format({'Nivel de Confianza': '{:.0f}%'}),
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.dataframe(display_df, hide_index=True, use_container_width=True)
            # -------------------------------------------------------
            
            st.markdown("---")          
            
            # BOTÓN DE DESCARGA
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    st.download_button(
                        label="📥 Descargar Reporte Excel Final",
                        data=f,
                        file_name=os.path.basename(file_path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        key="btn_download_unique_id" # Key única para evitar duplicados
                    )
                st.info(f"Evidencias guardadas localmente en: `{os.path.abspath('evidence/')}`")
            else:
                st.error("No se encontró el archivo generado.")
            
        with tab2:
            st.markdown("#### 🎯 Ratio de Aceptación")
            
            source = pd.DataFrame({
                "Estado": ["Aceptadas", "Rechazadas"],
                "Cantidad": [accepted, rejected]
            })

            base = alt.Chart(source).encode(
                theta=alt.Theta("Cantidad", stack=True)
            )

            # FIX: Cambiado 'use_container_width' por 'width' si fuera necesario, 
            # pero mantenemos el chart limpio.
            pie = base.mark_arc(innerRadius=60, outerRadius=120).encode(
                color=alt.Color(
                    "Estado",
                    scale=alt.Scale(domain=["Aceptadas", "Rechazadas"], range=["#28a745", "#dc3545"]),
                    legend=alt.Legend(title="Resultado")
                ),
                order=alt.Order("Cantidad", sort="descending"),
                tooltip=["Estado", "Cantidad", alt.Tooltip("Cantidad", format=",")]
            )

            text = base.mark_text(radius=140).encode(
                text="Cantidad",
                order=alt.Order("Cantidad", sort="descending"),
                color=alt.value("black") 
            )

            st.altair_chart(pie + text, use_container_width=True)
            
            if total > 0:
                acceptance_rate = (accepted / total) * 100
                st.caption(f"Tasa de éxito del **{acceptance_rate:.1f}%** sobre el total de la muestra.")

if __name__ == '__main__':
    main()