import subprocess
import sys
from pathlib import Path

import streamlit as st
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
DOC_PATH = ROOT_DIR / "docs" / "technical_documentation.md"
TRACE_PATH = ROOT_DIR / "data" / "traces.jsonl"


st.set_page_config(
    page_title="SDLC Agentic Demo",
    layout="wide",
)

st.title("SDLC Agentic Demo")
st.write("Frontend básico para ejecutar la demo con Copilot SDK.")

st.info(f"Directorio del proyecto: {ROOT_DIR}")

default_idea = (
    "Queremos permitir que un cliente pueda cancelar una transferencia pendiente "
    "desde la app móvil. La cancelación solo debe estar disponible para transferencias "
    "en estado pendiente, debe requerir autenticación fuerte, confirmación explícita "
    "del usuario, validación de titularidad de la cuenta y registro auditable de la operación."
)

user_idea = st.text_area(
    "Describe la iniciativa o idea de negocio",
    value=default_idea,
    height=180,
)


def read_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


if st.button("Ejecutar análisis SDLC"):
    st.write("Lanzando backend...")

    command = [
        sys.executable,
        "-m",
        "sdlc_demo.main",
        user_idea,
    ]

    st.code(" ".join(command))

    try:
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

        st.write(f"Return code: {process.returncode}")

        st.subheader("Salida estándar")
        st.text_area(
            "stdout",
            value=process.stdout or "Sin salida estándar",
            height=400,
        )

        if process.stderr:
            st.subheader("Errores")
            st.code(process.stderr)

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