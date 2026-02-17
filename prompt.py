import os
from google import genai
from pydantic import BaseModel, Field

# 1. ESQUEMA DE DATOS ESTRICTO (PYDANTIC)
class EvaluacionComparable(BaseModel):
    is_group: bool = Field(description="True si se debe rechazar por pertenecer a un Grupo corporativo/Holding.")
    topic_match: bool = Field(description="True si la actividad comercial coincide ESTRICTAMENTE.")
    reasoning: str = Field(description="Explicación breve de 1 línea del análisis.")
    evidence_quote: str = Field(description="Frase literal extraída que justifica el rechazo. Vacío si se acepta.")
    confidence_score: int = Field(description="Entero de 0 a 100 indicando la seguridad de la predicción.")

# 2. CONFIGURACIÓN DEL CLIENTE


MI_CLAVE_API = "AIzaSyAm1lEtko2B5L-03nEMqMedW2GssnXh6B0"
client = genai.Client(api_key=MI_CLAVE_API)

def evaluar_comparable(topic: str, web_json: str) -> dict:
    """
    Analiza el texto de la web y devuelve el JSON estructurado.
    """
    prompt = f"""
    # ROLE
    Actúa como un Analista Senior de Precios de Transferencia y un motor de clasificación de datos precisos. Tu tarea es evaluar el contenido de una página web corporativa (proporcionado en formato JSON) para determinar si la empresa es un "Comparable Funcional" válido para nuestro cliente.

    # CONTEXT & GOAL
    Realizamos un Benchmark de Precios de Transferencia. Requerimos empresas totalmente INDEPENDIENTES y cuya actividad principal sea ESTRICTAMENTE IGUAL al {topic} de nuestro cliente.

    # INPUTS
    - TOPIC (Actividad del cliente): "{topic}"
    - WEB_JSON (Contenido scrapeado): "{web_json}"

    # EVALUATION STEPS
    1. EVALUACIÓN DE INDEPENDENCIA: Analiza el WEB_JSON buscando menciones de "grupo", "holding", "subsidiaria", etc. Si pertenece a un grupo, es un descarte (is_group = true).
    2. EVALUACIÓN DE ACTIVIDAD: Compara la actividad principal descrita en el WEB_JSON con el TOPIC. La coincidencia debe ser estricta.
    3. RAZONAMIENTO: Explicación de máximo 15 palabras.
    4. EXTRACCIÓN DE EVIDENCIA: 
       - SI RECHAZAS: Extrae el fragmento EXACTO y LITERAL del WEB_JSON.
       - SI ACEPTAS: Déjalo vacío ("").
    5. CÁLCULO DE CONFIANZA: Porcentaje de seguridad (0-100).
    """

    try:
        # Usamos exactamente el nombre que te dio tu consola (sin el 'models/')
        response = client.models.generate_content(
            model='gemini-2.5-flash', # Puedes cambiarlo a 'gemini-2.5-pro' si prefieres la versión estable anterior
            contents=prompt,
            config={
                'temperature': 0.0, # Vital mantenerlo en 0.0 para análisis legal/fiscal
                'response_mime_type': 'application/json',
                'response_schema': EvaluacionComparable,
            }
        )
        
        
        # Pydantic y el SDK hacen el parseo automático y seguro
        if response.parsed:
            return response.parsed.model_dump()
        else:
            return None

    except Exception as e:
        print(f"Error en la API: {e}")
        return None

# 3. PRUEBA DE FUEGO
if __name__ == "__main__":
    print("Iniciando análisis...")
    # Simulamos el JSON extraído del web scraping
    json_prueba = '{"about": "Somos Logistics X. Formamos parte del poderoso Grupo Omega Global y nos dedicamos a la logística internacional."}'
    
    resultado = evaluar_comparable(topic="Servicios de transporte y logística", web_json=json_prueba)
    
    print("\n=== RESULTADO DEL ANÁLISIS ===")
    print(resultado)