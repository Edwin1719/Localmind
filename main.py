"""
Max — Agente de investigación local con wigolo + Ollama + LangGraph + Chainlit.

Arquitectura:
  Usuario → Chainlit UI → LangGraph Agent → Ollama (LLM local)
                                ↔ wigolo tools (search, fetch, research, cache, find_similar)
"""

import sqlite3
import os
from typing import Dict, Optional

import chainlit as cl
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver
from loguru import logger
from wigolo import Client

# ── Config ──────────────────────────────────────────────────────────
load_dotenv(".env")

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud")
CHECKPOINT_DB = "checkpoints.db"

# ── Wigolo client ───────────────────────────────────────────────────
# Conecta al daemon de wigolo en el puerto por defecto.
# Ejecuta 'wigolo serve' en una terminal separada antes de arrancar.
WIGOLO_BASE_URL = os.getenv("WIGOLO_BASE_URL", "http://127.0.0.1:3333")
_wigolo = Client(base_url=WIGOLO_BASE_URL)


# ── Response formatter (consistent JSON envelope) ───────────────────
class ResponseFormatter:
    @staticmethod
    def success(data, message="OK"):
        return {"status": "success", "message": message, "data": data}

    @staticmethod
    def error(message="Error", data=None):
        return {"status": "error", "message": message, "data": data}


# ── wigolo-powered tools ────────────────────────────────────────────

@tool
def buscar_en_web(
    query: str,
    max_results: int = 5,
    category: Optional[str] = None,
    time_range: Optional[str] = None,
    include_domains: Optional[str] = None,
    exclude_domains: Optional[str] = None,
) -> Dict:
    """Busca en la web usando 18 motores en paralelo con rank fusion y ML reranking.

    Usa esta herramienta cuando necesites buscar información actualizada,
    noticias, documentación, papers, o cualquier contenido web.

    Args:
        query: La consulta de búsqueda (usa palabras clave, no frases largas).
        max_results: Número máximo de resultados (1-20, default 5).
        category: Filtro por categoría: 'general', 'news', 'code', 'docs', 'papers', 'images'.
        time_range: Filtro temporal: 'day', 'week', 'month', 'year'.
        include_domains: Dominios a incluir separados por coma (ej: 'arxiv.org,github.com').
        exclude_domains: Dominios a excluir separados por coma.
    """
    try:
        params = {
            "query": query,
            "max_results": min(max_results, 20),
        }
        if category:
            params["category"] = category
        if time_range:
            params["time_range"] = time_range
        if include_domains:
            params["include_domains"] = [d.strip() for d in include_domains.split(",")]
        if exclude_domains:
            params["exclude_domains"] = [d.strip() for d in exclude_domains.split(",")]

        result = _wigolo.search(**params)
        return ResponseFormatter.success(result, f"Búsqueda completada: {query}")
    except Exception as e:
        logger.error(f"Error en búsqueda web: {e}")
        return ResponseFormatter.error(str(e))


@tool
def leer_pagina_web(
    url: str,
    render_js: bool = False,
    max_chars: int = 15000,
    section: Optional[str] = None,
) -> Dict:
    """Lee y extrae el contenido de una página web en formato markdown limpio.

    Usa esta herramienta cuando tengas una URL específica y necesites leer
    su contenido. Soporta SPAs, páginas con JavaScript, y extracción por secciones.

    Args:
        url: La URL completa de la página a leer.
        render_js: Si es True, usa un navegador real para páginas con JavaScript.
        max_chars: Máximo de caracteres a extraer (default 15000).
        section: Título de una sección específica a extraer (ej: 'Installation').
    """
    try:
        params = {
            "url": url,
            "max_chars": max_chars,
        }
        if render_js:
            params["render_js"] = True
        if section:
            params["section"] = section

        result = _wigolo.fetch(**params)
        return ResponseFormatter.success(result, f"Página leída: {url}")
    except Exception as e:
        logger.error(f"Error leyendo página: {e}")
        return ResponseFormatter.error(str(e))


@tool
def investigar_a_fondo(
    question: str,
    depth: str = "standard",
    include_domains: Optional[str] = None,
) -> Dict:
    """Investigación profunda multi-paso: descompone la pregunta, busca en paralelo,
    y sintetiza un reporte con citas.

    Usa esta herramienta para preguntas complejas que requieren múltiples fuentes
    y análisis. NO la uses para búsquedas simples (usa buscar_en_web).

    Args:
        question: La pregunta de investigación completa.
        depth: Profundidad: 'quick' (~15s), 'standard' (~40s, default), 'comprehensive' (~80s).
        include_domains: Dominios a incluir separados por coma.
    """
    try:
        params = {
            "question": question,
            "depth": depth,
        }
        if include_domains:
            params["include_domains"] = [d.strip() for d in include_domains.split(",")]

        result = _wigolo.research(**params)
        return ResponseFormatter.success(result, f"Investigación completada: {question}")
    except Exception as e:
        logger.error(f"Error en investigación: {e}")
        return ResponseFormatter.error(str(e))


