import asyncio
import sys

from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType
from copilot.session import PermissionHandler

from sdlc_demo.prompts import DEMO_IDEA, SYSTEM_PROMPT
from sdlc_demo.tools import (
    architecture_precheck,
    generate_technical_doc,
    save_trace,
    security_precheck,
    validate_spec,
)


def print_streaming_event(event):
    event_type = str(event.type)

    if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
        sys.stdout.write(event.data.delta_content)
        sys.stdout.flush()

    if "subagent" in event_type.lower():
        print(f"\n[Evento subagente] {event_type}")

    if event.type == SessionEventType.SESSION_IDLE:
        print("\n[Sesión finalizada]")


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
                architecture_precheck,
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
                        "para iniciativas SDLC, incluyendo componentes, integraciones, riesgos "
                        "arquitectónicos e infraestructura lógica."
                    ),
                    "tools": ["architecture_precheck"],
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

Tu misión:
- Proponer una arquitectura técnica inicial.
- Identificar componentes lógicos.
- Identificar integraciones necesarias.
- Detectar riesgos arquitectónicos.
- Usar la tool architecture_precheck cuando tengas información suficiente.
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
- No reproduzcas documentos completos en la respuesta final; si una tool genera un documento, muestra solo la ruta y un resumen.
- Termina la respuesta final después de guardar la traza.

Rol:
Actúa como ORQUESTADOR SDLC inteligente.

Subagentes disponibles:
1. security_reviewer
   - Especialista en seguridad, autenticación, autorización, trazabilidad, auditoría y riesgos regulatorios.

2. architecture_designer
   - Especialista en arquitectura técnica, infraestructura lógica, componentes, integraciones y riesgos técnicos.

3. technical_writer
   - Especialista en documentación técnica.
   - Úsalo solo al final si hay suficiente información validada para generar un borrador técnico.

Criterios de orquestación:
1. Primero convierte la idea en una especificación SDLC estructurada.
2. Después usa validate_spec.
3. Decide dinámicamente qué subagentes son necesarios según la especificación y la validación.
4. Puedes invocar uno, varios o ningún subagente.
5. No invoques technical_writer hasta haber terminado las revisiones necesarias.
6. No invoques subagentes innecesarios.
7. Si la especificación es demasiado ambigua, no fuerces arquitectura ni documentación completa; genera dudas abiertas.
8. Usa save_trace al final.
9. Devuelve la respuesta final en español.

La respuesta final debe incluir:
- Especificación estructurada resumida
- Resultado de validate_spec
- Subagentes considerados
- Subagentes invocados
- Motivo de cada invocación
- Resultado resumido de cada subagente invocado
- Ruta del documento técnico generado, sin reproducir el documento completo
- Dudas abiertas
- Trace ID
"""

        await session.send_and_wait(prompt, timeout=300)

    finally:
        await client.stop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        idea = " ".join(sys.argv[1:])
    else:
        idea = DEMO_IDEA

    asyncio.run(run_demo(idea))