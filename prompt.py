
import json
import os
import google.generativeai as genai


# ==========================================
# CONFIGURACIÓN DE LA API KEY
# ==========================================
# OPCIÓN A (Para pruebas rápidas): Pega tu clave directamente aquí.
MI_CLAVE_API = "AIzaSyAm1lEtko2B5L-03nEMqMedW2GssnXh6B0" 

# OPCIÓN B (Enterprise/Producción): Usar variables de entorno (Recomendado)
# MI_CLAVE_API = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=MI_CLAVE_API)

# ==========================================
# CONFIGURACIÓN DEL MODELO IA
# ==========================================
# Usamos el parámetro response_mime_type para forzar el JSON mode
configuracion_generacion = genai.GenerationConfig(
    temperature=0.0, # Máximo determinismo
    response_mime_type="application/json", # Equivalente al response_format de OpenAI
)

# Inicializamos el modelo. 
# Recomiendo 'gemini-1.5-pro' o el modelo equivalente más reciente por su capacidad de razonamiento lógico.
modelo_tp = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=configuracion_generacion,
    system_instruction="Eres un sistema automatizado experto en Precios de Transferencia. Tu única salida válida es un objeto JSON estricto, sin formato Markdown ni texto adicional."
)

def evaluar_comparable(topic: str, web_json: str) -> dict:
    """
    Analiza el texto de la web usando Gemini y devuelve la decisión en JSON.
    """
    
    # Tu Prompt Maestro Optimizado
    prompt = f"""
# ROLE
Actúa como un Analista Senior de Precios de Transferencia y un motor de clasificación de datos precisos. Tu tarea es evaluar el contenido de una página web corporativa (proporcionado en formato JSON) para determinar si la empresa es un "Comparable Funcional" válido para nuestro cliente.

# CONTEXT & GOAL
Realizamos un Benchmark de Precios de Transferencia. Requerimos empresas totalmente INDEPENDIENTES y cuya actividad principal sea ESTRICTAMENTE IGUAL al {topic} de nuestro cliente.

# INPUTS
- TOPIC (Actividad del cliente): "{topic}"
- WEB_JSON (Contenido scrapeado): "{web_json}"

# EVALUATION STEPS
1. EVALUACIÓN DE INDEPENDENCIA: Analiza el WEB_JSON buscando menciones de "grupo", "holding", etc. Si pertenece a un grupo, es un descarte (is_group = true).
2. EVALUACIÓN DE ACTIVIDAD: Compara la actividad principal descrita en el WEB_JSON con el TOPIC. La coincidencia debe ser estricta.
3. RAZONAMIENTO: Explicación de máximo 15 palabras.
4. EXTRACCIÓN DE EVIDENCIA: 
   - SI RECHAZAS: Extrae el fragmento EXACTO y LITERAL del WEB_JSON (máx. 20 palabras).
   - SI ACEPTAS: "".
5. CÁLCULO DE CONFIANZA: Porcentaje de seguridad (0-100).

# OUTPUT CONSTRAINTS
- Tu respuesta DEBE ser ÚNICA Y EXCLUSIVAMENTE un objeto JSON válido.
- La estructura debe ser exactamente esta:
{{
  "is_group": boolean,
  "topic_match": boolean,
  "reasoning": "string",
  "evidence_quote": "string",
  "confidence_score": integer
}}
    """

    try:
        # Llamada a la API de Gemini
        respuesta = modelo_tp.generate_content(prompt)
        
        # Transformar el texto JSON devuelto a un diccionario de Python
        resultado_diccionario = json.loads(respuesta.text)
        
        return resultado_diccionario

    except json.JSONDecodeError:
        print("Error Crítico: Gemini no devolvió un JSON válido.")
        return None
    except Exception as e:
        print(f"Error en la llamada a la API de Gemini: {e}")
        return None

# --- Prueba de la función ---
# res = evaluar_comparable("Desarrollo de software a medida", '{"about": "Somos una filial de GlobalTech dedicada a crear apps."}')
# print(res)