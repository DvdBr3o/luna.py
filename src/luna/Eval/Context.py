from __future__ import annotations
import luna.Eval.Val as Val
from luna.Eval.Val import CstStr, Tbl
import luna.Parse.Ast as Ast
import luna.Eval.Builtin as Builtin
from typing import Dict, Optional
from pathlib import Path
from luna.Exceptions import LunaError


class ModuleResolutionError(LunaError):
    def __init__(self, module_path: str, base_path: Path) -> None:
        super().__init__(
            f"Cannot resolve luna module `{module_path}` relative to `{base_path}`."
        )


class ModuleNotFoundError(LunaError):
    def __init__(self, target: Path) -> None:
        super().__init__(f"Luna module file not found: `{target}`")


class Env:
    _env: Dict[str, Val.Val]
    _prev: Optional[Env]

    def __init__(
        self, env: Optional[Dict[str, Val.Val]] = None, prev: Optional[Env] = None
    ) -> None:
        self._env = env if env is not None else {}
        self._prev = prev

    def with_env(self, env: Dict[str, Val.Val]) -> "Env":
        return self.derive(env)

    def eval(self, ast: Ast.Ast):
        return ast.eval(self)

    def lookup(self, id: str) -> Optional[Val.Val]:
        if id in self._env:
            value = self._env[id]
            if isinstance(value, Val.Lazy):
                return value.force()
            return value
        else:
            if self._prev is not None:
                return self._prev.lookup(id)
            else:
                return None

    def derive(self, env: Dict[str, Val.Val]) -> Env:
        return Env(env=env, prev=self)

    @staticmethod
    def default():
        cststr = CstStr.from_strlit

        meta = Tbl({})
        Nil = Tbl({})
        nil = Tbl(
            {
                meta: Nil,
            }
        )

        return Env(
            {
                "table": Tbl(
                    {
                        cststr("cat"): Builtin.Table.cat,
                        cststr("but"): Builtin.Table.but,
                        cststr("without"): Builtin.Table.without,
                        cststr("equal"): Builtin.Table.equal,
                        cststr("same"): Builtin.Table.same,
                        cststr("=="): Builtin.Table.equal,
                        cststr("==="): Builtin.Table.same,
                    }
                ),
                "number": Tbl(
                    {
                        cststr("add"): Builtin.Number.add,
                        cststr("mns"): Builtin.Number.mns,
                        cststr("div"): Builtin.Number.div,
                        cststr("mlt"): Builtin.Number.mlt,
                        cststr("+"): Builtin.Number.add,
                        cststr("-"): Builtin.Number.mns,
                        cststr("*"): Builtin.Number.mlt,
                        cststr("/"): Builtin.Number.div,
                    }
                ),
                "string": Tbl(
                    {
                        cststr("cat"): Builtin.String.cat(nil),
                        cststr("but"): Builtin.String.but(nil),
                        cststr("len"): Builtin.String.len_(nil),
                        cststr("at"): Builtin.String.at(nil),
                        cststr("sub"): Builtin.String.sub(nil),
                    }
                ),
                "meta": meta,
                "type": Tbl(
                    {
                        meta: Tbl(
                            {
                                # TODO:
                            }
                        ),
                        cststr("CstNum"): Tbl({}),
                        cststr("CstStr"): Tbl({}),
                        cststr("Tbl"): Tbl({}),
                        cststr("Clo"): Tbl({}),
                        cststr("BltClo"): Tbl({}),
                        cststr("BltCloCont"): Tbl({}),
                    }
                ),
                "Nil": Nil,
                "nil": nil,
                "false": nil,
                "true": Tbl({}),
                "if": Builtin.Cfg.if_(nil),
            }
        )


class Context:
    path: Path
    env: Env

    def __init__(self, path: Optional[Path] = None, env: Optional[Env] = None) -> None:
        self.path = (path or Path.cwd()).resolve()
        self.env = env or Env.default()

    def with_env(self, env: Dict[str, Val.Val]) -> "Context":
        self.env = self.env.derive(env)
        return self

    def with_path(self, path: Path) -> "Context":
        self.path = path.resolve()
        return self

    @property
    def module_base(self) -> Path:
        return self.path if self.path.is_dir() else self.path.parent

    @staticmethod
    def module_ref_to_path(module_ref: str) -> Path:
        parts = [part for part in module_ref.split(".") if part]
        if not parts:
            raise ModuleResolutionError(module_ref, Path.cwd())
        return Path(*parts).with_suffix(".luna")

    def resolve_module_path(self, module_ref: str) -> Path:
        rel = self.module_ref_to_path(module_ref)
        target = (self.module_base / rel).resolve()
        try:
            target.relative_to(self.module_base.resolve())
        except ValueError as err:
            raise ModuleResolutionError(module_ref, self.module_base) from err
        return target

    def read_module(self, module_ref: str) -> str:
        target = self.resolve_module_path(module_ref)
        return self.read_path(target)

    def read_path(self, target: Path) -> str:
        if not target.exists() or not target.is_file():
            raise ModuleNotFoundError(target)
        return target.read_text(encoding="utf-8")

    def parse_module(self, module_ref: str) -> Ast.Ast:
        from luna.Parse.Rule import expr

        return expr.parse(self.read_module(module_ref))

    def parse_path(self, target: Path) -> Ast.Ast:
        from luna.Parse.Rule import expr

        return expr.parse(self.read_path(target))

    def child_for_module(self, module_ref: str) -> "Context":
        return Context(path=self.resolve_module_path(module_ref), env=self.env)

    def eval_module(self, module_ref: str) -> Val.Val:
        target = self.resolve_module_path(module_ref)
        child = Context(path=target, env=self.env)
        return child.eval(child.parse_path(target))

    def eval(self, ast: Ast.Ast):
        return ast.eval(self.env)

    def meta(self):
        return eval(Ast.Ident("meta"))


def eval(ast: Ast.Ast):
    return Context().eval(ast)
