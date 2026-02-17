import pandas as pd
import json
import os
import asyncio
import random
import nest_asyncio
from playwright.async_api import async_playwright

# Aplicamos el parche para Spyder
nest_asyncio.apply()

# --- CONFIGURACIÓN ---
ARCHIVO_EXCEL = "Matriz AR en blanco (Solo españolas) (1).xlsx"
CARPETA_SALIDA = "data_json"

# Tus columnas exactas
NOMBRE_COLUMNA_URL = "Sitio web"
NOMBRE_COLUMNA_ID = "Nombre empresaAlfabeto latino"

# Palabras clave de navegación
KEYWORDS_NAV = ["servicios", "services", "about", "nosotros", "grupo", "group", "quienes somos"]

# Palabras clave para detectar webs basura (Parked domains)
KEYWORDS_JUNK = [
    "domain for sale", "comprar este dominio", "parked free", "godaddy", 
    "sedo", "hugedomains", "namecheap", "this domain is available", 
    "buy this domain", "dominio a la venta", "site under construction",
    "coming soon", "renew now"
]

# --- FUNCIONES ---

def limpiar_url(url):
    if not isinstance(url, str):
        return None
    url = url.strip()
    if not url.startswith("http"):
        return f"https://{url}"
    return url

def es_junk(texto, titulo):
    """Devuelve True si detecta patrones de venta de dominios."""
    texto_bajo = texto.lower()[:1000] # Miramos solo el principio
    titulo_bajo = titulo.lower()
    
    for kw in KEYWORDS_JUNK:
        if kw in texto_bajo or kw in titulo_bajo:
            return True
    return False

async def procesar_web(page, url):
    """
    Navega y extrae info estructurada (Status, Junk, Texto).
    Devuelve un diccionario con las variables solicitadas.
    """
    # Estructura base del resultado
    resultado = {
        "status": None,      
        "is_junk": False,    
        "text_content": "",  
        "error_msg": None    
    }

    try:
        print(f"   -> Visitando: {url}")
        
        # Intentamos ir a la web y capturar la RESPUESTA (para sacar el status code)
        response = await page.goto(url, timeout=15000, wait_until="domcontentloaded")
        
        # Pausa humana aleatoria
        await asyncio.sleep(random.uniform(1, 2))
        
        if response:
            resultado["status"] = response.status
        else:
            # A veces no hay response si hay error DNS
            resultado["status"] = 0 

        # Si el status es malo (404, 500), paramos aquí
        if resultado["status"] >= 400:
            resultado["error_msg"] = f"HTTP Error {resultado['status']}"
            return resultado

        # 1. Extraer texto HOME
        titulo = await page.title()
        texto_home = await page.locator("body").inner_text()
        
        # Comprobación de JUNK inmediata
        if es_junk(texto_home, titulo):
            print("   -> [JUNK] Web de parking/venta detectada.")
            resultado["is_junk"] = True
            resultado["text_content"] = f"TITULO: {titulo}\nTEXTO: {texto_home[:500]}..." # Guardamos poco texto
            return resultado

        resultado["text_content"] += f"--- PÁGINA: HOME ({titulo}) ---\n{texto_home}\n\n"

        # 2. Navegación a Sección Extra (Lógica Robusta)
        links = await page.get_by_role("link").all()
        url_secundaria = None
        
        for link in links[:50]:
            try:
                txt = await link.inner_text()
                if any(kw in txt.lower() for kw in KEYWORDS_NAV):
                    href = await link.get_attribute("href")
                    if href:
                        url_secundaria = href
                        print(f"   -> Encontrado enlace: {txt}")
                        break
            except:
                continue
        
        if url_secundaria:
            try:
                # Construcción URL absoluta
                if not url_secundaria.startswith("http"):
                    base = url.rstrip("/")
                    url_secundaria = base + url_secundaria if url_secundaria.startswith("/") else base + "/" + url_secundaria
                
                print(f"   -> Navegando a sección extra: {url_secundaria}")
                
                # --- CAMBIO IMPORTANTE: Espera robusta ---
                await page.goto(url_secundaria, timeout=20000, wait_until="domcontentloaded")
                
                # Esperamos 2 segundos REALES para que el JS termine de cargar el texto
                await asyncio.sleep(2) 
                
                texto_secundario = await page.locator("body").inner_text()
                
                # Validación de contenido vacío
                if len(texto_secundario) > 100:
                    resultado["text_content"] += f"--- PÁGINA: SECCIÓN EXTRA ---\n{texto_secundario}\n"
                else:
                    print("   -> [WARN] Sección extra vacía o no cargó bien.")
                    
            except Exception as e:
                print(f"   -> Fallo en sección extra: {e}")
                # No marcamos error global, porque ya tenemos la Home

    except Exception as e:
        print(f"   [!] Error crítico en {url}: {e}")
        resultado["error_msg"] = str(e)
        if not resultado["status"]:
            resultado["status"] = 0 # Error de conexión/DNS

    return resultado

# --- PROCESO PRINCIPAL ---

async def main():
    if not os.path.exists(CARPETA_SALIDA):
        os.makedirs(CARPETA_SALIDA)

    print("Cargando Excel...")
    try:
        df = pd.read_excel(ARCHIVO_EXCEL, header=0) 
    except Exception as e:
        print(f"Error Excel: {e}")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        total = 0
        for index, row in df.iterrows():
            nombre = str(row[NOMBRE_COLUMNA_ID]).strip()
            raw_url = row[NOMBRE_COLUMNA_URL]
            
            # Nombre de archivo limpio
            safe_name = "".join([c for c in nombre if c.isalnum() or c in (' ', '_')]).rstrip()
            ruta_json = os.path.join(CARPETA_SALIDA, f"{index}_{safe_name}.json")
            
            if os.path.exists(ruta_json):
                print(f"Skipping {nombre}, ya existe.")
                continue

            url_final = limpiar_url(raw_url)
            
            # Caso sin URL
            if not url_final or pd.isna(raw_url):
                print(f"Fila {index}: {nombre} -> Sin URL.")
                datos = {
                    "id_excel": index,
                    "empresa": nombre,
                    "url": None,
                    "status": None,
                    "is_junk": "False", # CORREGIDO: String "False"
                    "text_content": "",
                    "error_msg": "URL vacía en Excel" # Esto ya es un string, OK
                }
                with open(ruta_json, 'w', encoding='utf-8') as f:
                    json.dump(datos, f, ensure_ascii=False, indent=4)
                continue

            print(f"[{index}/{len(df)}] Procesando: {nombre} -> {url_final}")
            
            # --- LLAMADA A LA FUNCIÓN ---
            resultado_web = await procesar_web(page, url_final)
            
            # Construimos el JSON final fusionando datos y CONVIRTIENDO A STRING
            datos_finales = {
                "id_excel": index,
                "empresa": nombre,
                "url": url_final,
                "status": resultado_web["status"],
                # CORRECCIÓN AQUÍ: Usamos str() para que guarde "True"/"False" y "None"
                "is_junk": str(resultado_web["is_junk"]), 
                "text_content": resultado_web["text_content"],
                "error_msg": str(resultado_web["error_msg"]) 
            }
            
            with open(ruta_json, 'w', encoding='utf-8') as f:
                json.dump(datos_finales, f, ensure_ascii=False, indent=4)
                
            total += 1
            await asyncio.sleep(0.5)

        await browser.close()
        print(f"\nProceso finalizado. {total} empresas.")

if __name__ == "__main__":
    asyncio.run(main())