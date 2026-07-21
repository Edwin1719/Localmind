# ROADMAP — Wigolo_chain

Mejoras planeadas para el proyecto. Ordenadas por prioridad e impacto.

---

## Inmediato (próxima iteración)

### Persistencia multi-sesión real
**Estado:** Parcial — thread_id fijo (`"max-conversation"`)
**Problema:** Todas las conversaciones comparten el mismo thread. Si hay múltiples usuarios o sesiones simultáneas, se mezclan.
**Solución planeada:**
- Usar Chainlit user sessions con persistencia en SQLite/archivo
- Mapear `user_session.id` → `thread_id` persistente
- Al recargar, recuperar el thread_id anterior del mismo usuario
- Opción: integrar `cl.user_session` con el checkpointer de LangGraph

---

## Corto plazo

### Manejo de errores en herramientas
**Estado:** Básico — cada tool captura excepciones y devuelve error como string
**Mejoras:**
- Timeouts configurables por herramienta
- Reintentos automáticos en fallos transitorios (wigolo daemon caído)
- Health check del daemon antes de cada tool call
- Feedback visual en Chainlit durante tool calls largas (`research comprehensive`)

### Autenticación ligera
**Estado:** Sin auth — cualquiera en localhost:8000 puede usar el agente
**Mejoras:**
- Password via Chainlit config (ya soportado por el framework)
- OAuth2 minimal (GitHub/Google) para entornos compartidos

### Customización de herramientas
**Estado:** 8 herramientas wigolo expuestas (de 10 disponibles)
**Completado:** ✅ `rastrear_sitio` (crawl), `extraer_datos` (extract), `comparar_contenido` (diff)
**Pendiente:** `recolectar_datos` (agent), `monitorear_cambios` (watch)
**Mejoras:**
- UI para habilitar/deshabilitar herramientas por sesión
- Herramientas custom via archivo de configuración (YAML/TOML)

---

## Mediano plazo

### Historial de conversaciones
**Estado:** SQLite checkpointer guarda estado interno de LangGraph
**Mejoras:**
- UI de historial: ver, buscar, reanudar conversaciones anteriores
- Exportar conversaciones a Markdown/JSON
- Eliminar conversaciones antiguas

### Observabilidad
**Estado:** Logs básicos con loguru
**Mejoras:**
- Dashboard de uso: queries por herramienta, latencia, tokens consumidos
- Trazas de cada tool call visibles en la UI (ya parcialmente con `cot=full`)
- Métricas de calidad: cuántas búsquedas retornaron resultados vs vacías

### Embeddings locales para cache semántico
**Estado:** wigolo maneja el cache con SQLite + vectores internamente
**Mejoras:**
- Exponer búsqueda semántica en el cache como herramienta adicional
- Permitir al agente hacer preguntas como "¿qué hemos aprendido sobre X?"

---

## Largo plazo

### Agentes especializados (multi-agente)
**Estado:** Un solo agente "Max" monolítico
**Mejoras:**
- Arquitectura multi-agente: researcher, writer, reviewer, fact-checker
- Orquestación con LangGraph sub-graphs
- Cada agente con su propio conjunto de herramientas

### Despliegue Docker
**Estado:** Solo local con Python + Node
**Mejoras:**
- Dockerfile multi-stage: Python app + wigolo + Ollama (opcional)
- docker-compose con todos los servicios
- Health checks y reinicio automático

### Modo headless / API
**Estado:** Solo interfaz Chainlit
**Mejoras:**
- API REST alongside Chainlit para integraciones
- Modo CLI: `python main.py --query "busca X"`
- Webhook para recibir preguntas y devolver respuestas

---

## Notas técnicas

### Deuda actual
1. **Thread fijo** — `THREAD_ID = "max-conversation"` es temporal. Migrar a multi-sesión real.
2. **Cobertura de herramientas** — 8 de 10 herramientas de wigolo expuestas. Pendientes: `recolectar_datos` (agent) y `monitorear_cambios` (watch).
3. **Configuración dispersa** — Centralizar toda la config (modelo, puertos, timeouts) en un solo archivo YAML/TOML.
4. **Error handling en el launcher** — `start.py` no reintenta si wigolo falla después de iniciar.

### Decisiones de arquitectura
- **wigolo vía REST (no MCP):** el SDK de Python usa REST al daemon local. Es más simple que el cliente MCP para este caso de uso. Si en el futuro necesitamos las 10 herramientas de wigolo sin wrappers manuales, considerar migrar a `wigolo-langchain`.
- **SqliteSaver (no Postgres):** Para uso local monousuario, SQLite es suficiente. Si el proyecto escala a multi-usuario, migrar a `PostgresSaver`.
- **Ollama (no APIs cloud):** Por privacidad y costo cero. Si se necesita mayor calidad, agregar `ChatOpenAI` / `ChatAnthropic` como fallback condicional.
