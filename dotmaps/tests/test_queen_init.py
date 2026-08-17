"""C1: dotmaps init — pick a home folder + linked folders, once."""
from dotmaps.queen import init as init_mod


def test_home_state_none_before_init(tmp_path):
    assert init_mod.home_state(tmp_path / "home.json") is None


def test_run_init_writes_resolved_paths(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    linked = tmp_path / "linked"
    linked.mkdir()
    path = tmp_path / "home.json"
    state = init_mod.run_init(str(home), [str(linked)], path=path)
    assert state["home"] == str(home.resolve())
    assert state["linked"] == [str(linked.resolve())]
    assert state["initialized_at"]

    reread = init_mod.home_state(path)
    assert reread == state


def test_run_init_overwrites_on_rerun(tmp_path):
    path = tmp_path / "home.json"
    a = tmp_path / "a"
    a.mkdir()
    b = tmp_path / "b"
    b.mkdir()
    init_mod.run_init(str(a), path=path)
    second = init_mod.run_init(str(b), path=path)
    assert init_mod.home_state(path)["home"] == str(b.resolve())
    assert second["home"] == str(b.resolve())


def test_scoped_dirs_falls_back_to_demo_workspace_when_uninitialized(tmp_path):
    dirs = init_mod.scoped_dirs(tmp_path / "never.json")
    assert len(dirs) == 1
    assert "seed-ws" in dirs[0]


def test_scoped_dirs_after_init(tmp_path):
    path = tmp_path / "home.json"
    home = tmp_path / "home"
    home.mkdir()
    init_mod.run_init(str(home), path=path)
    assert init_mod.scoped_dirs(path) == [str(home.resolve())]
