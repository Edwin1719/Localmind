<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/node-20-green?logo=node.js" alt="Node 20">
  <img src="https://img.shields.io/badge/license-MIT-2563eb" alt="MIT">
  <img src="https://img.shields.io/badge/costo-$0-success" alt="$0">
  <img src="https://img.shields.io/badge/privacidad-100%25%20local-brightgreen" alt="100% local">
</p>

# localmind

**Agente de investigación local-first. Búsqueda multi-motor, investigación profunda y memoria persistente — cero API keys, cero costos.**

`localmind` es un asistente de IA que investiga la web por vos. Todo corre en tu máquina: las búsquedas no pasan por servidores externos, el cache de conocimiento es tuyo, y no hay suscripción ni metered billing. Un solo comando lo levanta todo.

---

## ¿Por qué localmind?

| Problema | Solución de localmind |
|---|---|
| Las APIs de búsqueda cobran por consulta | **18 motores de búsqueda, $0 por query** — wigolo habla directo con los buscadores, sin intermediarios |
| Tus datos de investigación salen de tu máquina | **100% local** — búsquedas, cache, embeddings y modelos corren en `~/.wigolo/` |
| Los agentes "gratis" pierden la memoria al cerrar | **SQLite** — conversaciones y conocimiento persisten entre sesiones |
| Configurar un agente requiere 5 terminales | **`python start.py`** — el launcher levanta Ollama, wigolo y Chainlit, y los apaga al salir |
| Modelos pequeños fallan en tool-calling | **gpt-oss:20b-cloud** (gratuito vía Ollama registry) — 20B parámetros, razonamiento multi-paso confiable |

---

## Comparación con alternativas

| | localmind | Open WebUI + SearXNG | AnythingLLM | ChatGPT Plus | Perplexity Pro |
|---|---|---|---|---|---|
| **Búsqueda web** | 18 motores | 1 motor (SearXNG) | APIs cloud ($$$) | Built-in | Built-in |
| **Investigación profunda** | ✅ Pipeline multi-paso | ❌ | ❌ | ✅ Deep Research | ✅ Pro Search |
| **Fetch con browser real** | ✅ SPAs, JS, anti-bot | ❌ | Parcial | ❌ | ❌ |
| **Cache local** | ✅ SQLite + vectores | ❌ | ✅ | ❌ | ❌ |
| **Costo mensual** | **$0** | $0 (hosting) | Variable | $20 | $20 |
| **API keys requeridas** | **Ninguna** | Ninguna | OpenAI/Anthropic | N/A | N/A |
| **Privacidad de búsquedas** | ✅ Local | ✅ Local | ❌ Cloud | ❌ Cloud | ❌ Cloud |
| **Modelo LLM** | gpt-oss:20b (gratis) | Cualquiera | Cualquiera | GPT-4o | Propietario |
| **Instalación** | 3 comandos | Docker | Docker | Navegador | Navegador |
| **Multi-sesión** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Open source** | ✅ MIT | ✅ | ✅ | ❌ | ❌ |

---

## Arquitectura

```
┌──────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Usuario │────▶│   Chainlit   │────▶│  LangGraph      │────▶│  Ollama (LLM)    │
│          │     │  (UI web)    │     │  (orquestador)  │     │  gpt-oss:20b     │
└──────────┘     └──────────────┘     └────────┬────────┘     └──────────────────┘
                                               │
                                      ┌────────┴────────┐
                                      │   wigolo tools   │
                                      │  (REST daemon)   │
                                      └──────┬──────────-┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │           │            │           │            │
                    ▼           ▼            ▼           ▼            ▼
              ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐
              │ search  │ │ fetch   │ │ research │ │ cache   │ │similar   │
              │18 motores│ │HTTP→Brw│ │multi-paso│ │SQLite   │ │keyword+  │
              │rank fus. │ │stealth  │ │+citas    │ │+vectores│ │embed+web │
              └─────────┘ └─────────┘ └──────────┘ └─────────┘ └──────────┘
```

### Flujo de una consulta

1. **Chainlit** recibe el mensaje del usuario
2. **LangGraph** decide si responde directo o invoca herramientas
3. **wigolo** ejecuta la herramienta (search, fetch, research, cache, find_similar)
4. **Ollama** sintetiza la respuesta con los resultados
5. **Chainlit** streamea la respuesta token por token al chat

