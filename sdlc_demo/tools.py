import asyncio
import json
import os
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from copilot.tools import define_tool
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

TRACE_FILE = Path("data/traces.jsonl")
WIKIPEDIA_MCP_DEBUG_FILE = Path("data/wikipedia_mcp_debug.log")


def write_wikipedia_debug(message: str) -> None:
    WIKIPEDIA_MCP_DEBUG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with WIKIPEDIA_MCP_DEBUG_FILE.open("a", encoding="utf-8") as file:
        file.write(message)
        file.write("\n")

class WikipediaMcpContextParams(BaseModel):
    concepts: List[str] = Field(
        description="Lista de conceptos públicos a consultar en Wikipedia mediante MCP"
    )
class WikipediaMcpContextParams(BaseModel):
    concepts: List[str] = Field(
        description="Lista de conceptos públicos a consultar en Wikipedia mediante MCP"
    )


@define_tool(
    description=(
        "Diagnostica y recupera contexto público desde Wikipedia usando un MCP server real "
        "por stdio. No usa web_fetch ni llamadas HTTP directas desde el agente."
    )
)
async def wikipedia_mcp_context(params: WikipediaMcpContextParams) -> dict:
    try:
        write_wikipedia_debug("INICIO wikipedia_mcp_context")
        write_wikipedia_debug(f"Conceptos recibidos: {params.concepts}")

        command = str(Path(sys.executable).parent / "wikipedia-mcp.exe")
        write_wikipedia_debug(f"Comando MCP: {command}")

        server_params = StdioServerParameters(
            command=command,
            args=[
                "--transport",
                "stdio",
                "--language",
                "es",
            ],
        )

        write_wikipedia_debug("ANTES de stdio_client")

        async with stdio_client(server_params) as (read, write):
            write_wikipedia_debug("DESPUES de stdio_client")

            async with ClientSession(read, write) as mcp_session:
                write_wikipedia_debug("DESPUES de ClientSession")

                write_wikipedia_debug("ANTES de initialize")
                await mcp_session.initialize()
                write_wikipedia_debug("DESPUES de initialize")

                write_wikipedia_debug("ANTES de list_tools")
                tools_response = await mcp_session.list_tools()
                available_tools = [tool.name for tool in tools_response.tools]
                write_wikipedia_debug(f"TOOLS DISPONIBLES: {available_tools}")

                return {
                    "status": "ok",
                    "source": "Wikipedia",
                    "method": "MCP via stdio",
                    "mcp_server": "wikipedia_context",
                    "tool_used_by_subagent": "wikipedia_mcp_context",
                    "available_tools": available_tools,
                    "concepts_requested": params.concepts[:3],
                }

    except BaseException as exc:
        error_detail = traceback.format_exc()

        write_wikipedia_debug("ERROR EN wikipedia_mcp_context")
        write_wikipedia_debug(f"Tipo error: {type(exc).__name__}")
        write_wikipedia_debug(f"Error: {str(exc)}")
        write_wikipedia_debug(error_detail)

        return {
            "status": "error",
            "source": "Wikipedia",
            "method": "MCP via stdio",
            "mcp_server": "wikipedia_context",
            "tool_used_by_subagent": "wikipedia_mcp_context",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "debug_file": str(WIKIPEDIA_MCP_DEBUG_FILE),
            "concepts_requested": params.concepts[:3],
        }
    
class ValidateSpecParams(BaseModel):
    problem: str = Field(description="Problema de negocio que se quiere resolver")
    users: str = Field(description="Usuarios afectados por el problema")
    expected_value: str = Field(description="Valor esperado para negocio o usuario")
    scope: str = Field(description="Alcance funcional de la solución")
    constraints: str = Field(description="Restricciones funcionales, técnicas, regulatorias o de seguridad")
    acceptance_criteria: List[str] = Field(description="Criterios de aceptación verificables")


