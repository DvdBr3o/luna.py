from __future__ import annotations
from luna.Eval.Context import Context, Env
import luna.Eval.Val as Val
from dataclasses import dataclass
from typing import Dict, List, Tuple
from abc import ABC, abstractmethod
from luna.Exceptions import LunaError


# Exceptions
class IdentNotFoundError(LunaError):
    def __init__(self, ident: str) -> None:
        super().__init__(f"Ident `{ident}` not found!")


# Ast
class Ast(ABC):
    @abstractmethod
    def eval(self, env: Env) -> Val.Val:
        pass


def _nil_value(env: Env) -> Val.Val:
    return env.nil()


def _lookup_table(env: Env, obj: Val.Val, index: Val.Val) -> Val.Val:
    if not isinstance(obj, Val.Tbl):
        raise TypeError(f"Cannot index non-table value: {obj!r}")
    value = obj.at(index)
    if value is None:
        return _nil_value(env)
    return value


def _is_operator_ident(ident: str) -> bool:
    return bool(ident) and all(ch in "!@#$%^&*+-?/|~<>=" for ch in ident)


def _resolve_dotted_path_from_value(env: Env, base: Val.Val, path: str) -> Val.Val:
    cur = base
    for part in path.split("."):
        if not part:
            continue
        if isinstance(cur, Val.Tbl):
            nxt = cur.at(Val.CstStr.from_strlit(part))
            if nxt is None:
                return _nil_value(env)
            cur = nxt
        else:
            raise TypeError(f"Cannot resolve path `{path}` from non-table value {cur!r}")
    return cur


def _resolve_dotted_path_from_env(env: Env, path: str) -> Val.Val:
    parts = [part for part in path.split(".") if part]
    if not parts:
        return _nil_value(env)
    cur = env.lookup(parts[0])
    if cur is None:
        return _nil_value(env)
    return _resolve_dotted_path_from_value(env, cur, ".".join(parts[1:])) if len(parts) > 1 else cur


def _literal_binding_name(key: Ast) -> str | None:
    if isinstance(key, StrLit):
        return key.lit
    return None


class Pattern(ABC):
    pass


@dataclass(frozen=True)
class IdentPattern(Pattern):
    ident: str


@dataclass(frozen=True)
class TablePattern(Pattern):
    positional: Tuple[Pattern, ...]
    named: Tuple[Tuple[str, str], ...]


@dataclass(frozen=True)
class NumLit(Ast):
    lit: str

    def eval(self, env):
        return Val.CstNum(int(self.lit))


@dataclass(frozen=True)
class StrLit(Ast):
    lit: str

    def eval(self, env):
        return Val.CstStr(bytes(self.lit, "utf-8"))


@dataclass(frozen=True)
class Ident(Ast):
    ident: str

    def eval(self, env: Env):
        val = env.lookup(self.ident)
        if val is not None:
            return val
        else:
            raise IdentNotFoundError(self.ident)


@dataclass(frozen=True)
class LetIn(Ast):
    ident: str | Pattern
    expr: Ast
    body: Ast

    def eval(self, env: Env):
        match self.ident:
            case str() as ident:
                return env.with_env({ident: self.expr.eval(env)}).eval(self.body)
            case IdentPattern(ident):
                return env.with_env({ident: self.expr.eval(env)}).eval(self.body)
            case TablePattern(positional, named):
                value = self.expr.eval(env)
                if not isinstance(value, Val.Tbl):
                    raise TypeError("Table pattern let expects a table value")
                bindings: Dict[str, Val.Val] = {}
                for i, pat in enumerate(positional, start=1):
                    if not isinstance(pat, IdentPattern):
                        raise NotImplementedError("Nested table pattern let is not implemented yet.")
                    matched = value.at(Val.CstNum(i))
                    if matched is None:
                        raise IdentNotFoundError(pat.ident)
                    bindings[pat.ident] = matched
                for name, target in named:
                    matched = value.at(Val.CstStr.from_strlit(target))
                    if matched is None:
                        raise IdentNotFoundError(target)
                    bindings[name] = matched
                return env.with_env(bindings).eval(self.body)
            case _:
                raise NotImplementedError("Pattern let eval is not implemented yet.")


@dataclass(frozen=True)
class Table(Ast):
    tbl: Dict[Ast, Ast]

    def eval(self, env):
        bindings: Dict[str, Val.Val] = {}
        table_env = env.with_env(bindings)
        for key, value in self.tbl.items():
            ident = _literal_binding_name(key)
            if ident is None:
                continue
            bindings[ident] = Val.Lazy(lambda value=value: table_env.eval(value))
        return Val.Tbl({table_env.eval(k): table_env.eval(v) for k, v in self.tbl.items()})


@dataclass(frozen=True)
class Lambda(Ast):
    param: str | Pattern
    body: Ast

    def eval(self, env: Env):
        match self.param:
            case str() as param:
                bound = param
            case IdentPattern(ident):
                bound = ident
            case TablePattern():
                bound = f"__pattern_arg_{id(self)}__"
                return Val.Clo(
                    env=env,
                    param=bound,
                    body=LetIn(
                        ident=self.param,
                        expr=Ident(bound),
                        body=self.body,
                    ),
                )
            case _:
                raise NotImplementedError("Pattern lambda eval is not implemented yet.")
        return Val.Clo(
            env=env,
            param=bound,
            body=self.body,
        )


@dataclass(frozen=True)
class FieldAccess(Ast):
    obj: Ast
    field: str

    def eval(self, env):
        return _lookup_table(env, env.eval(self.obj), Val.CstStr.from_strlit(self.field))


@dataclass(frozen=True)
class IndexAccess(Ast):
    obj: Ast
    index: Ast

    def eval(self, env):
        return _lookup_table(env, env.eval(self.obj), env.eval(self.index))


@dataclass(frozen=True)
class Apply(Ast):
    applyer: Ast
    applyee: Ast

    def eval(self, env):
        if isinstance(self.applyer, Ident) and self.applyer.ident.startswith("."):
            lhs = env.eval(self.applyee)
            operator = _resolve_dotted_path_from_env(env, self.applyer.ident[1:])
            return env.apply_val(operator, lhs)
        if isinstance(self.applyer, Ident) and self.applyer.ident.startswith("\\"):
            lhs = env.eval(self.applyee)
            operator = _resolve_dotted_path_from_value(
                env,
                env.eval_meta(lhs),
                self.applyer.ident[1:],
            )
            return env.apply_val(operator, lhs)
        if isinstance(self.applyer, Ident) and _is_operator_ident(self.applyer.ident):
            lhs = env.eval(self.applyee)
            operator = env.eval_meta_field(
                lhs,
                Val.CstStr.from_strlit(self.applyer.ident),
            )
            return env.apply_val(operator, lhs)
        return env.apply_val(env.eval(self.applyer), env.eval(self.applyee))


def chain_apply(applyer: Ast, applyees: List[Ast] = []):
    if len(applyees) == 0:
        return applyer

    app = Apply(applyer, applyees[0])
    for applyee in applyees[1:]:
        app = Apply(app, applyee)
    return app


@dataclass(frozen=True)
class InstantVal(Ast):
    val: Val.Val

    def eval(self, env: Env) -> Val.Val:
        return self.val