Todo el estado de la conversación se persiste en **SQLite** vía `SqliteSaver`. Si recargás la página, la conversación sigue donde la dejaste.

---

## Stack tecnológico

| Capa | Tecnología | Rol |
|---|---|---|
| **UI** | [Chainlit 2.6](https://docs.chainlit.io/) | Interfaz de chat web con streaming |
| **Orquestador** | [LangGraph 1.0](https://langchain-ai.github.io/langgraph/) | Grafo de decisiones: qué herramienta usar, cuándo responder |
| **Framework** | [LangChain 1.0](https://python.langchain.com/) | `create_agent` + tool binding |
| **LLM** | [Ollama](https://ollama.com/) + `gpt-oss:20b-cloud` | Modelo cloud gratuito, 20B parámetros |
| **Inteligencia web** | [wigolo 0.2.1](https://github.com/KnockOutEZ/wigolo) | 18 motores de búsqueda, fetch con browser, research pipeline |
| **Persistencia** | SQLite + `SqliteSaver` | Conversaciones y cache sobreviven reinicios |
| **Launcher** | `start.py` (~200 líneas) | Detección automática de Node.js, levanta y apaga servicios |

---

## Herramientas del agente

### `buscar_en_web`
Búsqueda multi-motor con 18 engines en paralelo, rank fusion y ML reranking.

**Filtros disponibles:**
- `category`: `general`, `news`, `code`, `docs`, `papers`, `images`
- `time_range`: `day`, `week`, `month`, `year`
- `include_domains` / `exclude_domains`: filtrar por dominios
- `max_results`: 1–20

**Ejemplo:** *"Busca papers sobre transformers, solo arxiv.org, último mes"*

---

### `leer_pagina_web`
Fetch inteligente con router que escala de HTTP simple a navegador real.

**Capacidades:**
- Renderizado JS automático (SPAs, React, Vue)
- Extracción por sección (`section="Installation"`)
- Anti-bot challenge evasion
- PDF parsing

**Ejemplo:** *"Lee la sección Quickstart de fastapi.tiangolo.com"*

---

### `investigar_a_fondo`
Pipeline de investigación multi-paso completo.

```
Pregunta → descomposición en sub-queries → búsqueda paralela
→ fetch de fuentes → validación → síntesis con citas
```

**Profundidades:**
| Nivel | Tiempo | Sub-queries | Fuentes |
|---|---|---|---|
| `quick` | ~15s | 2 | 5–8 |
| `standard` | ~40s | 4 | 12–15 |
| `comprehensive` | ~80s | 7 | 20–25 |

**Ejemplo:** *"Investiga a fondo las diferencias entre LangGraph, CrewAI y AutoGen"*

---

### `buscar_en_cache`
Memoria local de todo lo que wigolo ya ha visto. Instantáneo, sin consumir red.

- Búsqueda full-text con `AND`, `OR`, `NOT`, `"frase exacta"`
- Filtro por patrón glob de URL (`*github.com*`)

**Ejemplo:** *"¿Qué tenemos guardado sobre Python asyncio?"*

---

### `encontrar_similar`
Descubrimiento de contenido relacionado por fusión híbrida (keyword + embeddings semánticos + búsqueda web).

**Ejemplo:** *"Encuentra páginas similares a docs.python.org/3/"*

### `rastrear_sitio`
Explora un sitio web completo desde una URL semilla. Control de profundidad, páginas máximas y filtros por patrón glob.

**Estrategias:**
- `bfs` (anchura, default), `dfs` (profundidad), `sitemap` (sitemap.xml), `map` (solo URLs)

**Ejemplo:** *"Rastrea docs.python.org/3/library/ con profundidad 2 y máximo 10 páginas"*

---

### `extraer_datos`
Extrae datos estructurados (tablas, listas, precios, metadatos) de una página web. Modo `auto` detecta la estructura automáticamente; modo `css` permite selectores manuales.

**Ejemplo:** *"Extrae todas las funciones de docs.python.org/3/library/functions.html"*

---

### `comparar_contenido`
Compara dos páginas web y detecta diferencias a nivel de línea, palabra o sección. Ideal para seguir cambios en documentación, changelogs o versiones de un mismo recurso.

**Ejemplo:** *"Compara las release notes de Django 5.0 y 5.1"*

---

## Instalación

### Requisitos previos

| Componente | Versión | Verificación |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Node.js | **v20** (no v22) | `node --version` |
| Ollama | cualquier | `ollama list` |
| Git | cualquier | `git --version` |

### 1. Clonar e instalar dependencias Python

```powershell
git clone https://github.com/TU_USUARIO/localmind.git
cd localmind
pip install -r requirements.txt
```

### 2. Node.js v20

Si estás en Windows con Node v22+, instalá nvm-windows y cambiá a v20:

```powershell
winget install CoreyButler.NVMforWindows
# Cerrá y reabrí la terminal
nvm install 20
nvm use 20
```

### 3. Instalar wigolo

```powershell
npm install -g wigolo
wigolo init          # ~1.5 GB, solo la primera vez
```

### 4. Modelo de Ollama

```powershell
ollama pull gpt-oss:20b-cloud
```

### 5. Configurar (opcional)

```powershell
copy .env.example .env
```

### 6. Ejecutar

```powershell
python start.py
```

Abrí `http://localhost:8000`. **Ctrl+C** detiene todo limpiamente.

---

## Estructura del proyecto

```
localmind/
├── main.py                  # Agente principal (~400 líneas, 8 herramientas)
├── start.py                 # Launcher multi-servicio
├── requirements.txt         # 7 dependencias
├── pyproject.toml           # Config pytest + proyecto
├── .env.example             # Modelo Ollama + wigolo LLM provider
├── chainlit.md              # Pantalla de bienvenida de Max
├── .chainlit/
│   └── config.toml          # UI: nombre, tema, CoT
├── tests/
│   ├── conftest.py           # Fixtures y mock de wigolo
│   ├── unit/                 # 62 tests (formatter, tools, launcher)
│   ├── integration/          # Daemon, checkpointer, agente
│   └── e2e/                  # Flujos de chat, edge cases
├── ROADMAP.md               # Plan de mejoras y deuda técnica
├── LICENSE                   # MIT
└── README.md                 # Este archivo
```

---

## Tests

```powershell
# Unitarios (sin servicios externos)
pytest tests/unit/ -v               # 62 tests

# Integración (requiere wigolo serve)
pytest tests/integration/ -v

# End-to-end (requiere stack completo)
pytest tests/e2e/ -v

# Todo
pytest -v
```

---

## Solución de problemas

| Error | Causa | Solución |
|---|---|---|
| `wigolo CLI not found` | `npm install -g wigolo` no se ejecutó | `npm install -g wigolo` |
| `AssignProcessToJobObject: (87)` | Warning no-fatal de Windows | Ignorar — es cosmético |
| `SyntaxError` en `@google/genai` | Node v22 | `nvm use 20` |
| `ERR_UNSUPPORTED_DIR_IMPORT` en `zod/v3` | Caché corrupta de npx | `rmdir /s /q %LOCALAPPDATA%\npm-cache\_npx` |
| `could not connect to wigolo at 127.0.0.1:3333` | Daemon no corriendo | Usá `python start.py` (lo levanta solo) |
| Modelo no encontrado | No descargado en Ollama | `ollama pull gpt-oss:20b-cloud` |
| Tests de integración skippeados | No hay daemon | `wigolo serve` en otra terminal |

---

## Roadmap

Ver [ROADMAP.md](ROADMAP.md) para el plan completo. Prioridades:

1. Multi-sesión real (thread_id por usuario)
2. Docker + docker-compose
3. Exponer herramientas restantes de wigolo (`crawl`, `extract`, `agent`, `diff`, `watch`)
4. Health check del daemon con reintentos automáticos
5. Dashboard de uso y observabilidad

---

## Licencia

MIT © 2026 Edwin Quintero — ver [LICENSE](LICENSE) para detalles.

---

<p align="center">
  <sub>Construido con ❤️ usando <a href="https://github.com/KnockOutEZ/wigolo">wigolo</a>, <a href="https://ollama.com/">Ollama</a>, <a href="https://langchain-ai.github.io/langgraph/">LangGraph</a> y <a href="https://docs.chainlit.io/">Chainlit</a></sub>
</p>
