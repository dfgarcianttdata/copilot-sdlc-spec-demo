import asyncio
import sys

from pathlib import Path
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType
from copilot.session import PermissionHandler

from sdlc_demo.prompts import DEMO_IDEA, SYSTEM_PROMPT
from sdlc_demo.tools import (
    architecture_llm_design,
    generate_technical_doc,
    save_trace,
    security_precheck,
    validate_spec,
    wikipedia_mcp_context,
)

from sdlc_demo.session_store import (
    build_continuation_context,
    generate_session_id,
    save_session_record,
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def safe_write(text: str):
    if text is None:
        return

    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except UnicodeEncodeError:
        safe_text = text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        print(safe_text, end="", flush=True)




async def run_demo(user_idea: str, existing_session_id: str | None = None):
    
    
    demo_session_id = existing_session_id or generate_session_id()
    previous_context = ""

    if existing_session_id:
        previous_context = build_continuation_context(existing_session_id)

    client = CopilotClient()
    await client.start()

    wikipedia_mcp_server = {
        "wikipedia_context": {
            "command": str(Path(sys.executable).parent / "wikipedia-mcp.exe"),
            "args": [
                "--transport",
                "stdio",
                "--language",
                "es",
            ],
        }
    }

    try:
        session = await client.create_session(
            on_permission_request=PermissionHandler.approve_all,
            streaming=True,
            tools=[
                validate_spec,
                save_trace,
                security_precheck,
                architecture_llm_design,
                generate_technical_doc,
                wikipedia_mcp_context,
            ],
            mcp_servers= wikipedia_mcp_server,
            custom_agents=[
                {
                    "name": "security_reviewer",
                    "display_name": "Security Reviewer",
                    "description": (
                        "Subagente especializado en revisar especificaciones SDLC "
                        "desde el punto de vista de seguridad, trazabilidad, control, "
                        "autenticación, autorización y riesgos regulatorios."
                    ),
                    "tools": ["security_precheck"],
                    "prompt": """
                    Eres un subagente especializado en seguridad y control para un SDLC bancario regulado.

                    Alcance estricto:
                    - Usa únicamente la información de la especificación que recibas.
                    - No explores repositorios.
                    - No inspecciones archivos.
                    - No ejecutes comandos.
                    - No busques contexto adicional.
                    - No inventes normativa concreta.
                    - No uses emojis ni iconos Unicode.

                    Tu misión:
                    - Revisar riesgos de seguridad, auditoría, trazabilidad, autenticación y autorización.
                    - Usar la tool security_precheck cuando tengas información suficiente.
                    - Devolver hallazgos claros, accionables y priorizados.
                    - Responder siempre en español.
                    """,
                },
                {
                    "name": "architecture_designer",
                    "display_name": "Architecture Designer",
                    "description": (
                        "Subagente especializado en proponer una arquitectura técnica inicial "
                        "para iniciativas SDLC. Este subagente usa un LLM externo configurado "
                        "mediante la tool architecture_llm_design."
                    ),
                    "tools": ["architecture_llm_design"],
                    "prompt": """
                    Eres un subagente arquitecto técnico para un SDLC bancario regulado.

                    Alcance estricto:
                    - Usa únicamente la especificación recibida.
                    - No explores repositorios.
                    - No inspecciones archivos.
                    - No ejecutes comandos.
                    - No busques contexto externo.
                    - No inventes sistemas internos concretos.
                    - No des por aprobada la arquitectura; genera una propuesta inicial.
                    - No uses emojis ni iconos Unicode.

                    Tu misión:
                    - Proponer una arquitectura técnica inicial.
                    - Identificar componentes lógicos.
                    - Identificar integraciones necesarias.
                    - Detectar riesgos arquitectónicos.
                    - Usar obligatoriamente la tool architecture_llm_design cuando tengas información suficiente.
                    - Indicar que la propuesta de arquitectura se ha generado con el LLM externo de arquitectura configurado.
                    - Al devolver tu resultado, indica explícitamente:
                    "Modelo/proveedor utilizado: LLM externo OpenAI-compatible configurado en .env"
                    - Indica también:
                    "Tool utilizada: architecture_llm_design"
                    - Responder siempre en español.
                    """,
                },
                {
                    "name": "technical_writer",
                    "display_name": "Technical Writer",
                    "description": (
                        "Subagente especializado en generar documentación técnica inicial "
                        "a partir de la especificación, validaciones, arquitectura y revisión de seguridad."
                    ),
                    "tools": ["generate_technical_doc"],
                    "prompt": """
                    Eres un subagente especializado en documentación técnica SDLC.

                    Alcance estricto:
                    - Usa únicamente la información generada durante la sesión.
                    - No explores repositorios.
                    - No inspecciones archivos.
                    - No ejecutes comandos.
                    - No busques contexto externo.
                    - No inventes decisiones aprobadas.
                    - No escribas el documento completo en la respuesta conversacional.
                    - No uses emojis ni iconos Unicode.

                    Tu misión:
                    - Generar documentación técnica inicial en formato resumido.
                    - Usar la tool generate_technical_doc cuando tengas información suficiente.
                    - Tras usar la tool, devuelve solo:
                    1. estado
                    2. ruta del fichero generado
                    3. secciones incluidas
                    4. dudas abiertas principales

                    Límite:
                    - Máximo 12 líneas de respuesta.
                    - No repitas toda la especificación.
                    - No repitas toda la arquitectura.
                    - Responde siempre en español.
                    """,
                },
                {
                    "name": "public_context_reviewer",
                    "display_name": "Public Context Reviewer",
                    "description": (
                        "Subagente especializado en recuperar contexto público de referencia "
                        "desde Wikipedia mediante una tool puente que invoca MCP por stdio."
                    ),
                    "tools": ["wikipedia_mcp_context"],
                    "prompt": """
                Eres un subagente de contexto público para una demo SDLC.

                Alcance estricto:
                - Usa únicamente la tool wikipedia_mcp_context.
                - La tool wikipedia_mcp_context invoca internamente un MCP server real de Wikipedia por stdio.
                - No intentes usar directamente el MCP wikipedia_context.
                - No busques tools MCP directamente.
                - No uses web_fetch, búsqueda web, navegador, curl o HTTP fetch.
                - No simules haber consultado Wikipedia.
                - No sustituyas MCP Wikipedia por otra herramienta.
                - No busques información interna de BBVA.
                - No busques datos personales.
                - No uses Wikipedia como fuente normativa o corporativa.
                - No tomes Wikipedia como fuente de verdad para decisiones regulatorias.
                - No uses emojis ni iconos Unicode.
                - Responde siempre en español.

                Tu misión:
                - Recuperar contexto público de referencia sobre conceptos relevantes de la iniciativa.
                - Usa wikipedia_mcp_context con estos conceptos:
                1. Autenticación multifactor
                2. Auditoría informática
                3. Trazabilidad
                - Devuelve un resumen breve y útil para el orquestador.
                - Indica claramente:
                - Fuente: Wikipedia
                - Método: MCP vía tool puente wikipedia_mcp_context
                - MCP server interno: wikipedia_context
                - Tool local invocada por el subagente: wikipedia_mcp_context

                Si wikipedia_mcp_context devuelve error, informa el error y no inventes contenido.
                """,
                },
            ],
        )

        assistant_output_parts = []

        def print_streaming_event(event):
            event_type = str(event.type)

            if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
                delta = event.data.delta_content or ""
                assistant_output_parts.append(delta)
                safe_write(delta)

            if "subagent" in event_type.lower():
                safe_write(f"\n[Evento subagente] {event_type}\n")

            if event.type == SessionEventType.SESSION_IDLE:
                safe_write("\n[Sesion finalizada]\n")

        session.on(print_streaming_event)

        prompt = f"""
{SYSTEM_PROMPT}

Session ID de demo:
{demo_session_id}

Idea de negocio:
{user_idea}

Contexto persistido:
{previous_context}

Instrucciones estrictas:
- No explores el repositorio.
- No inspecciones ficheros.
- No ejecutes comandos.
- No uses contexto externo salvo que el usuario pida explícitamente usar contexto público, usar Wikipedia o usar MCP Wikipedia.
- Si se permite contexto externo, solo puede obtenerse mediante el subagente public_context_reviewer y la tool wikipedia_mcp_context.
- La tool wikipedia_mcp_context invoca un MCP server real de Wikipedia por stdio.
- No uses web_fetch, búsqueda web, curl, navegador ni herramientas HTTP alternativas.
- No asumas nombres concretos de tools MCP.
- No menciones prefijos de tools MCP en la respuesta final.
- Trabaja principalmente con la idea de negocio proporcionada.
- No uses emojis.
- No uses iconos Unicode.
- No uses símbolos decorativos.
- No reproduzcas documentos completos en la respuesta final.
- Termina la respuesta final después de guardar la traza.
- Si hay contexto persistido, úsalo como referencia, pero no lo trates como verdad absoluta.
- Si el usuario pide continuar, refinar o ampliar, conserva la trazabilidad con el Session ID anterior.
- No uses herramientas alternativas como web_fetch, búsqueda web, navegador, HTTP fetch o herramientas no declaradas.
- Si wikipedia_mcp_context devuelve error, informa el error y continúa sin simular contexto público.
- No simules haber consultado Wikipedia.
- No sustituyas MCP Wikipedia por otra herramienta.

Rol:
Actúa como ORQUESTADOR SDLC.

Subagentes disponibles:

1. security_reviewer
   - Especialista en seguridad, autenticación, autorización, trazabilidad, auditoría y riesgos regulatorios.
   - Úsalo si la iniciativa afecta a clientes, operaciones bancarias, datos sensibles, permisos, identidad, pagos, transferencias, auditoría o cumplimiento.
   - Si se invoca, debe usar la tool security_precheck.

2. architecture_designer
   - Especialista en arquitectura técnica, infraestructura lógica, componentes, integraciones y riesgos técnicos.
   - Usa un LLM externo configurado para arquitectura mediante la tool architecture_llm_design.
   - Úsalo si la iniciativa requiere APIs, backend, integración con sistemas, canales digitales, core bancario, eventos, servicios, persistencia u observabilidad.
   - Si se invoca, debe usar la tool architecture_llm_design.

3. technical_writer
   - Especialista en documentación técnica.
   - Úsalo si el usuario pide explícitamente documentación técnica, borrador técnico o artefacto técnico.
   - Si se invoca, debe usar la tool generate_technical_doc.

4. public_context_reviewer
   - Especialista en recuperar contexto público de referencia desde Wikipedia mediante MCP.
   - Usa la tool wikipedia_mcp_context, que invoca un MCP server real de Wikipedia por stdio.
   - Úsalo si la iniciativa contiene "usar contexto público", "usar Wikipedia", "usar MCP Wikipedia" o si el usuario pide enriquecer la sesión con contexto externo público.
   - No debe usar web_fetch, búsqueda web, curl ni herramientas HTTP alternativas.
   - No debe usarse para información interna, normativa corporativa, datos sensibles ni decisiones regulatorias.

Regla de orquestación principal:
- Distingue entre subagentes de contexto y subagentes de análisis.
- public_context_reviewer es un subagente de contexto.
- security_reviewer, architecture_designer y technical_writer son subagentes de análisis.
- Por defecto, puedes invocar como máximo UN subagente de análisis.
- public_context_reviewer puede invocarse adicionalmente antes del subagente de análisis si el usuario pide usar contexto público, Wikipedia o MCP Wikipedia.
- Si se invoca public_context_reviewer, debe usar la tool wikipedia_mcp_context para intentar recuperar contexto público.
- Si wikipedia_mcp_context devuelve error, informa el error y continúa el flujo SDLC sin simular contexto público.
- Después decide si invocar un subagente de análisis.
- Solo puedes invocar varios subagentes de análisis si la idea contiene explícitamente la frase: "ejecutar sala completa".
- Si la idea contiene "ejecutar sala completa", puedes invocar security_reviewer, architecture_designer y technical_writer, si aplica.
- Si la idea contiene "usar MCP Wikipedia" o "usar Wikipedia", puedes invocar public_context_reviewer además de los subagentes de análisis aplicables.
- No invoques subagentes innecesarios.
- Si hay duda entre seguridad y arquitectura, prioriza security_reviewer cuando haya clientes, pagos, transferencias, autenticación, autorización o auditoría.
- Si el usuario indica explícitamente que la prioridad de la sesión es arquitectura técnica, prioriza architecture_designer como subagente de análisis.

Proceso:
1. Convierte la idea en una especificación SDLC estructurada.
2. Usa validate_spec para revisar si la especificación está completa.
3. Decide si debe invocarse public_context_reviewer.
4. Si se invoca public_context_reviewer, usa el contexto público recuperado para enriquecer la especificación, la decisión de orquestación y las dudas abiertas.
5. Decide qué subagente de análisis invocar según la regla de orquestación principal.
6. Invoca como máximo un subagente de análisis, salvo que la idea pida "ejecutar sala completa".
7. Si invocas security_reviewer, debe usar security_precheck.
8. Si invocas architecture_designer, debe usar architecture_llm_design.
9. Si invocas technical_writer, debe usar generate_technical_doc.
10. Usa save_trace para guardar la traza.
11. Devuelve la respuesta final en español.

La respuesta final debe incluir obligatoriamente estas secciones:

1. Especificación estructurada resumida

2. Contexto externo utilizado
   Incluye:
   - Si se ha usado contexto externo o no
   - Fuente utilizada
   - Método utilizado
   - Tool invocada
   - MCP interno utilizado por la tool, si aplica
   - Resumen del contexto recuperado
   - Limitaciones del contexto público

3. Resultado de validate_spec

4. Decisión de orquestación
   Incluye:
   - Subagentes disponibles
   - Subagentes evaluados
   - Subagentes candidatos
   - Subagentes invocados
   - Subagentes no invocados y motivo

   Usa estas definiciones:
   - Disponible: el subagente existe en la sesión.
   - Evaluado: el orquestador lo ha analizado como posible opción.
   - Candidato: el subagente sería útil para la iniciativa.
   - Invocado: el subagente se ha ejecutado realmente.
   - No invocado: el subagente no se ha ejecutado, aunque pueda haber sido evaluado o candidato.

   No uses "aplicable" como sinónimo de "invocado".
   Si un subagente es candidato pero no se invoca, explica claramente el motivo.

5. Modelo utilizado por agente/subagente
   Para cada agente o subagente indica:
   - nombre del agente
   - si ha sido invocado o no
   - modelo/proveedor utilizado
   - tool principal o MCP utilizado

   Usa esta convención:
   - Agente principal SDLC: Copilot SDK modelo por defecto
   - public_context_reviewer: Copilot SDK modelo por defecto + tool wikipedia_mcp_context + MCP wikipedia_context por stdio si ha sido invocado
   - security_reviewer: Copilot SDK modelo por defecto + security_precheck si ha sido invocado
   - architecture_designer: LLM externo OpenAI-compatible configurado en .env mediante architecture_llm_design si ha sido invocado
   - technical_writer: Copilot SDK modelo por defecto + generate_technical_doc si ha sido invocado

6. Resultado resumido de cada subagente invocado

7. Dudas abiertas

8. Trace ID
"""

        await session.send_and_wait(prompt, timeout=420)
        assistant_response = "".join(assistant_output_parts)

        save_session_record(
            {
                "session_id": demo_session_id,
                "created_at": None,
                "user_idea": user_idea,
                "prompt": prompt,
                "response": assistant_response,
                "status": "completed",
                "source": "copilot_sdlc_demo",
            }
        )

        safe_write(f"\n[Session ID persistido] {demo_session_id}\n")
    finally:
        await client.stop()


if __name__ == "__main__":
    idea = sys.argv[1] if len(sys.argv) > 1 else DEMO_IDEA
    existing_session_id = sys.argv[2] if len(sys.argv) > 2 else None

    asyncio.run(run_demo(idea, existing_session_id))