import asyncio
import sys


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


def print_streaming_event(event):
    event_type = str(event.type)

    if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
        safe_write(event.data.delta_content)

    if "subagent" in event_type.lower():
        safe_write(f"\n[Evento subagente] {event_type}\n")

    if event.type == SessionEventType.SESSION_IDLE:
        safe_write("\n[Sesion finalizada]\n")


async def run_demo(user_idea: str):
    client = CopilotClient()
    await client.start()

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
            ],
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
            ],
        )

        session.on(print_streaming_event)

        prompt = f"""
{SYSTEM_PROMPT}

Idea de negocio:
{user_idea}

Instrucciones estrictas:
- No explores el repositorio.
- No inspecciones ficheros.
- No ejecutes comandos.
- No busques contexto externo.
- Trabaja únicamente con la idea de negocio proporcionada.
- No uses emojis.
- No uses iconos Unicode.
- No uses símbolos decorativos.
- No reproduzcas documentos completos en la respuesta final.
- Termina la respuesta final después de guardar la traza.

Rol:
Actúa como ORQUESTADOR SDLC.

Subagentes disponibles:
1. security_reviewer
   - Especialista en seguridad, autenticación, autorización, trazabilidad, auditoría y riesgos regulatorios.
   - Úsalo si la iniciativa afecta a clientes, operaciones bancarias, datos sensibles, permisos, identidad, pagos, transferencias, auditoría o cumplimiento.

2. architecture_designer
   - Especialista en arquitectura técnica, infraestructura lógica, componentes, integraciones y riesgos técnicos.
   - Úsalo si la iniciativa requiere APIs, backend, integración con sistemas, canales digitales, core bancario, eventos, servicios, persistencia u observabilidad.

3. technical_writer
   - Especialista en documentación técnica.
   - Úsalo si el usuario pide explícitamente documentación técnica, borrador técnico o artefacto técnico.

Regla de orquestación principal:
- Por defecto, invoca como máximo UN subagente.
- Elige el subagente más relevante según la idea de negocio.
- No invoques subagentes innecesarios.
- Si hay duda entre seguridad y arquitectura, prioriza security_reviewer cuando haya clientes, pagos, transferencias, autenticación, autorización o auditoría.
- Solo puedes invocar varios subagentes si la idea contiene explícitamente la frase: "ejecutar sala completa".
- Si la idea contiene "ejecutar sala completa", puedes invocar security_reviewer, architecture_designer y technical_writer, si aplica.

Proceso:
1. Convierte la idea en una especificación SDLC estructurada.
2. Usa validate_spec para revisar si la especificación está completa.
3. Decide qué subagente invocar según la regla de orquestación principal.
4. Invoca como máximo un subagente, salvo que la idea pida "ejecutar sala completa".
5. Si invocas security_reviewer, debe usar security_precheck.
6. Si invocas architecture_designer, debe usar architecture_llm_design.
7. Si invocas technical_writer, debe usar generate_technical_doc.
8. Usa save_trace para guardar la traza.
9. Devuelve la respuesta final en español.

La respuesta final debe incluir obligatoriamente estas secciones:

1. Especificación estructurada resumida

2. Resultado de validate_spec

3. Decisión de orquestación
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

4. Modelo utilizado por agente/subagente
   Para cada agente o subagente indica:
   - nombre del agente
   - si ha sido invocado o no
   - modelo/proveedor utilizado
   - tool principal utilizada

   Usa esta convención:
   - Agente principal SDLC: Copilot SDK modelo por defecto
   - security_reviewer: Copilot SDK modelo por defecto si ha sido invocado
   - architecture_designer: LLM externo OpenAI-compatible configurado en .env mediante architecture_llm_design si ha sido invocado
   - technical_writer: Copilot SDK modelo por defecto si ha sido invocado

5. Resultado resumido de cada subagente invocado

6. Dudas abiertas

7. Trace ID

"""

        await session.send_and_wait(prompt, timeout=420)

    finally:
        await client.stop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        idea = " ".join(sys.argv[1:])
    else:
        idea = DEMO_IDEA

    asyncio.run(run_demo(idea))