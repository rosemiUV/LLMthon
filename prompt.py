
import json
from openai import OpenAI

# Inicializa el cliente (Asegúrate de tener tu OPENAI_API_KEY en las variables de entorno)
client = OpenAI()

def evaluar_comparable(topic: str, web_json: str) -> dict:
    """
    Analiza el texto de la web y devuelve la decisión de comparabilidad en JSON.
    """
    
    # Tu prompt maestro inyectando las variables
    
    prompt = f"""
        # ROLE
Actúa como un Analista Senior de Precios de Transferencia y un motor de clasificación de datos precisos. Tu tarea es evaluar el contenido de una página web corporativa (proporcionado en formato JSON) para determinar si la empresa es un "Comparable Funcional" válido para nuestro cliente.

# CONTEXT & GOAL
Realizamos un Benchmark de Precios de Transferencia. Requerimos empresas totalmente INDEPENDIENTES (que no pertenezcan a un grupo corporativo) y cuya actividad comercial principal sea ESTRICTAMENTE IGUAL al {topic} de nuestro cliente. 
El contenido de entrada puede estar en cualquier idioma; debes procesarlo y comprenderlo, pero las extracciones de texto literal deben mantenerse en su idioma original.

# INPUTS
- TOPIC (Actividad del cliente): "{topic}"
- WEB_JSON (Contenido scrapeado): "{web_json}"

# EVALUATION STEPS (Sigue esta lógica estrictamente)
1. EVALUACIÓN DE INDEPENDENCIA: Analiza el WEB_JSON buscando menciones de "grupo", "holding", "subsidiaria", "parte de", "filial", "empresa matriz", etc. Si pertenece a un grupo, es un descarte (is_group = true).
2. EVALUACIÓN DE ACTIVIDAD: Compara la actividad principal descrita en el WEB_JSON con el TOPIC. La coincidencia debe ser estricta. Un producto no es un servicio. "Venta de peluches" no es "Venta de muebles". Si no coincide exactamente, es un descarte (topic_match = false).
3. RAZONAMIENTO: Formula una explicación de máximo 15 palabras del porqué de tu decisión.
4. EXTRACCIÓN DE EVIDENCIA: 
   - SI RECHAZAS a la empresa (is_group = true O topic_match = false), extrae el fragmento EXACTO y LITERAL del WEB_JSON (máx. 20 palabras) que justifica el rechazo.
   - SI ACEPTAS a la empresa (is_group = false Y topic_match = true), este campo debe ser un string vacío "".
5. CÁLCULO DE CONFIANZA: Asigna un porcentaje de seguridad (0-100) sobre tu análisis. Usa puntuaciones bajas (<70) si la web tiene poca información o es ambigua.

# OUTPUT CONSTRAINTS
- Tu respuesta DEBE ser ÚNICA Y EXCLUSIVAMENTE un objeto JSON válido.
- No incluyas saludos, no incluyas bloques de código Markdown (```json), ni texto antes o después.
- La estructura debe ser exactamente esta:

{
  "is_group": boolean,
  "topic_match": boolean,
  "reasoning": "string",
  "evidence_quote": "string",
  "confidence_score": integer
}
        """

    try:
        # Llamada a la API optimizada para producción
        response = client.chat.completions.create(
            model="gpt-4o", # El modelo más preciso para razonamiento y JSON mode
            messages=[
                {
                    "role": "system", 
                    "content": "Eres un sistema automatizado experto en Precios de Transferencia. Tu única salida válida es un objeto JSON estricto, sin formato Markdown ni texto adicional."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.0, # Determinismo máximo (respuestas consistentes)
            response_format={"type": "json_object"} # Fuerza al modelo a validar la estructura JSON
        )
        
        # Extracción de la respuesta del LLM
        respuesta_raw = response.choices[0].message.content
        
        # Transformar el string JSON a un diccionario de Python
        resultado_diccionario = json.loads(respuesta_raw)
        
        return resultado_diccionario

    except json.JSONDecodeError:
        print("Error: El modelo no devolvió un JSON válido.")
        return None
    except Exception as e:
        print(f"Error crítico en la llamada a la API: {e}")
        return None

# --- Ejemplo de Uso ---
# resultado = evaluar_comparable("Servicios de logística en frío", '{"about_us": "Somos parte de Grupo Omega..."}')
# print(resultado['is_group']) # Devolvería True