@define_tool(description="Valida si una especificación SDLC mínima está suficientemente completa")
async def validate_spec(params: ValidateSpecParams) -> dict:
    issues = []

    if len(params.problem.strip()) < 25:
        issues.append("El problema está poco definido o es demasiado genérico.")

    if len(params.users.strip()) < 10:
        issues.append("Los usuarios afectados no están suficientemente definidos.")

    if len(params.expected_value.strip()) < 20:
        issues.append("El valor esperado es ambiguo o insuficiente.")

    if len(params.scope.strip()) < 20:
        issues.append("El alcance funcional necesita más detalle.")

    if len(params.constraints.strip()) < 20:
        issues.append("Las restricciones son insuficientes para un entorno bancario regulado.")

    if len(params.acceptance_criteria) < 3:
        issues.append("Debe haber al menos 3 criterios de aceptación verificables.")

    weak_criteria = [
        criterion
        for criterion in params.acceptance_criteria
        if len(criterion.strip()) < 15
    ]

    if weak_criteria:
        issues.append("Algunos criterios de aceptación son demasiado vagos.")

    return {
        "agent": "main_sdlc_orchestrator",
        "provider": "copilot_sdk_default_model",
        "tool_used": "validate_spec",
        "is_complete": len(issues) == 0,
        "issues": issues,
        "recommendation": (
            "Puede pasar a revisión humana inicial."
            if len(issues) == 0
            else "Debe refinarse antes de pasar a MSA/Jira o construcción."
        ),
    }


class SaveTraceParams(BaseModel):
    input_idea: str = Field(description="Idea original introducida por el usuario")
    generated_spec_summary: str = Field(description="Resumen de la especificación generada")
    validation_result: str = Field(description="Resultado de la validación")
    open_questions: List[str] = Field(description="Dudas abiertas detectadas")


@define_tool(description="Guarda una traza mínima auditable de una interacción agéntica SDLC")
async def save_trace(params: SaveTraceParams) -> dict:
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)

    trace_id = str(uuid.uuid4())

    event = {
        "trace_id": trace_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_idea": params.input_idea,
        "generated_spec_summary": params.generated_spec_summary,
        "validation_result": params.validation_result,
        "open_questions": params.open_questions,
    }

    with TRACE_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")

    return {
        "agent": "main_sdlc_orchestrator",
        "provider": "copilot_sdk_default_model",
        "tool_used": "save_trace",
        "trace_id": trace_id,
        "status": "stored",
        "file": str(TRACE_FILE),
    }

class SecurityPrecheckParams(BaseModel):
    feature_summary: str = Field(description="Resumen funcional de la iniciativa")
    constraints: str = Field(description="Restricciones conocidas")
    acceptance_criteria: List[str] = Field(description="Criterios de aceptación")


@define_tool(description="Realiza una prevalidación básica de seguridad para una especificación SDLC bancaria")
async def security_precheck(params: SecurityPrecheckParams) -> dict:
    findings = []

    text = " ".join(
        [
            params.feature_summary,
            params.constraints,
            " ".join(params.acceptance_criteria),
        ]
    ).lower()

    if "autentic" not in text and "identidad" not in text and "login" not in text:
        findings.append(
            "No se menciona autenticación o verificación de identidad del usuario."
        )

    if "autoriza" not in text and "permiso" not in text and "rol" not in text:
        findings.append(
            "No se menciona autorización o control de permisos."
        )

    if "auditor" not in text and "traza" not in text and "log" not in text:
        findings.append(
            "No se menciona trazabilidad o auditoría de la operación."
        )

    if "confirm" not in text and "firma" not in text and "doble" not in text:
        findings.append(
            "No se menciona confirmación explícita antes de ejecutar la acción."
        )

    if "estado" not in text and "pendiente" not in text:
        findings.append(
            "No se especifica claramente el estado permitido de la operación."
        )

    return {
    "agent": "security_reviewer",
    "provider": "copilot_sdk_default_model",
    "tool_used": "security_precheck",
    "security_status": "ok" if len(findings) == 0 else "needs_review",
    "findings": findings,
    "recommendation": (
        "La especificación supera la prevalidación básica de seguridad."
        if len(findings) == 0
        else "La especificación debe revisarse/refinarse desde seguridad antes de avanzar."
    ),
}

