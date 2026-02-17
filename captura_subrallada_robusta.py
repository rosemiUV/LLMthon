import os
import asyncio
import nest_asyncio
import random 
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# Esto evita conflictos con el event loop
nest_asyncio.apply()

# --- FUNCIÓN DEFINITIVA PARA RESALTADO LÁSER ---
async def resaltar_texto_en_pagina(page, texto):
    """
    Busca la frase exacta y usa una Regex Flexible para ignorar etiquetas HTML
    intermedias o saltos de línea, subrayando SOLO la evidencia.
    """
    if not texto:
        return

    print(f"Intentando resaltar con precisión láser: '{texto}'...")
    try:
        locator = page.get_by_text(texto, exact=False)
        count = await locator.count()
        
        if count == 0:
            print(f"No se encontró el texto. Se hará captura limpia.")
            return

        print(f"Se encontraron {count} ocurrencias. Aplicando subrayador...")

        # Script JS con Regex Flexible
        js_script = r"""
        (element, textToHighlight) => {
            // 1. Escapamos los caracteres especiales del texto objetivo
            const escapeRegExp = (string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            let escapedText = escapeRegExp(textToHighlight);

            // 2. LA MAGIA: Reemplazamos los espacios literales por un comodín
            // Este comodín (?:\\s|&nbsp;|<[^>]+>)* significa: "acepta cualquier espacio, salto de línea o etiqueta HTML que esté en medio de las palabras"
            let flexibleRegexString = escapedText.replace(/\\ /g, '(?:\\s|&nbsp;|<[^>]+>)*');
            
            // Creamos la regla de búsqueda global ignorando mayúsculas/minúsculas
            const regex = new RegExp(`(${flexibleRegexString})`, 'gi');

            if (!element.innerHTML.includes('rpa-highlight-mark')) {
                // Comprobamos si nuestra nueva super-regex encuentra la frase
                if (regex.test(element.innerHTML)) {
                    // PLAN A (Éxito): Envuelve SOLO la frase exacta, manteniendo el resto del párrafo intacto
                    element.innerHTML = element.innerHTML.replace(
                        regex, 
                        `<span class="rpa-highlight-mark" style="background-color: #FFFF00 !important; color: #000000 !important; outline: 3px solid red !important; font-weight: bold !important; box-shadow: 0 0 10px yellow !important; border-radius: 4px; padding: 2px;">$1</span>`
                    );
                } else {
                    // PLAN B (Solo si el DOM es extremadamente caótico): Subraya la caja
                    element.style.cssText += 'background-color: #FFFF00 !important; color: #000000 !important; outline: 3px solid red !important; font-weight: bold !important; box-shadow: 0 0 10px yellow !important;';
                }
            }
            
            // Movemos la cámara al lugar exacto
            element.scrollIntoView({behavior: "smooth", block: "center", inline: "nearest"});
        }
        """

        for i in range(count):
            element_handle = locator.nth(i)
            await element_handle.evaluate(js_script, texto)
            
        await asyncio.sleep(0.5)
        
    except Exception as e:
        print(f"Error al intentar resaltar: {e}")
        
        
        
# --- FUNCIÓN PRINCIPAL ACTUALIZADA (CON BANNER ROJO DE AUDITORÍA) ---
async def capturar_pagina(context, url, carpeta_salida, texto_a_resaltar=None):
    """
    Navega a la URL, RESALTA TEXTO (si se pide), inyecta la cinta roja de auditoría y toma captura.
    """
    page = await context.new_page()
    
    try:
        print(f"Navegando a: {url}")
        await page.goto(url, timeout=90000, wait_until="networkidle")    
        print("Esperando a que se estabilicen las animaciones visuales...")
        await asyncio.sleep(1.5)    
        
        # --- PASO 1: APLICAR RESALTADO ---
        if texto_a_resaltar:
            await resaltar_texto_en_pagina(page, texto_a_resaltar)

        # --- PASO 2: INYECCIÓN DE LA CINTA ROJA DE AUDITORÍA (VERSIÓN XL) ---
        ahora_texto = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        script_barra_roja = f"""
            const banner = document.createElement('div');
            banner.innerText = 'EVIDENCIA AUDITADA: {ahora_texto}';
            banner.style.position = 'absolute'; 
            banner.style.top = '0';
            banner.style.left = '0';
            banner.style.width = '100%';
            banner.style.zIndex = '2147483647';
            banner.style.backgroundColor = '#cc0000';
            banner.style.color = 'white';
            banner.style.textAlign = 'center';
            banner.style.fontSize = '36px';
            banner.style.padding = '25px 0';
            banner.style.letterSpacing = '2px';
            banner.style.fontWeight = 'bold';
            banner.style.fontFamily = 'Arial, sans-serif';
            banner.style.boxShadow = '0px 4px 15px rgba(0,0,0,0.6)';
            
            document.body.prepend(banner);
            document.body.style.marginTop = '100px';
            
            window.scrollTo(0, 0);
        """
        await page.evaluate(script_barra_roja)
        await asyncio.sleep(0.5) 

        # --- PASO 3: TOMAR LA CAPTURA ---
        dominio = urlparse(url).netloc.replace("www.", "")
        timestamp_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")
        sufijo = "_RESALTADO" if texto_a_resaltar else ""
        nombre_archivo = f"{dominio}{sufijo}_{timestamp_archivo}.png"
        
        ruta_completa = os.path.join(carpeta_salida, nombre_archivo)

        await page.screenshot(path=ruta_completa, full_page=True)
        print(f"Éxito: Captura guardada en -> {ruta_completa}\n")

    except Exception as e:
        print(f"Error crítico al capturar {url}: {e}\n")
        
    finally:
        await page.close()
        
        
async def motor_rpa():
    # --- CAMBIO IMPORTANTE EN LA LISTA ---
    # Ahora usamos una lista de DICCIONARIOS.
    # Cada diccionario tiene la URL y, opcionalmente, el texto a resaltar.
    lista_objetivos = [
        {
            "url": "https://www.ecija.com/",
            "highlight": "Un equipo global" 
        },
    ]
    
    # IMPORTANTE: Usa r"" antes de la ruta si estás en Windows para evitar errores
    carpeta_destino = r"C:\Users\GL553VD\Downloads\Ciencia de Datos_UV\3r Curso\2o Cuatri\MC\Tareas\LegalThon\7948_3454_7132_4993\LLMthon\capturas_sub"
    os.makedirs(carpeta_destino, exist_ok=True)
    
    print(f"Carpeta de destino preparada: {os.path.abspath(carpeta_destino)}")
    print("Iniciando motor RPA...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Cambia a False si quieres verlo trabajar
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})

        # Iteramos sobre nuestra nueva lista de objetivos
        for objetivo in lista_objetivos:
            target_url = objetivo.get("url")
            # Obtenemos el texto a resaltar, si no existe la clave, devuelve None
            texto_target = objetivo.get("highlight") 
            
            # Llamamos a la función actualizada
            await capturar_pagina(context, target_url, carpeta_destino, texto_a_resaltar=texto_target)
            
            await asyncio.sleep(random.uniform(1.5, 4.0))

        await browser.close()
        print("Proceso finalizado.")


if __name__ == "__main__":
    asyncio.run(motor_rpa())