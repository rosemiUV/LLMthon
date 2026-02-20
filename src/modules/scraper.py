import json
import subprocess
import os
import sys
from datetime import datetime
from urllib.parse import urlparse

class Scraper:
    def __init__(self):
        # Ruta al worker.py
        self.worker_path = os.path.join("src", "modules", "worker.py")

    def extract_text(self, url):
        """
        Lanza un subproceso aislado para evitar choques con Streamlit.
        """
        print(f"🕷️ Scraping: {url}")
        
        # Estructura de error estándar
        error_response = {
            "status": 500, 
            "is_junk": False, 
            "text_content": "", 
            "error_msg": "", 
            "url_evidencia": url # Si falla, la evidencia es la URL original
        }

        try:
            # Ejecutamos worker.py como un proceso independiente
            result = subprocess.run(
                [sys.executable, self.worker_path, str(url)],
                capture_output=True,
                text=True,
                encoding='utf-8' 
            )
            
            if result.returncode != 0:
                error_response["error_msg"] = f"Worker Failed: {result.stderr}"
                return error_response
            
            # Parseamos el JSON que nos devuelve el worker
            try:
                data = json.loads(result.stdout)
                return data
            except json.JSONDecodeError:
                error_response["error_msg"] = "Invalid JSON from worker"
                # Opcional: imprimir stdout para debug
                print(f"DEBUG WORKER STDOUT: {result.stdout}")
                return error_response

        except Exception as e:
            error_response["error_msg"] = f"Subprocess Error: {str(e)}"
            return error_response

    def take_screenshot(self, url, text_to_highlight):
        """
        MODO 2: Captura de Evidencia (Nuevo).
        Llama al worker con el comando "screenshot" y un JSON de configuración.
        """
        if not url: return None
        
        # Limpiamos el texto a resaltar (máximo 50 chars para log)
        preview_text = text_to_highlight[:30] + "..." if text_to_highlight else "Sin texto"
        print(f"📸 Generando Evidencia: {url} (Highlight: '{preview_text}')")
        
        # 1. Definir ruta de salida única
        try:
            domain = urlparse(url).netloc.replace("www.", "").replace(".", "_")
            if not domain: domain = "unknown_domain"
        except:
            domain = "unknown_domain"
            
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{domain}_{timestamp}.png"
        
        # Aseguramos carpeta evidence
        evidence_dir = "evidence"
        os.makedirs(evidence_dir, exist_ok=True)
        output_path = os.path.join(evidence_dir, filename)
        
        # 2. Configurar el payload para el worker
        config = {
            "url": url,
            "text": text_to_highlight,
            "path": output_path
        }
        
        try:
            # LLAMADA AL WORKER EN MODO SCREENSHOT
            # Argumentos: [worker.py, "screenshot", '{json_config}']
            result = subprocess.run(
                [sys.executable, self.worker_path, "screenshot", json.dumps(config)],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            # 3. Analizar respuesta
            try:
                # El worker imprime un JSON por stdout
                response = json.loads(result.stdout)
                
                if response.get("success"):
                    print(f"✅ Evidencia guardada: {output_path}")
                    return output_path
                else:
                    print(f"⚠️ Fallo en worker screenshot: {result.stdout}")
                    return None
            except json.JSONDecodeError:
                print(f"⚠️ Error decodificando respuesta del worker: {result.stdout}")
                return None
                
        except Exception as e:
            print(f"⚠️ Error subprocess screenshot: {e}")
            return None