class ArchitecturePrecheckParams(BaseModel):
    feature_summary: str = Field(description="Resumen funcional de la iniciativa")
    functional_scope: str = Field(description="Alcance funcional de la iniciativa")
    constraints: str = Field(description="Restricciones funcionales, técnicas, regulatorias o de seguridad")
    acceptance_criteria: List[str] = Field(description="Criterios de aceptación")


@define_tool(description="Propone una arquitectura técnica inicial para una iniciativa SDLC")
async def architecture_precheck(params: ArchitecturePrecheckParams) -> dict:
    text = " ".join(
        [
            params.feature_summary,
            params.functional_scope,
            params.constraints,
            " ".join(params.acceptance_criteria),
        ]
    ).lower()

    components = []
    risks = []
    recommendations = []

    if "app" in text or "móvil" in text or "mobile" in text:
        components.append("Frontend móvil / canal digital")
        recommendations.append("Exponer la funcionalidad mediante API backend consumible por canal móvil.")

    if "transferencia" in text or "pago" in text or "cuenta" in text:
        components.append("Servicio backend de operaciones bancarias")
        components.append("Integración con sistema core/transaccional")
        risks.append("Riesgo de inconsistencia si no se valida correctamente el estado de la operación.")

    if "cancelar" in text or "anular" in text:
        components.append("Servicio de validación de estado y reversibilidad")
        recommendations.append("Validar estado permitido antes de ejecutar la cancelación.")

    if "auditor" in text or "traza" in text or "log" in text:
        components.append("Registro de auditoría / event log")
    else:
        risks.append("No aparece explícitamente un componente de auditoría o trazabilidad.")

    if "autentic" in text or "firma" in text or "confirm" in text:
        components.append("Servicio de autenticación / autorización / firma")
    else:
        risks.append("No aparece explícitamente un mecanismo de autenticación fuerte o confirmación.")

    if not components:
        components.append("API backend")
        components.append("Servicio de negocio")
        components.append("Persistencia")
        components.append("Observabilidad básica")

    return {
        "architecture_style": "Arquitectura orientada a servicios/API con integración controlada a sistemas internos.",
        "suggested_components": components,
        "integration_points": [
            "Canal digital",
            "Backend de dominio",
            "Sistema core/transaccional",
            "Auditoría y observabilidad",
        ],
        "architecture_risks": risks,
        "recommendations": recommendations,
        "human_review_required": True,
    }


class TechnicalDocParams(BaseModel):
    title: str = Field(description="Título del documento técnico")
    feature_summary: str = Field(description="Resumen funcional de la iniciativa")
    architecture_summary: str = Field(description="Resumen de arquitectura propuesta")
    validation_summary: str = Field(description="Resumen de validaciones realizadas")
    security_summary: str = Field(description="Resumen de revisión de seguridad")
    open_questions: List[str] = Field(description="Dudas abiertas")


@define_tool(description="Genera y guarda una documentación técnica en Markdown para una iniciativa SDLC")
async def generate_technical_doc(params: TechnicalDocParams) -> dict:
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)

    file_path = docs_dir / "technical_documentation.md"

    open_questions = "\n".join(
        f"- {question}" for question in params.open_questions
    )

    content = f"""# {params.title}

## 1. Contexto

{params.feature_summary}

## 2. Arquitectura propuesta

{params.architecture_summary}

## 3. Validaciones realizadas

{params.validation_summary}

## 4. Consideraciones de seguridad

{params.security_summary}

## 5. Dudas abiertas

{open_questions}

## 6. Próximos pasos

- Revisión humana de la especificación.
- Validación con arquitectura.
- Validación con seguridad.
- Refinamiento antes de crear épica/historia técnica.
"""

    file_path.write_text(content, encoding="utf-8")

    return {
        "agent": "technical_writer",
        "provider": "copilot_sdk_default_model",
        "tool_used": "generate_technical_doc",
        "document_type": "Documento técnico inicial",
        "title": params.title,
        "file_path": str(file_path),
        "included_sections": [
            "Contexto",
            "Arquitectura propuesta",
            "Validaciones realizadas",
            "Consideraciones de seguridad",
            "Dudas abiertas",
            "Próximos pasos",
        ],
        "format": "markdown",
        "status": "saved",
    }

