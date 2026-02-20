import os
import google.generativeai as genai
from dotenv import load_dotenv

# Carga la clave
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ NO HAY API KEY EN .ENV")
else:
    genai.configure(api_key=api_key)
    print(f"🔑 Clave configurada. Consultando a Google...\n")
    
    try:
        print("--- MODELOS DISPONIBLES PARA TU CUENTA ---")
        count = 0
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"✅ {m.name}")
                count += 1
        
        if count == 0:
            print("⚠️ No se encontraron modelos. Tu API Key podría estar restringida o mal configurada.")
            
    except Exception as e:
        print(f"❌ Error conectando: {e}")