@tool
def buscar_en_cache(query: str, url_pattern: Optional[str] = None) -> Dict:
    """Busca en el historial local de páginas ya visitadas. Instantáneo, sin consumir red.

    Usa esta herramienta ANTES de hacer una búsqueda web si crees que ya consultaste
    algo similar antes. Soporta búsqueda full-text con AND, OR, NOT, y frases exactas.

    Args:
        query: Búsqueda full-text (soporta 'AND', 'OR', 'NOT', \"frase exacta\").
        url_pattern: Patrón glob para filtrar por URL (ej: '*github.com*').
    """
    try:
        params = {"query": query}
        if url_pattern:
            params["url_pattern"] = url_pattern

        result = _wigolo.cache(**params)
        return ResponseFormatter.success(result, f"Cache consultada: {query}")
    except Exception as e:
        logger.error(f"Error en cache: {e}")
        return ResponseFormatter.error(str(e))


@tool
def encontrar_similar(
    url: Optional[str] = None,
    concept: Optional[str] = None,
    max_results: int = 5,
) -> Dict:
    """Encuentra páginas similares a una URL o concepto usando fusión híbrida
    (keyword + embeddings semánticos + búsqueda web).

    Útil para descubrir contenido relacionado, fuentes alternativas,
    o explorar un tema a partir de una buena página.

    Args:
        url: URL de referencia para encontrar páginas similares.
        concept: Concepto o tema para encontrar páginas relacionadas.
        max_results: Máximo de resultados (default 5, max 50).
    """
    try:
        if not url and not concept:
            return ResponseFormatter.error("Debes proporcionar 'url' o 'concept'")

        params = {"max_results": min(max_results, 50)}
        if url:
            params["url"] = url
        if concept:
            params["concept"] = concept

        result = _wigolo.find_similar(**params)
        return ResponseFormatter.success(result, "Búsqueda de similares completada")
    except Exception as e:
        logger.error(f"Error en find_similar: {e}")
        return ResponseFormatter.error(str(e))



@tool
def rastrear_sitio(
    url: str,
    max_pages: int = 10,
    strategy: str = "bfs",
    max_depth: int = 2,
    include_patterns: Optional[str] = None,
) -> Dict:
    """Explora un sitio web completo desde una URL semilla y extrae su contenido.

    Usa esta herramienta cuando necesites mapear la estructura de un sitio,
    extraer todas sus paginas, o recolectar contenido de un dominio entero.
    Para leer una sola pagina, usa leer_pagina_web.

    Args:
        url: URL semilla desde donde empezar el rastreo.
        max_pages: Maximo de paginas a visitar (default 10, max 50).
        strategy: Estrategia de rastreo: 'bfs' (anchura), 'dfs' (profundidad),
                  'sitemap' (usar sitemap.xml), 'map' (solo URLs, sin contenido).
        max_depth: Profundidad maxima desde la URL semilla (default 2).
        include_patterns: Patrones glob para filtrar URLs, separados por coma
                          (ej: '/docs/*,*/api/*').
    """
    try:
        params = {
            "url": url,
            "max_pages": min(max_pages, 50),
            "strategy": strategy,
            "max_depth": max_depth,
        }
        if include_patterns:
            params["include_patterns"] = [
                p.strip() for p in include_patterns.split(",")
            ]

        result = _wigolo.crawl(**params)
        return ResponseFormatter.success(result, f"Sitio rastreado: {url}")
    except Exception as e:
        logger.error(f"Error en rastreo: {e}")
        return ResponseFormatter.error(str(e))


@tool
def extraer_datos(
    url: str,
    mode: str = "auto",
    css_selector: Optional[str] = None,
    multiple: bool = False,
) -> Dict:
    """Extrae datos estructurados (tablas, listas, precios, metadatos) de una pagina web.

    Usa esta herramienta cuando necesites recolectar datos especificos de una pagina,
    no entender su contenido general. Para leer y comprender contenido, usa leer_pagina_web.

    Args:
        url: La URL completa de la pagina a extraer.
        mode: Modo de extraccion: 'auto' (deteccion automatica de tablas/listas),
              'css' (selector CSS manual).
        css_selector: Selector CSS para extraer elementos especificos (solo con mode='css').
                      Ej: 'table.releases', 'a[href]', '.price'.
        multiple: Si es True, extrae todas las coincidencias como array.
                  Si es False, extrae solo la primera.
    """
    try:
        params = {
            "url": url,
            "mode": mode,
            "multiple": multiple,
        }
        if css_selector:
            params["css_selector"] = css_selector

        result = _wigolo.extract(**params)
        return ResponseFormatter.success(result, f"Datos extraidos: {url}")
    except Exception as e:
        logger.error(f"Error en extraccion: {e}")
        return ResponseFormatter.error(str(e))


