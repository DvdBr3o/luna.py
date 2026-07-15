from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Callable, cast, TYPE_CHECKING
from abc import ABC, abstractmethod
from collections.abc import Buffer

if TYPE_CHECKING:
    from luna.Eval.Context import Env, Context
    from Parse.Ast import Ast


class Val(ABC):
    pass


@dataclass(frozen=True)
class CstNum(Val):
    cst: float


@dataclass(frozen=True)
class CstStr(Val):
    cst: str


@dataclass(frozen=True)
class Clo(Val):
    env: Env
    param: str
    body: Ast

    def apply(self, arg: Val) -> Val:
        from luna.Eval.Context import Context

        return Context(self.env).with_env({self.param: arg}).eval(self.body)


@dataclass(frozen=True)
class BltClo(Val):
    arity: int
    fn: Callable[[List[Val]], Val]


@dataclass(frozen=True)
class BltCloCont(Val):
    clo: BltClo
    argc: int
    args: List[Val]


def builtin(arity: int):
    def decorator(func: Callable) -> BltClo:
        return BltClo(
            fn=func,
            arity=arity,
        )

    return decorator


@dataclass(frozen=True)
class TableTag:
    tag: object = field(hash=False, default=object())


@dataclass(frozen=True)
class Tbl(Val):
    tbl: Dict[Val, Val] = field(hash=False)
    tag: TableTag = TableTag()

    def without(self, index: Val) -> Tbl:
        """
        tbl .without index
        """
        return Tbl({k: v for k, v in self.tbl.items() if k != index})

    def but(self, index: Val, val: Val) -> Tbl:
        """
        tbl .but key val
        """
        return Tbl({**self.tbl, index: val})

    def at(self, index: Val) -> Val | None:
        """
        tbl .at index
        """
        return self.tbl.get(index)

    def fold(self, init: Val, clo: Clo):
        """
        tbl .fold init init -> k -> v ->...

        e.g.
        len         = tbl -> tbl .fold 0 init -> k -> v -> init + 1
        times2      = tbl -> tbl .fold tbl init -> k -> v tbl .but k (v * 2)
        reverse_kv  = tbl -> tbl .fold tbl init -> k -> v -> tbl .but v k
        """
        for k, v in self.tbl.items():
            print(f"{init}")
            init = cast(Clo, cast(Clo, clo.apply(init)).apply(k)).apply(v)
        print(f"{init}")
        return init
