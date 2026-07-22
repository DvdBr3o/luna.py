from pathlib import Path

from luna.__main__ import main, run_module, stringify
from luna.Eval.Context import Context
from luna.Eval.Val import CstNum, CstStr


TEST_ROOT = (Path(__file__).parent / "test_luna").resolve()


def test_context_resolve_module_path_from_dir():
    ctx = Context(path=TEST_ROOT)
    assert ctx.resolve_module_path("demo.value") == TEST_ROOT / "demo" / "value.luna"


def test_context_resolve_module_path_from_file():
    entry = TEST_ROOT / "demo" / "value.luna"
    ctx = Context(path=entry)
    assert ctx.resolve_module_path("nested.mod") == TEST_ROOT / "demo" / "nested" / "mod.luna"


def test_run_module_returns_module_value():
    assert run_module("demo.value", cwd=TEST_ROOT) == CstStr.from_strlit("hello")


def test_run_module_applies_cli_arg_to_closure():
    assert run_module("demo.identity", ["114"], cwd=TEST_ROOT) == CstNum(114)


def test_run_module_applies_multiple_cli_args_to_curried_closure():
    assert run_module("demo.pair", ["114", "514"], cwd=TEST_ROOT) == CstNum(114)


def test_main_prints_result(monkeypatch, capsys):
    monkeypatch.chdir(TEST_ROOT)

    code = main(["demo.identity", "114"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "114"
    assert captured.err == ""


def test_stringify_host_values():
    assert stringify(CstNum(3)) == "3"
    assert stringify(CstStr.from_strlit("hello")) == "hello"
