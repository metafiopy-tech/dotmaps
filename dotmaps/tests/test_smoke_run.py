"""Phase-1 gate: the orchestrator loop passes the trivial two-dot smoke map."""
from conftest import SMOKE_MAP

from dotmaps.models import Map
from dotmaps.runtime.orchestrator import Orchestrator


def test_smoke_map_goes_all_green(tmp_path):
    m = Map.load(SMOKE_MAP)
    assert m.validate() == []  # rule 1: compile/validate before launch
    board = Orchestrator(m, tmp_path / "ws", verbose=False).run()
    assert board.ended == "all_green"
    assert board.eaten == {"001", "002"}
    # dependency ordering: 001 was eaten no later than 002 (selector respected deps)
    assert (tmp_path / "ws" / "hello.txt").read_text().strip() == "MAGIC-TOKEN present"


def test_selector_respects_depends_on(tmp_path):
    from dotmaps.runtime.selector import Selector
    from dotmaps.scoreboard.state import Scoreboard

    m = Map.load(SMOKE_MAP)
    board = Scoreboard.load_or_init(tmp_path / "ws2", m)
    # nothing eaten yet -> only 001 is eligible (002 depends on 001)
    assert Selector.next_uneaten(board, m.dots).id == "001"
    board.eaten.add("001")
    assert Selector.next_uneaten(board, m.dots).id == "002"
