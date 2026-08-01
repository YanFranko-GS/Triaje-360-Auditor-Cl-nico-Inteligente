from __future__ import annotations

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from auth_service import AuthPrincipal
from clinical_db import patient_by_id
from longitudinal_db import descriptive_statistics, patient_longitudinal_record, schema_catalog


def _patient_dni(principal: AuthPrincipal) -> str | None:
    patient = patient_by_id(principal.patient_id or "")
    return patient["synthetic_identifier"] if patient else None


def render_patient_history(principal: AuthPrincipal) -> None:
    dni = _patient_dni(principal)
    if not dni:
        st.error("No se encontró el registro longitudinal asociado.")
        return
    st.title("Mi historia clínica")
    st.caption("Consultas y registros confirmados por personal sanitario.")
    c1, c2, c3 = st.columns(3)
    date_from = c1.date_input("Desde", value=date(2025, 1, 1), key="history_from")
    date_to = c2.date_input("Hasta", value=date.today(), key="history_to")
    facility = c3.selectbox("Establecimiento", ("", "DEMO_FAC_A", "DEMO_FAC_B"), format_func=lambda value: {"": "Todos", "DEMO_FAC_A": "Centro Andino", "DEMO_FAC_B": "Policlínico Costa"}[value])
    record = patient_longitudinal_record(dni, facility_id=facility or None, date_from=date_from.isoformat(), date_to=date_to.isoformat())
    if not record["encounters"]:
        st.info("No existen consultas para los filtros seleccionados.")
    for encounter in record["encounters"]:
        encounter_diagnoses = [item for item in record["diagnoses"] if item.get("encounter_id") == encounter["id"]]
        encounter_prescriptions = [item for item in record["prescriptions"] if item.get("encounter_id") == encounter["id"]]
        with st.expander(f"{encounter['started_at'][:10]} · {encounter['chief_complaint']} · {encounter.get('facility_name') or 'Establecimiento'}"):
            st.write(f"**Estado:** {encounter['status']}")
            st.write("**Profesional:** " + (encounter.get("created_by") or "Registrado por el establecimiento"))
            st.write("**Diagnóstico registrado:** " + (", ".join(item["description"] for item in encounter_diagnoses) or "Sin diagnóstico registrado"))
            st.write("**Receta registrada:** " + (", ".join(item["medication_name"] for item in encounter_prescriptions) or "Sin receta registrada"))
            if encounter_prescriptions:
                st.write("**Indicaciones registradas:** " + "; ".join(item.get("instructions") or "" for item in encounter_prescriptions))
            st.write("**Resultados:** consulte los registros confirmados del establecimiento.")
            st.write("**Próxima cita:** no registrada")


def render_descriptive_analytics(dni: str) -> None:
    st.subheader("Resumen histórico descriptivo")
    st.caption("Los gráficos describen registros existentes y no establecen causalidad ni calculan riesgo.")
    stats = descriptive_statistics(dni)
    c1, c2 = st.columns(2)
    if stats["monthly"]:
        monthly = pd.DataFrame(stats["monthly"])
        c1.altair_chart(alt.Chart(monthly).mark_bar(color="#0b5cab").encode(x=alt.X("mes:N", title="Mes"), y=alt.Y("atenciones:Q", title="Atenciones"), tooltip=["mes", "atenciones"]).properties(title="Atenciones por mes"), use_container_width=True)
    if stats["complaints"]:
        complaints = pd.DataFrame(stats["complaints"])
        c2.altair_chart(alt.Chart(complaints).mark_bar(color="#0284c7").encode(y=alt.Y("motivo:N", sort="-x", title="Motivo"), x=alt.X("atenciones:Q", title="Atenciones"), tooltip=["motivo", "atenciones"]).properties(title="Motivos más frecuentes"), use_container_width=True)
    vitals = pd.DataFrame(stats["vitals"])
    if not vitals.empty:
        vitals["fecha"] = pd.to_datetime(vitals["recorded_at"])
        for title, columns in (
            ("Evolución de presión arterial", ["systolic", "diastolic"]),
            ("Evolución de saturación", ["oxygen_saturation"]),
            ("Evolución de temperatura", ["temperature"]),
            ("Escala de dolor histórica", ["pain_score"]),
        ):
            available = [column for column in columns if column in vitals and vitals[column].notna().any()]
            if available:
                melted = vitals[["fecha", *available]].melt("fecha", var_name="medición", value_name="valor").dropna()
                st.altair_chart(alt.Chart(melted).mark_line(point=True).encode(x=alt.X("fecha:T", title="Fecha"), y=alt.Y("valor:Q", title="Valor", scale=alt.Scale(zero=False)), color="medición:N", tooltip=["fecha:T", "medición:N", "valor:Q"]).properties(title=title), use_container_width=True)
    if stats["facilities"]:
        st.dataframe(stats["facilities"], use_container_width=True, hide_index=True)
    record = patient_longitudinal_record(dni)
    st.write("**Medicamentos registrados:** " + (", ".join(item["name"] for item in record["medications"]) or "Sin registros"))


def render_data_structure() -> None:
    st.title("Estructura de datos")
    st.caption("Catálogo administrativo de SQLite. No expone contraseñas, hashes, sales ni secretos.")
    catalog = schema_catalog()
    summary = [{"tabla": item["table"], "columnas": len(item["columns"]), "registros": item["row_count"], "claves_foráneas": len(item["foreign_keys"])} for item in catalog]
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.success("Migraciones idempotentes aplicadas · claves foráneas activas")
    selected = st.selectbox("Inspeccionar tabla", [item["table"] for item in catalog])
    item = next(entry for entry in catalog if entry["table"] == selected)
    safe_columns = [column for column in item["columns"] if not any(secret in column["name"].casefold() for secret in ("password", "hash", "salt", "secret", "token"))]
    st.dataframe(safe_columns, use_container_width=True, hide_index=True)
    if item["foreign_keys"]:
        st.markdown("#### Claves foráneas")
        st.dataframe(item["foreign_keys"], use_container_width=True, hide_index=True)