@tool
def comparar_contenido(
    url_a: str,
    url_b: str,
    granularidad: str = "section",
) -> Dict:
    """Compara el contenido de dos paginas web y muestra las diferencias.

    Usa esta herramienta cuando necesites saber que cambio entre dos versiones
    de documentacion, articulos, changelogs, o cualquier par de URLs.

    Args:
        url_a: URL de la primera pagina (version anterior o base).
        url_b: URL de la segunda pagina (version nueva o a comparar).
        granularidad: Nivel de detalle del diff: 'line', 'word', o 'section' (default).
    """
    try:
        result = _wigolo.diff(
            old={"url": url_a},
            new={"url": url_b},
            granularity=granularidad,
        )
        return ResponseFormatter.success(result, f"Comparacion completada")
    except Exception as e:
        logger.error(f"Error en comparacion: {e}")
        return ResponseFormatter.error(str(e))

# ── Agent assembly ──────────────────────────────────────────────────

tools = [
    buscar_en_web,
    leer_pagina_web,
    investigar_a_fondo,
    buscar_en_cache,
    encontrar_similar,
    rastrear_sitio,
    extraer_datos,
    comparar_contenido,
]

model = ChatOllama(model=OLLAMA_MODEL)

SYSTEM_PROMPT = """Eres Max, un asistente de investigación amigable, cálido y profesional.
Tienes acceso a herramientas avanzadas de inteligencia web que corren 100% local:

- buscar_en_web: Búsqueda multi-motor (18 motores) con resultados puntuados y citas.
- leer_pagina_web: Lee cualquier URL con navegador real para SPAs y JS.
- investigar_a_fondo: Pipeline de investigación multi-paso que descompone preguntas,
  busca fuentes en paralelo y sintetiza reportes con citas.
- buscar_en_cache: Tu memoria local — consultas previas son instantaneas y sin red.
- encontrar_similar: Descubre contenido relacionado a una URL o concepto.
- rastrear_sitio: Explora un sitio web completo desde una URL semilla. Extrae
  multiples paginas de documentacion, blogs, o sitios enteros con profundidad controlable.
- extraer_datos: Extrae datos estructurados (tablas, listas, precios) de una pagina.
  Usa mode='auto' para deteccion automatica, o CSS para elementos especificos.
- comparar_contenido: Compara dos paginas web y detecta diferencias. Util para
  seguir cambios en documentacion, changelogs, o versiones de un mismo recurso.

Reglas:
1. SIEMPRE usa las herramientas cuando necesites información de la web.
2. Para búsquedas rápidas usa buscar_en_web. Para preguntas complejas, investigar_a_fondo.
3. Antes de buscar algo nuevo, revisa buscar_en_cache por si ya lo tienes.
4. Cuando leas una página, cita la fuente.
5. Sé conversacional y cálido, pero riguroso con la información.
6. Si una herramienta falla, intenta otra estrategia — no te rindas.
7. Responde en el mismo idioma en que te preguntan."""

_conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
checkpointer = SqliteSaver(_conn)

agent = create_agent(
    model=model,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


# ── Chainlit UI handlers ────────────────────────────────────────────

THREAD_ID = "max-conversation"


@cl.on_chat_start
async def on_chat_start():
    """Initialize a new chat session — conversation persists across reloads."""
    logger.info(f"Session started — thread: {THREAD_ID}")

    await cl.Message(
        content="¡Hola! Soy **Max**, tu asistente de investigación local. "
        "Puedo buscar en la web, leer páginas, investigar a fondo, "
        "y recordar lo que ya consultamos — incluso si recargas la página. ¿En qué te ayudo hoy? 🔍"
    ).send()


@cl.on_message
async def on_message(msg: cl.Message):
    """Process each user message through the wigolo-powered agent."""
    final_answer = cl.Message(content="")

    try:
        for message_chunk, metadata in agent.stream(
            {"messages": [HumanMessage(content=msg.content)]},
            {"configurable": {"thread_id": THREAD_ID}},
            stream_mode="messages",
        ):
            if message_chunk.content and metadata.get("langgraph_node") == "model":
                await final_answer.stream_token(message_chunk.content)

    except Exception as e:
        logger.error(f"Agent error: {e}")
        final_answer.content = f"Lo siento, ocurrió un error: {str(e)}"

    await final_answer.send()


# ── Entry point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    run_chainlit(__file__)
