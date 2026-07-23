from pathlib import Path

from luna.__main__ import main, run_module, stringify
from luna.Eval.Context import Context
from luna.Eval.Val import CstNum, CstStr
from luna.Parse.Rule import expr


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


def test_run_module_add_one_uses_operator_meta_dispatch():
    assert run_module("add_one", ["114"], cwd=TEST_ROOT) == CstNum(115)


def test_context_require_caches_modules():
    ctx = Context(path=TEST_ROOT)
    assert ctx.require_module("match") is ctx.require_module("match")


def test_context_require_shares_exported_meta_identity():
    ctx = Context(path=TEST_ROOT)
    typ_meta = ctx.eval(
        expr.parse(
            """
{ :type } = require "match"
(type Number)[meta]
            """.strip()
        )
    )
    exported_meta = ctx.eval(
        expr.parse(
            """
{ :MatchType } = require "match"
MatchType
            """.strip()
        )
    )
    assert typ_meta is exported_meta


def test_run_module_match_uses_module_relative_require():
    assert run_module("test_match", cwd=TEST_ROOT) == CstNum(4)


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
