import pandas as pd
import time
import os
import sys
from datetime import datetime

# Importamos los módulos reales
from modules.scraper import Scraper
from modules.llm_engine import LLMEngine

class Orchestrator:
    
    def __init__(self):
        self.input_path = 'data/input/Matriz AR en blanco.xlsx'
        self.output_folder = 'data/output'
        
        # Instanciamos los agentes
        self.scraper = Scraper()
        self.llm = LLMEngine()
        
        # Aseguramos que existan carpetas de salida
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs('evidence', exist_ok=True)
        
    def run_benchmark(self, client_description, upload_file_obj=None, progress_callback=None):
        """
        Función principal que coordina todo el flujo.
        """
        
        # 1. Cargar los datos
        print("📂 Cargando Excel...")
        
        try:
            if upload_file_obj:
                df = pd.read_excel(upload_file_obj)
            else: 
                df = pd.read_excel(self.input_path)
        except Exception as e:
            return {"status": "error", "message": f"Error leyendo Excel: {str(e)}"}            
        
        # --- LIMPIEZA Y RE-INDEXACIÓN ---
        original_len = len(df)
        
        # Quitamos vacíos reales, pero mantenemos los "0"
        df = df.dropna(subset=['Sitio web'])
        
        # VITAL: Reenumerar las filas (0, 1, 2...) para evitar el error del 101% en la barra de progreso
        df = df.reset_index(drop=True)
        
        total_rows = len(df)
        print(f"🧹 Limpieza: {original_len} -> {total_rows} filas (Se mantuvieron valores '0')")
        
        results_df = df.copy()
        results_df = results_df.astype(object) 
        
        # Asegurar columnas de salida
        new_cols = ['Falta de información', 'Distintas funciones', 'Distinto servicio', 
                    'Grupo', 'A/R', 'Comentario', 'Link Evidencia', 'Nivel de Confianza']
        
        for col in new_cols:
            if col not in results_df.columns:
                results_df[col] = ''
                
        print(f"🚀 Iniciando procesamiento de {total_rows} empresas...")
        
        # 2. Bucle principal con enumerate para control exacto de la barra de progreso
        for i, (index, row) in enumerate(results_df.iterrows()):
                        
            # Actualizar UI (i + 1 siempre llegará al 100% exacto del total de filas)
            current_company = row.get("Nombre empresaAlfabeto latino", "Desconocida")
            if progress_callback:
                progress_callback(i + 1, total_rows, f'Analizando: {current_company}') 
                
            raw_url = str(row.get('Sitio web', '')).strip()
            
            # --- TRATAMIENTO DEL VALOR "0" ---
            if raw_url == "0" or not raw_url:
                results_df.at[index, 'A/R'] = 'R'
                results_df.at[index, 'Comentario'] = "Rechazado: Valor de sitio web no válido (0)."
                results_df.at[index, 'Falta de información'] = 'SI (Rechazado)'
                results_df.at[index, 'Nivel de Confianza'] = 100
                continue

            # --- Paso A: Scrapping (Texto) ---------
            web_data = self.scraper.extract_text(raw_url)
            
            # Si la web es basura o inaccesible, paramos aquí
            if web_data['is_junk'] or web_data['status'] != 200:
                results_df.at[index, 'A/R'] = 'R'
                results_df.at[index, 'Comentario'] = f"Error/Junk: {web_data.get('error_msg', 'Web inaccesible')}"
                results_df.at[index, 'Falta de información'] = 'SI (Rechazado)'
                continue
            
            # --- Paso B: INTELIGENCIA ARTIFICIAL ---------
            analysis = self.llm.analyze(web_data['text_content'], client_description)
                        
            # --- Paso C: EVIDENCIA (Screenshot + Highlight Láser) ---------
            quote_to_find = analysis.get('evidence_quote', '')
            target_url_for_screenshot = web_data.get('url_evidencia', raw_url)
            
            # El scraper llamará al worker con la lógica de resaltado de tus compañeros
            screenshot_path = self.scraper.take_screenshot(target_url_for_screenshot, quote_to_find)
            
            # --- Paso D: LÓGICA DE NEGOCIO ---------
            decision = 'A'
            reason = analysis.get('reasoning', 'Sin razonamiento')
            confidence = analysis.get('confidence_score', 0)
            
            results_df.at[index, 'Nivel de Confianza'] = confidence
            
            # Regla 1: Grupos fuera
            if analysis.get('is_group'):
                decision = 'R'
                results_df.at[index, 'Grupo'] = 'SI (Rechazado)' 
            else:
                results_df.at[index, 'Grupo'] = 'NO'
                
            # Regla 2: Manufactura fuera
            if analysis.get('is_manufacturer'):
                decision = "R"
                results_df.at[index, 'Distintas funciones'] = "SI (Rechazado)"
            else:
                results_df.at[index, 'Distintas funciones'] = "NO"
                
            # 3. Distinto servicio
            if not analysis.get('service_match', True): 
                decision = 'R'
                results_df.at[index, 'Distinto servicio'] = 'SI (Rechazado)'
            else:
                results_df.at[index, 'Distinto servicio'] = 'NO'
            
            # 4. Falta de información
            if confidence < 30:
                decision = 'R'
                results_df.at[index, 'Falta de información'] = 'SI (Rechazado)'
                reason = "Información insuficiente o web no operativa."
            else:
                results_df.at[index, 'Falta de información'] = 'NO'
                
            results_df.at[index, 'A/R'] = decision
            results_df.at[index, 'Comentario'] = f"{reason} (Confianza: {confidence}%)"
            
            # Hyperlink local para el Excel
            if screenshot_path:
                abs_path = os.path.abspath(screenshot_path)
                results_df.at[index, 'Link Evidencia'] = f'=HYPERLINK("{abs_path}", "Ver Evidencia")'
        
        # 3. Guardar resultados
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"Matriz_Trabajada_{timestamp}.xlsx"
        output_path = os.path.join(self.output_folder, output_filename)
        
        results_df.to_excel(output_path, index=False)
        print(f"✅ Proceso terminado. Archivo guardado en: {output_path}")
        
        return {"status": "success", "file_path": output_path, "dataframe": results_df}

if __name__ == "__main__":
    import asyncio
    import sys
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    def console_progress_bar(current, total, message):
        percent = float(current) * 100 / total
        bar_length = 40
        arrow = '█' * int(percent / 100 * bar_length - 1) + '>'
        spaces = ' ' * (bar_length - len(arrow))
        sys.stdout.write(f"\rProgress: [{arrow}{spaces}] {percent:.2f}% | {message}")
        sys.stdout.flush()
        
    orc = Orchestrator()
    orc.run_benchmark("Empresa de servicios administrativos",
                      progress_callback=console_progress_bar)