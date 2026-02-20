import sys
import json
import time
from urllib.parse import urljoin
from datetime import datetime
import nest_asyncio
from playwright.sync_api import sync_playwright

nest_asyncio.apply()

# --- FUNCIONES DE UTILIDAD VISUAL (RPA) ---

def inject_audit_banner(page):
    """Inyecta una cinta roja de auditoría en la parte superior."""
    ahora_texto = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    js = f"""
        const banner = document.createElement('div');
        banner.innerText = 'EVIDENCIA AUDITADA: {ahora_texto}';
        banner.style.position = 'fixed'; 
        banner.style.top = '0';
        banner.style.left = '0';
        banner.style.width = '100%';
        banner.style.zIndex = '2147483647';
        banner.style.backgroundColor = '#cc0000';
        banner.style.color = 'white';
        banner.style.textAlign = 'center';
        banner.style.fontSize = '24px';
        banner.style.fontWeight = 'bold';
        banner.style.padding = '10px 0';
        banner.style.boxShadow = '0px 4px 15px rgba(0,0,0,0.6)';
        document.body.prepend(banner);
        document.body.style.marginTop = '60px'; 
    """
    try:
        page.evaluate(js)
    except:
        pass
    
def highlight_text_laser(page, text):
    """Subraya el texto específico ignorando diferencias menores de formato."""
    if not text or len(text) < 5: return # Evitamos resaltar palabras sueltas como "de" o "la"
    
    # Limpieza extrema del texto para evitar que rompa el JS
    text = text.replace('"', '').replace("'", "").replace("\n", " ").strip()

    js_script = r"""
    (textToHighlight) => {
        const escapeRegExp = (string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        let escapedText = escapeRegExp(textToHighlight);
        
        // Regex ultra-flexible: permite cualquier cantidad de espacios o saltos entre palabras
        let flexibleRegexString = escapedText.split(/\s+/).join('(?:\\s|&nbsp;|<[^>]+>)*');
        const regex = new RegExp(`(${flexibleRegexString})`, 'gi');

        function highlightNode(node) {
            if (node.nodeType === 3) { 
                const match = regex.exec(node.data);
                if (match) {
                    const span = document.createElement('span');
                    span.className = 'rpa-highlight-mark';
                    span.style.cssText = 'background-color: yellow !important; color: black !important; outline: 4px solid red !important; font-weight: bold !important; box-shadow: 0 0 15px rgba(255,0,0,0.5) !important; border-radius: 4px; padding: 2px;';
                    
                    const middle = node.splitText(match.index);
                    middle.splitText(match[0].length);
                    const newNode = middle.cloneNode(true);
                    
                    span.appendChild(newNode);
                    middle.parentNode.replaceChild(span, middle);
                    return true; 
                }
            } else if (node.nodeType === 1 && node.childNodes && !/(script|style|textarea)/i.test(node.tagName)) {
                for (let i = 0; i < node.childNodes.length; i++) {
                    if (highlightNode(node.childNodes[i])) return true;
                }
            }
            return false;
        }

        const found = highlightNode(document.body);
        if (found) {
            const el = document.querySelector('.rpa-highlight-mark');
            if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
        }
        return found;
    }
    """
    try:
        page.evaluate(js_script, text)
    except:
        pass
    

# --- MODO 1: SCRAPING (Tu lógica original mejorada) ---

