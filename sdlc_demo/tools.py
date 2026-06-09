import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from copilot.tools import define_tool
from pydantic import BaseModel, Field


TRACE_FILE = Path("data/traces.jsonl")


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