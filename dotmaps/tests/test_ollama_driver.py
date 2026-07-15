"""Ollama traveler driver — offline unit tests.

The live all-green traversal is the real proof (see certification probe stats);
these tests cover the driver's parsing/robustness logic without a model server.
"""
from dotmaps.runtime.traveler import _parse_textual_tool_call, _ollama_tool_specs, ToolBox
from dotmaps.models import Map
from conftest import SMOKE_MAP


def test_parses_bare_json_tool_call():
    tc = _parse_textual_tool_call(
        '{"name": "filesystem__write_file", "arguments": {"path": "a.txt", "content": "x"}}'
    )
    assert tc == {"function": {"name": "filesystem__write_file",
                               "arguments": {"path": "a.txt", "content": "x"}}}


def test_parses_fenced_json_tool_call():
    content = 'Sure, I will do that:\n```json\n{"name": "filesystem__mkdir", "arguments": {"path": "d"}}\n```\nDone.'
    tc = _parse_textual_tool_call(content)
    assert tc["function"]["name"] == "filesystem__mkdir"


def test_parses_synonym_keys():
    tc = _parse_textual_tool_call('{"tool": "filesystem__delete", "parameters": {"path": "x"}}')
    assert tc["function"]["name"] == "filesystem__delete"
    assert tc["function"]["arguments"] == {"path": "x"}


def test_rejects_prose_and_garbage():
    assert _parse_textual_tool_call("I have completed the task successfully.") is None
    assert _parse_textual_tool_call('{"name": "x"}') is None          # no arguments
    assert _parse_textual_tool_call('{"arguments": {}}') is None      # no name
    assert _parse_textual_tool_call("{not json}") is None
    assert _parse_textual_tool_call("") is None


def test_tool_specs_expose_real_schemas(tmp_path):
    m = Map.load(SMOKE_MAP)
    ws = tmp_path / "ws"
    ws.mkdir()
    specs = _ollama_tool_specs(ToolBox(m, ws))
    by_name = {s["function"]["name"]: s["function"] for s in specs}
    write = by_name["filesystem__write_file"]
    assert write["parameters"]["required"] == ["path", "content"]
    # nothing outside the whitelist leaked into the spec list (rule 3)
    assert all(n.startswith("filesystem__") for n in by_name)