def run_scrape(url):
    headless = True
    timeout = 20000
    
    result = {
        "status": 0,
        "is_junk": False,
        "text_content": "",
        "error_msg": None,
        "url_evidencia": url # Por defecto, la evidencia es la URL de entrada
    }
    
    keywords_junk = [
        "domain for sale", "comprar este dominio", "parked free", "godaddy", 
        "sedo", "hugedomains", "namecheap", "this domain is available", 
        "buy this domain", "dominio a la venta", "site under construction",
        "coming soon", "renew now"
    ]
    keywords_nav = ["servicios", "services", "about", "nosotros", "grupo", "group", "quienes somos"]

    # Limpieza URL
    if not url or str(url) == 'nan': 
        return {"status": 0, "is_junk": False, "text_content": "", "error_msg": "URL Nula"}
    url = str(url).strip()
    if not url.startswith('http'): url = f'https://{url}'

    result["url_evidencia"] = url

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            page = context.new_page()

            # 1. HOME
            try:
                response = page.goto(url, timeout=timeout, wait_until='domcontentloaded')
                page.wait_for_timeout(1500)
                status = response.status if response else 0
                result["status"] = status
            except Exception as e:
                browser.close()
                result["error_msg"] = "Timeout/Error Conexión"
                return {"status": 0, "is_junk": False, "text_content": "", "error_msg": "Timeout/Error Conexión"}

            if status >= 400:
                browser.close()
                result["error_msg"] = f"HTTP {status}"
                return {"status": status, "is_junk": False, "text_content": "", "error_msg": f"HTTP {status}"}

            # 2. JUNK CHECK
            title = page.title()
            body = page.locator('body').inner_text()
            full_text = (title + " " + body[:1000]).lower()
            
            for kw in keywords_junk:
                if kw in full_text:
                    browser.close()
                    result["status"] = 200
                    result["is_junk"] = True
                    result["text_content"] = f"TITULO: {title}\nTEXTO: {body[:500]}..."
                    result["error_msg"] = f"Junk detectado: {kw}"
                    return result

            content = f"--- HOME ({title}) ---\n{body}\n\n"

            # 3. DEEP SCRAPING
            try:
                links = page.get_by_role("link").all()
                target = None
                for link in links[:50]:
                    try:
                        href = link.get_attribute('href')
                        txt = link.inner_text().lower()
                        if href and any(k in txt for k in keywords_nav):
                            target = href
                            break
                    except: continue
                
                if target_url:
                    # Construcción URL absoluta robusta
                    if not target_url.startswith('http'):
                        base = url.rstrip('/')
                        # Si target empieza con /, quitamos la base y concatenamos, o manejamos la unión
                        if target_url.startswith('/'):
                            # Lógica simple de unión: base + target
                            # Ojo: si base tiene path, esto podría fallar, pero para home suele valer
                            # Mejor usar la url base del objeto page por si hubo redirección
                            current_url_base = page.url.rstrip('/') 
                            # Si es root relative
                            import urllib.parse
                            target_url = urllib.parse.urljoin(page.url, target_url)
                        else:
                            target_url = f"{base}/{target_url}"
                    
                    # Navegamos
                    page.goto(target_url, timeout=20000, wait_until='domcontentloaded')
                    
                    # Espera robusta para carga de JS
                    page.wait_for_timeout(2000)
                    
                    secondary_text = page.locator('body').inner_text()
                    
                    # Validación: Si hay suficiente texto, nos quedamos esta URL como evidencia
                    if len(secondary_text) > 100:
                        content += f"--- EXTRA ({target_url}) ---\n{secondary_text}"
                        result["url_evidencia"] = page.url # ACTUALIZAMOS LA EVIDENCIA
                    else:
                        content += "\n(Sección extra visitada pero con poco texto)"
                        
            except Exception as e:
                # No fallamos todo el proceso si falla el deep scraping, solo lo logueamos en el texto
                content += f"\n[Error en navegación extra: {str(e)}]"

            browser.close()
            result["text_content"] = ' '.join(content.split()) # Limpieza de espacios
            return result

    except Exception as e:
        result["status"] = 500
        result["error_msg"] = str(e)
        return result
    
    
# --- MODO 2: SCREENSHOT (Nueva Funcionalidad Fusionada) ---

def take_screenshot(config):
    url = config.get("url")
    text_to_highlight = config.get("text")
    output_path = config.get("path")
    
    response = {"success": False, "path": ""}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080}) 
            page = context.new_page()
            
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000) 
            except:
                browser.close()
                return response 

            # APLICAMOS LA MAGIA VISUAL
            if text_to_highlight:
                highlight_text_laser(page, text_to_highlight)
                page.wait_for_timeout(500)

            inject_audit_banner(page)
            page.wait_for_timeout(500)
            
            page.screenshot(path=output_path, full_page=True)
            
            response["success"] = True
            response["path"] = output_path
            
            browser.close()
            return response

    except Exception as e:
        return response


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        # Si el argumento es "screenshot", esperamos un JSON en el 2º argumento
        if arg == "screenshot":
            try:
                config_json = sys.argv[2]
                config = json.loads(config_json)
                print(json.dumps(take_screenshot(config)))
            except Exception as e:
                print(json.dumps({"success": False, "error": str(e)}))
        
        # Si no, asumimos que es una URL normal (Modo Scrape Legacy)
        else:
            print(json.dumps(run_scrape(arg)))