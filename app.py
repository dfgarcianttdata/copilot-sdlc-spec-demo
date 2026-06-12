import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

from sdlc_demo.session_store import load_session_records


ROOT_DIR = Path(__file__).parent
DOC_PATH = ROOT_DIR / "docs" / "technical_documentation.md"
TRACE_PATH = ROOT_DIR / "data" / "traces.jsonl"


st.set_page_config(
    page_title="SDLC Agentic Demo",
    layout="wide",
)


def read_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def run_sdlc_backend(user_idea: str, session_id: str | None = None):
    command = [
        sys.executable,
        "-m",
        "sdlc_demo.main",
        user_idea,
    ]

    if session_id:
        command.append(session_id)

    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }

    process = subprocess.run(
        command,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=420,
        env=env,
    )

    return process.returncode, process.stdout, process.stderr, command


st.title("SDLC Agentic Demo")
st.write("Frontend básico para ejecutar la demo con Copilot SDK.")

st.info(f"Directorio del proyecto: {ROOT_DIR}")


st.sidebar.title("SDLC Demo")
st.sidebar.markdown("## Sesiones persistidas")

session_records = load_session_records(limit=10)

session_options = ["Nueva sesión"]
session_id_by_label = {}

for record in session_records:
    created_at = record.get("created_at") or ""
    session_id = record.get("session_id") or ""

    label = f"{created_at[:19]} | {session_id}"
    session_options.append(label)
    session_id_by_label[label] = session_id

selected_session_label = st.sidebar.selectbox(
    "Continuar sesión",
    session_options,
)

selected_session_id = None

if selected_session_label != "Nueva sesión":
    selected_session_id = session_id_by_label[selected_session_label]
    st.sidebar.caption(f"Session ID seleccionado: {selected_session_id}")

    selected_record = next(
        (
            record
            for record in session_records
            if record.get("session_id") == selected_session_id
        ),
        None,
    )

    if selected_record:
        with st.sidebar.expander("Ver resumen de sesión"):
            st.write("Idea anterior:")
            st.caption(selected_record.get("user_idea", "")[:1000])
else:
    st.sidebar.caption("Se creará una nueva sesión.")


default_idea = (
    "Queremos permitir que un cliente pueda cancelar una transferencia pendiente "
    "desde la app móvil. La cancelación solo debe estar disponible para transferencias "
    "en estado pendiente, debe requerir autenticación fuerte, confirmación explícita "
    "del usuario, validación de titularidad de la cuenta y registro auditable de la operación."
)

if selected_session_id:
    default_idea = "Continúa esta sesión y añade riesgos técnicos de arquitectura."

user_idea = st.text_area(
    "Describe la iniciativa o idea de negocio",
    value=default_idea,
    height=180,
)

if selected_session_id:
    st.info(f"Se continuará la sesión: {selected_session_id}")
else:
    st.info("Se ejecutará una nueva sesión.")


if st.button("Ejecutar análisis SDLC"):
    try:
        with st.spinner("Ejecutando análisis SDLC..."):
            returncode, stdout, stderr, command = run_sdlc_backend(
                user_idea=user_idea,
                session_id=selected_session_id,
            )

        st.code(" ".join(command))
        st.write(f"Return code: {returncode}")

        st.subheader("Salida estándar")
        st.text_area(
            "stdout",
            value=stdout or "Sin salida estándar",
            height=500,
        )

        if stderr:
            st.subheader("Errores")
            st.code(stderr)

        if returncode == 0:
            st.success(
                "Ejecución completada. Refresca la página para ver la sesión en el selector."
            )

    except subprocess.TimeoutExpired:
        st.error("La ejecución ha superado el timeout del frontend.")
    except Exception as exc:
        st.error("Error ejecutando el backend.")
        st.exception(exc)


st.subheader("Documento técnico")

doc_content = read_file(DOC_PATH)

if doc_content:
    st.download_button(
        "Descargar documentación técnica",
        data=doc_content,
        file_name="technical_documentation.md",
        mime="text/markdown",
    )

    with st.expander("Previsualizar documento técnico"):
        st.markdown(doc_content)
else:
    st.info("No se encontró documentación técnica todavía.")


st.subheader("Trazabilidad")

trace_content = read_file(TRACE_PATH)

if trace_content:
    st.download_button(
        "Descargar trazas",
        data=trace_content,
        file_name="traces.jsonl",
        mime="application/json",
    )

    with st.expander("Ver trazas"):
        st.code(trace_content)
else:
    st.info("No se encontraron trazas todavía.")