def call_architecture_llm(prompt: str) -> str:
    api_key = os.getenv("ARCH_LLM_API_KEY")
    base_url = os.getenv("ARCH_LLM_BASE_URL")
    deployment = os.getenv("ARCH_LLM_DEPLOYMENT")

    missing = []

    if not api_key:
        missing.append("ARCH_LLM_API_KEY")

    if not base_url:
        missing.append("ARCH_LLM_BASE_URL")

    if not deployment:
        missing.append("ARCH_LLM_DEPLOYMENT")

    if missing:
        return (
            "No se ha podido invocar el LLM de arquitectura porque faltan variables "
            "en el fichero .env: " + ", ".join(missing)
        )

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    response = client.responses.create(
        model=deployment,
        input=prompt,
    )

    return response.output_text

class ArchitectureLlmDesignParams(BaseModel):
    feature_summary: str = Field(description="Resumen funcional de la iniciativa")
    functional_scope: str = Field(description="Alcance funcional de la iniciativa")
    constraints: str = Field(description="Restricciones funcionales, técnicas, regulatorias o de seguridad")
    acceptance_criteria: List[str] = Field(description="Criterios de aceptación")
    security_summary: str = Field(description="Resumen de la revisión de seguridad, si existe")


@define_tool(description="Genera una propuesta de arquitectura usando un LLM externo configurado para arquitectura")
async def architecture_llm_design(params: ArchitectureLlmDesignParams) -> dict:
    architecture_prompt = f"""
Eres un arquitecto técnico senior en un entorno bancario regulado.

Genera una propuesta de arquitectura técnica inicial para la siguiente iniciativa SDLC.

Resumen funcional:
{params.feature_summary}

Alcance funcional:
{params.functional_scope}

Restricciones:
{params.constraints}

Criterios de aceptación:
{chr(10).join("- " + criterion for criterion in params.acceptance_criteria)}

Resumen de seguridad:
{params.security_summary}

Necesito una propuesta resumida con estas secciones:
1. Estilo arquitectónico recomendado
2. Componentes lógicos
3. Integraciones necesarias
4. Datos y trazabilidad
5. Observabilidad
6. Riesgos técnicos
7. Decisiones pendientes
8. Revisión humana requerida

Reglas:
- Responde en español.
- No uses emojis.
- No uses iconos Unicode.
- No inventes nombres internos de sistemas.
- Marca supuestos cuando falte información.
- No digas que la arquitectura está aprobada.
"""

    try:
        architecture_output = await asyncio.to_thread(
            call_architecture_llm,
            architecture_prompt,
        )

        return {
            "agent": "architecture_designer",
            "provider": "external_openai_compatible_llm",
            "deployment": os.getenv("ARCH_LLM_DEPLOYMENT", "not_configured"),
            "model_source": "configured_in_env",
            "tool_used": "architecture_llm_design",
            "status": "ok",
            "architecture_proposal": architecture_output,
            "human_review_required": True,
        }

    except Exception as exc:
        return {
            "agent": "architecture_designer",
            "provider": "external_openai_compatible_llm",
            "deployment": os.getenv("ARCH_LLM_DEPLOYMENT", "not_configured"),
            "model_source": "configured_in_env",
            "tool_used": "architecture_llm_design",
            "status": "error",
            "error": str(exc),
            "architecture_proposal": "No se pudo generar la arquitectura con el LLM externo.",
            "human_review_required": True,
        }