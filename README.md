# 🚀 TP-Benchmark-AI: Automatización de Precios de Transferencia

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red)
![Playwright](https://img.shields.io/badge/RPA-Playwright-green)
![LLM](https://img.shields.io/badge/AI-OpenAI%2FGemini-orange)

> **Solución ganadora para el Datathon 2024.**
> Automatización inteligente del proceso de Benchmark de Precios de Transferencia mediante Web Scraping avanzado, Análisis con LLMs y Generación de Evidencias Auditables.

---

## 📋 Contexto del Negocio

El proceso de **Benchmark de Precios de Transferencia** requiere validar manualmente cientos de empresas para determinar si son comparables al cliente objetivo. Esto implica verificar:
1.  **Independencia:** ¿Es parte de un grupo empresarial?
2.  **Función:** ¿Es manufacturera o prestadora de servicios?
3.  **Comparabilidad:** ¿Ofrece los mismos servicios que nuestro cliente?

**TP-Benchmark-AI** reduce este proceso de semanas a minutos, generando un Excel auditado con **evidencias gráficas (capturas de pantalla)** y razonamiento lógico detallado.

---

## 🌟 Características Clave (The Winning Features)

* **🛡️ Navegador Fantasma (Anti-Junk):** Detección automática de "dominios en venta" o páginas caídas para ahorrar costes de API. [Revisar sitemap.xml de la empresa para encontrar páginas que expliquen el funcionamiento de la empresa]
* **🧠 Deep Context Analysis:** El LLM no solo lee, *entiende*. Clasifica empresas basándose en análisis semántico multilingüe.
* **📸 Evidencia Forense:** Generación automática de Screenshots con **Time-Stamping**.
* **✨ Smart Highlighting:** Inyección de CSS en tiempo real para **resaltar en rojo/amarillo** la frase exacta en la web que causó el rechazo (ej. "Subsidiary of...").
* **🚦 Semáforo de Confianza:** El sistema marca en amarillo las filas donde la IA duda (<70% confianza) para revisión humana.
* **🔗 Trazabilidad Total:** El Excel de salida incluye hipervínculos locales directos a la evidencia gráfica.

---


## 🌟 Crear entorno virtual

En anaconda prompt:

* mamba create -n tp-benchmark python=3.11 -y
* mamba activate tp-benchmark

---

## 👨‍💻 Guía de Desarrollo & Contratos de API (Squad Roles)

Para trabajar en paralelo sin romper el código del compañero, cada integrante debe respetar estrictamente los siguientes formatos de entrada y salida (Interfaces).

---

### 🕷️ Rol 1: The Hunter (Web Scraping)
**Archivo:** `src/modules/scraper.py`
**Responsabilidad:** Navegación Headless, Extracción de texto y Capturas con Highlighting.

Debe implementar una clase `Scraper` con estas dos funciones independientes:

#### A. Función `extract_text(url)`
Extrae el texto limpio para enviarlo a la IA (Fase 1).
* **Input:** `url` (str)
* **Output:** Diccionario (JSON)

{
    "status": 200,            // Código HTTP (404, 500, etc.)
    "is_junk": false,         // True si detecta "Domain for sale", "GoDaddy", etc.
    "text_content": "Texto completo y limpio de la web...",
    "error_msg": null         // String descriptivo si hubo error
}


## 👨‍💻 Guía de Desarrollo & Contratos de API (Squad Roles)

Para trabajar en paralelo sin romper el código del compañero, cada integrante debe respetar estrictamente los siguientes formatos de entrada y salida (Interfaces).

#### B. Función take_screenshot(url, text_to_highlight)
Vuelve a navegar para sacar la "Foto de la Evidencia" (Fase 2).

* **Input**: url (str), text_to_highlight (str - Frase corta identificada por el LLM).

* **Lógica**: Buscar la frase en el DOM -> Inyectar CSS (Borde rojo/amarillo) -> Sacar foto.

* **Output**: String (Path relativo a la imagen guardada).
"evidence/20231027_empresa_X.png"

---

### 🧠 Rol 2: The Analyst (LLM Engine)
**Archivo:** `src/modules/llm_engine.py`
**Responsabilidad:** Prompt Engineering y Parsing de JSON.

#### A. Función `analyze(text, client_description)`
* **Input**: text (str - viene del scraper), client_description (str - viene del usuario).

* **Output**: Diccionario JSON plano (Estricto).

{
    "is_group": boolean,          // True si se debe rechazar por ser Grupo
    
    "is_manufacturer": boolean,   // True si se debe rechazar por Manufactura
    
    "service_match": boolean,     // True si los servicios coinciden
    
    "reasoning": "Explicación breve de 1 línea.",
    
    "evidence_quote": "Subsidiary of Omega Group",   // <--- VITAL: La frase exacta para el Highlighting
    
    "confidence_score": 95        // Entero 0-100
}

---

### 🏗️ Rol 3: The Architect (Orchestration & UI)
**Archivo:** `src/app.py` y `src/core/orchestrator.py`
**Responsabilidad:**

* Unir las piezas (Scraper -> LLM -> Scraper -> Excel).
* Interfaz visual en Streamlit.

---

## 📂 Estructura del Proyecto (Clean Architecture)

El proyecto sigue una arquitectura modular para desacoplar la interfaz, la lógica de negocio y los servicios externos.

```text
transfer-pricing-benchmark/
│
├── .env                     # Variables de entorno (API Keys)
├── .gitignore               # Exclusiones de git
├── requirements.txt         # Dependencias del proyecto
├── README.md                # Documentación
│
├── data/                    # Almacenamiento temporal de datos
│   ├── input/               # Lugar para "Matriz AR en blanco.xlsx"
│   └── output/              # Destino de "Matriz AR trabajada.xlsx"
│
├── evidence/                # Repositorio de capturas de pantalla
│   └── YYYYMMDD_HHMM/       # Subcarpetas por ejecución (Timestamp)
│
├── src/                     # Código Fuente
│   ├── __init__.py
│   ├── app.py               # Entry Point (Streamlit UI)
│   │
│   ├── core/                # Lógica de Negocio Central
│   │   ├── __init__.py
│   │   ├── orchestrator.py  # Controlador del flujo (UI <-> Scraper <-> LLM)
│   │   └── config.py        # Configuraciones globales y constantes
│   │
│   ├── modules/             # Servicios Independientes
│   │   ├── __init__.py
│   │   ├── excel_handler.py # Pandas/Openpyxl (Lectura/Escritura/Estilos)
│   │   ├── scraper.py       # Playwright (Nav, Screenshot, Highlighting)
│   │   └── llm_engine.py    # Integración API (Prompting & Parsing)
│   │
│   └── utils/               # Utilidades Transversales
│       ├── __init__.py
│       ├── logger.py        # Sistema de logging centralizado
│       └── helpers.py       # Limpieza de strings, fechas, validaciones
│
└── tests/                   # Unit tests y scripts de prueba rápida
