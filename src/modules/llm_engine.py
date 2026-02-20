import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Cargamos las claves del archivo .env
load_dotenv()

class LLMEngine:
    
    def __init__(self):
        # 1. GESTIÓN DE API KEY
        self.api_key = os.getenv("GOOGLE_API_KEY")
        
        # Fallback si no hay .env (Pega tu clave aquí si es necesario)
        if not self.api_key:
            self.api_key = "TU_CLAVE_API_AQUI" 
            
        try:
            # Configuración de la librería antigua (estable)
            genai.configure(api_key=self.api_key)
        except Exception as e:
            print(f"❌ Error iniciando cliente Gemini: {e}")

    def _clean_json(self, text):
        """
        Limpia la respuesta de la IA. 
        A veces Gemini devuelve: ```json { ... } ``` y eso rompe el parser.
        Esta función extrae solo lo que hay entre { y }.
        """
        text = text.strip()
        # Si empieza con bloque de código, lo limpiamos
        if "```" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                return text[start:end]
        # Si devuelve texto plano con el json dentro
        if "{" in text and "}" in text:
             start = text.find("{")
             end = text.rfind("}") + 1
             return text[start:end]
        return text

    def analyze(self, text_content, client_description):
        """
        Analiza el texto de la web y devuelve el JSON estructurado.
        """
        
        # Validación básica de entrada
        if not text_content or len(text_content) < 50:
            return {
                "is_group": False, "is_manufacturer": False, "service_match": False,
                "reasoning": "Contenido web insuficiente o inaccesible.",
                "evidence_quote": "", "confidence_score": 0
            }

        # Prompt Estricto
        prompt = f"""
        Rol: Auditor de Precios de Transferencia.
        Objetivo: Determinar si la empresa analizada es comparable a la del cliente.
        
        CLIENTE: "{client_description}"
        
        TEXTO DE LA EMPRESA ANALIZADA:
        "{text_content[:8000]}"
        
        INSTRUCCIONES:
        Devuelve ÚNICAMENTE un objeto JSON válido. No escribas nada más.
        - evidence_quote: Debe ser una pequeña frase extraída LITERALMENTE del texto. 
          NO resumas, NO añadas puntos si no existen, copia y pega un fragmento exacto que justifique el rechazo.
        
        ESQUEMA JSON:
        {{
            "is_group": boolean, (True si menciona grupo, holding, filial, headquarters, subsidiaria o similares)
            "is_manufacturer": boolean, (True si menciona fábrica, producción, planta industrial. False si es servicios/distribución)
            "service_match": boolean, (True si la actividad coincide con la del cliente. No seas demasiado estricto eso luego lo indicaras en el confidence_score)
            "reasoning": "string", (Resumen muy breve del porqué)
            "evidence_quote": "string", (Frase literal corta que demuestre el rechazo. Vacío si se acepta)
            "confidence_score": int (0-100), (Indica la confianza que le determinas a tu aceptación o rechazo. Al ser más flexible habrán situaciones donde la confianza que pongas sea mas baja pero eso no es problema. Eso se marcará para que lo revise un humano)
        }}
        """

        # LISTA DE MODELOS A PROBAR (En orden de preferencia)
        # 1. gemini-1.5-flash: El mejor balance (gratis 1500/día).
        # 2. gemini-pro: El clásico (gratis 60/min), muy estable.
        models_to_try = [
            'gemini-2.5-flash',
            'gemini-2.5-flash-lite', 
            'gemini-2.0-flash',    
            'gemini-2.0-flash-001',       
            'gemini-2.0-flash-lite-001',         
            'gemini-2.0-flash-lite',          
        ]

        for model_name in models_to_try:
            try:
                # Instanciamos el modelo
                model = genai.GenerativeModel(model_name)
                
                # Generamos contenido (Sin forzar configuración JSON para evitar errores de versión)
                response = model.generate_content(prompt)
                
                if response.text:
                    # Limpiamos y parseamos
                    json_str = self._clean_json(response.text)
                    return json.loads(json_str)
                
            except Exception as e:
                # Si es un error de cuota (429), esperamos un poco
                error_msg = str(e)
                if "429" in error_msg:
                    print(f"⏳ Cuota excedida en {model_name}. Esperando 5s...")
                    time.sleep(5)
                    continue # Reintentamos o pasamos al siguiente
                elif "404" in error_msg:
                    print(f"⚠️ Modelo {model_name} no encontrado. Probando siguiente...")
                    continue # Pasamos al siguiente modelo de la lista
                else:
                    print(f"⚠️ Error desconocido en {model_name}: {e}")
                    # Si falla, intentamos el siguiente modelo por si acaso

        # SI FALLAN TODOS LOS MODELOS:
        return {
            "is_group": False, 
            "is_manufacturer": False, 
            "service_match": False,
            "reasoning": "Error de conexión con IA (Todos los modelos fallaron).", 
            "evidence_quote": "", 
            "confidence_score": 0
        }