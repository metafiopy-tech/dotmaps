"""Phase-2 gate: a tester can parameterize map 1 via the dialogue and approve
the board (spec §5). Non-interactive proofs via the answers-dict front-end; the
CLI wires the same engine to prompts.
"""
import json

import pytest
from conftest import MAPS

from dotmaps.compiler.intake import Template, compile_map, fill, render_board
from dotmaps.models import Map

MAP1 = MAPS / "map-deploy-verify-cloudflare"

ANSWERS = {
    "base_url": "https://bennyslu.lovable.app",
    "pages": "/, /about, /scoring-camp, /contact",
    "custom_domain": "",
    "form_endpoint": "/api/public/signup",
    "form_staging_base": "",
    "allow_prod_form": "no",
    "min_images": "3",
    "lighthouse_min": "80",
}


def test_dialogue_fills_map1_config(tmp_path):
    m = Map.load(MAP1)
    out = compile_map(m, tmp_path / "ws", answers=ANSWERS, approve=lambda b: True)
    cfg = json.loads(out.read_text())
    assert out.name == "target.json"
    assert cfg["base_url"] == "https://bennyslu.lovable.app"
    assert cfg["pages"] == ["/", "/about", "/scoring-camp", "/contact"]
    assert cfg["custom_domain"] is None       # blank optional -> null
    assert cfg["allow_prod_form"] is False    # "no" -> bool
    assert cfg["min_images"] == 3             # "3" -> int


def test_board_shown_and_approval_required(tmp_path):
    m = Map.load(MAP1)
    shown = {}
    def approve(board_text: str) -> bool:
        shown["text"] = board_text
        return False  # user declines
    with pytest.raises(PermissionError):
        compile_map(m, tmp_path / "ws", answers=ANSWERS, approve=approve)
    # the user saw every promise and the fog before declining
    assert "9 promises" in shown["text"]
    assert "Every page in the sitemap returns HTTP 200" in shown["text"]
    assert "THE FOG" in shown["text"]
    assert "[destructive — gated]" in shown["text"]  # dot 007 flagged honestly
    # declined -> nothing written
    assert not (tmp_path / "ws" / "target.json").exists()


def test_approval_artifact_written(tmp_path):
    m = Map.load(MAP1)
    compile_map(m, tmp_path / "ws", answers=ANSWERS, approve=lambda b: True)
    artifact = tmp_path / "ws" / ".dotmaps" / "approved_board.txt"
    assert artifact.exists()
    assert "[approved " in artifact.read_text()


def test_compiled_config_satisfies_map1_verifiers(tmp_path):
    """The dialogue's output must be exactly what the verifiers consume."""
    from dotmaps.verifier.runner import Verifier
    m = Map.load(MAP1)
    ws = tmp_path / "ws"
    compile_map(m, ws, answers=ANSWERS, approve=lambda b: True)
    v = Verifier.for_map(m, mode="local")
    r = v.run_one(m, "002", ws)  # live HTTP check driven by the compiled config
    assert r.passed, r.evidence


def test_unknown_answer_keys_rejected():
    m = Map.load(MAP1)
    t = Template.for_map(m)
    with pytest.raises(ValueError, match="unknown answer keys"):
        fill(t, {"base_url": "https://x.com", "not_a_field": 1})


def test_all_three_maps_have_templates():
    for name in ("map-deploy-verify-cloudflare", "map-content-migration", "map-health-recert"):
        m = Map.load(MAPS / name)
        t = Template.for_map(m)   # raises if the template is missing
        assert t.questions
        assert render_board(m)    # board renders for every shipped map
