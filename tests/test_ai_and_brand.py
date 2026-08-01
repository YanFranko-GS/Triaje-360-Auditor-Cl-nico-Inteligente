from pathlib import Path

from PIL import Image

from ui.ai_status import AIState, LABELS, make_status


ROOT = Path(__file__).resolve().parents[1]


def test_logos_exist_and_keep_valid_dimensions() -> None:
    for name in ("GEMA.png", "Nosotros_KutanLAB.png"):
        path = ROOT / "logos" / name
        assert path.is_file()
        with Image.open(path) as image:
            assert image.width > 100 and image.height > 100


def test_all_runtime_states_have_spanish_labels() -> None:
    assert set(LABELS) == set(AIState)
    assert LABELS[AIState.READY] == "Disponible"
    assert LABELS[AIState.ANALYZING] == "Analizando"
    assert LABELS[AIState.FALLBACK] == "Fallback activado"


def test_runtime_status_tracks_duration_and_fallback() -> None:
    status = make_status(
        AIState.FALLBACK, "deterministic-fallback", duration_seconds=1.25,
        fallback_used=True, last_result="Conexión no disponible",
    )
    assert status.duration_seconds == 1.25
    assert status.fallback_used
    assert status.checked_at


def test_activity_is_indeterminate_not_clinical_percentage() -> None:
    source = (ROOT / "ui" / "ai_status.py").read_text(encoding="utf-8")
    styles = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")
    assert "progreso por etapas, no porcentaje clínico" in source
    assert "@keyframes triage-activity" in styles
    assert "width:34%" in styles
