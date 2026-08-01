from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
COMPONENTS = (ROOT / "ui" / "components.py").read_text(encoding="utf-8")
PAGES = (ROOT / "ui" / "pages.py").read_text(encoding="utf-8")
AI_STATUS = (ROOT / "ui" / "ai_status.py").read_text(encoding="utf-8")
STYLES = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")


def test_header_and_primary_copy_are_present() -> None:
    assert "TRIaje 360" in COMPONENTS
    assert "Auditor Clínico Inteligente" in COMPONENTS
    assert "Auditoría concurrente de completitud documental con Gemma 4" in COMPONENTS
    assert "Prototipo educativo" in COMPONENTS


def test_initial_clinical_panel_explains_the_flow() -> None:
    assert "Esperando análisis del caso" in COMPONENTS
    assert "Registrar" in COMPONENTS
    assert "Estructurar" in COMPONENTS
    assert "Verificar" in COMPONENTS


def test_main_actions_and_model_states_are_visible() -> None:
    assert "Analizar caso con Gemma 4 y RAG" in PAGES
    assert "Cerrar registro demostrativo" in PAGES
    assert "Gemma 4 respondió correctamente" in PAGES
    assert "Fallback activado" in AI_STATUS


def test_styles_use_safe_header_spacing() -> None:
    assert ".block-container" in STYLES
    assert "padding: 2.5rem" in STYLES
    assert "position: fixed" not in STYLES
    assert "margin-top: -" not in STYLES
    assert "translate(" not in STYLES
    assert "overflow: hidden" not in STYLES


def test_ui_uses_only_repository_relative_assets() -> None:
    combined = APP + COMPONENTS + PAGES + AI_STATUS + STYLES
    assert "C:\\Users\\ACER" not in combined
    assert "C:/Users/ACER" not in combined
    assert "http://" not in STYLES
    assert "https://" not in STYLES


def test_required_status_and_flow_labels_are_present() -> None:
    for label in ("Estado de Ollama", "Modelo activo", "Motor de seguridad", "Base de datos"):
        assert label in COMPONENTS
    for label in ("Admisión", "Análisis con Gemma", "Verificación", "Cierre documental"):
        assert label in COMPONENTS


def test_multiview_navigation_and_branding_are_present() -> None:
    for page in ("Inicio", "Portal del paciente", "Estación de triaje", "Panel médico", "Datos ficticios", "Auditoría"):
        assert page in APP or page in PAGES
    assert "Nosotros_KutanLAB.png" in COMPONENTS
    assert "GEMA.png" in COMPONENTS
    assert "brand-fallback" in COMPONENTS
    assert 'initial_sidebar_state="expanded"' in APP
    assert 'key="nav_page"' in APP
