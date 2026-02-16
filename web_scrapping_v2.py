# -*- coding: utf-8 -*-
"""
Created on Sun Feb 15 20:49:19 2026

@author: hugof
"""

import pandas as pd
import json
import os
import asyncio
import random
import nest_asyncio  
from playwright.async_api import async_playwright 

# Aplicamos el parche para que funcione en Spyder/Jupyter
nest_asyncio.apply()

# --- CONFIGURACIÓN (TUS VARIABLES) ---
ARCHIVO_EXCEL = "Matriz AR en blanco (Solo españolas) (1).xlsx" 
CARPETA_SALIDA = "data_json"           

# Nombres exactos de las columnas 
NOMBRE_COLUMNA_URL = "Sitio web"       
NOMBRE_COLUMNA_ID = "Nombre empresaAlfabeto latino"    

# Palabras clave
KEYWORDS_NAV = ["servicios", "services", "about", "nosotros", "grupo", "group", "quienes somos"]

# --- FUNCIONES ---

def limpiar_url(url):
    """Asegura que la URL tenga http/https y limpia espacios."""
    if not isinstance(url, str):
        return None
    url = url.strip()
    if not url.startswith("http"):
        return f"https://{url}"
    return url

async def extraer_texto_web(page, url, nombre_archivo_base, carpeta_salida):
    """Navega, saca FOTO y extrae texto."""
    contenido_total = ""
    try:
        print(f"   -> Visitando: {url}")
        # Await es necesario para operaciones de red
        await page.goto(url, timeout=15000, wait_until="domcontentloaded")
        
        # Esperamos un poco para que cargue visualmente
        await asyncio.sleep(random.uniform(1, 3))
        
        # --- NUEVO: CAPTURA DE PANTALLA ---
        # Guardamos la evidencia visual de la Home
        ruta_foto = os.path.join(carpeta_salida, f"{nombre_archivo_base}_HOME.png")
        try:
            await page.screenshot(path=ruta_foto)
            print(f"   -> [FOTO] Guardada en: {ruta_foto}")
        except Exception as e:
            print(f"   -> [!] Error sacando foto: {e}")
        # ----------------------------------
        
        # 1. Extraer texto de la HOME
        titulo = await page.title()
        texto_home = await page.locator("body").inner_text()
        contenido_total += f"--- PÁGINA: HOME ({titulo}) ---\n{texto_home}\n\n"
        
        # 2. Buscar enlaces interesantes
        links = await page.get_by_role("link").all()
        url_secundaria = None
        
        # Revisamos los primeros 50 enlaces para no saturar
        for link in links[:50]:
            try:
                texto_link = await link.inner_text()
                texto_link = texto_link.lower()
                
                if any(kw in texto_link for kw in KEYWORDS_NAV):
                    href = await link.get_attribute("href")
                    if href:
                        url_secundaria = href
                        print(f"   -> Encontrado enlace relevante: {texto_link}")
                        break 
            except:
                continue
        
        # 3. Si encontramos sub-página, entramos
        if url_secundaria:
            try:
                # Construir URL absoluta si es relativa
                if not url_secundaria.startswith("http"):
                    base_url = url.rstrip("/")
                    if url_secundaria.startswith("/"):
                         url_secundaria = base_url + url_secundaria
                    else:
                         url_secundaria = base_url + "/" + url_secundaria
                
                print(f"   -> Navegando a sección extra: {url_secundaria}")
                await page.goto(url_secundaria, timeout=10000, wait_until="domcontentloaded")
                
                # Opcional: Si quisieras foto de la sección extra, se pondría aquí.
                # De momento con la HOME suele valer como evidencia principal.
                
                texto_secundario = await page.locator("body").inner_text()
                contenido_total += f"--- PÁGINA: SECCIÓN EXTRA ---\n{texto_secundario}\n"
            except Exception as e:
                print(f"   -> No se pudo cargar la sección extra: {e}")

    except Exception as e:
        print(f"   [!] Error cargando {url}: {e}")
        return None 

    return contenido_total

# --- PROCESO PRINCIPAL ---

async def main():
    # 1. Crear carpeta
    if not os.path.exists(CARPETA_SALIDA):
        os.makedirs(CARPETA_SALIDA)

    # 2. Cargar Excel
    print("Cargando Excel...")
    try:
        # header=0 coge la primera fila como títulos
        df = pd.read_excel(ARCHIVO_EXCEL, header=0) 
    except Exception as e:
        print(f"Error leyendo el Excel: {e}")
        return

    # 3. Iniciar el navegador (ASYNC)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # False para ver el navegador
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        page = await context.new_page()

        total_procesados = 0
        
        for index, row in df.iterrows():
            nombre_empresa = str(row[NOMBRE_COLUMNA_ID]).strip()
            raw_url = row[NOMBRE_COLUMNA_URL]
            
            # Limpieza del nombre de archivo
            nombre_archivo = "".join([c for c in nombre_empresa if c.isalnum() or c in (' ', '_')]).rstrip()
            ruta_json = os.path.join(CARPETA_SALIDA, f"{index}_{nombre_archivo}.json")
            
            # Saltamos si ya existe el JSON (asumimos que si hay JSON, hubo intento de foto)
            if os.path.exists(ruta_json):
                print(f"Skipping {nombre_empresa}, ya existe.")
                continue

            url_final = limpiar_url(raw_url)
            
            # Gestión de filas sin URL
            if not url_final or pd.isna(raw_url):
                print(f"Fila {index}: {nombre_empresa} -> Sin URL válida.")
                datos = {"empresa": nombre_empresa, "status": "no_url", "texto": ""}
                with open(ruta_json, 'w', encoding='utf-8') as f:
                    json.dump(datos, f, ensure_ascii=False, indent=4)
                continue

            print(f"[{index}/{len(df)}] Procesando: {nombre_empresa} -> {url_final}")
            
            # --- MODIFICADO: Pasamos nombre_archivo y carpeta para la foto ---
            texto_extraido = await extraer_texto_web(page, url_final, nombre_archivo, CARPETA_SALIDA)
            # ----------------------------------------------------------------
            
            estado = "ok" if texto_extraido else "error_carga"
            
            datos = {
                "id_excel": index,
                "empresa": nombre_empresa,
                "url": url_final,
                "status": estado,
                "texto": texto_extraido if texto_extraido else ""
            }
            
            with open(ruta_json, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=4)
                
            total_procesados += 1
            await asyncio.sleep(0.5) 

        await browser.close()
        print(f"\nProceso finalizado. {total_procesados} empresas procesadas.")

if __name__ == "__main__":
    asyncio.run(main())