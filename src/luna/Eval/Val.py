from __future__ import annotations
from luna.Utils import nu, NuTag
from dataclasses import dataclass, field
from typing import Dict, List, Callable, cast, TYPE_CHECKING
from abc import ABC
from collections.abc import Buffer

if TYPE_CHECKING:
    from luna.Eval.Context import Env
    from Parse.Ast import Ast


class Val(ABC):
    pass


class Lazy(Val):
    def __init__(self, resolver: Callable[[], Val]) -> None:
        self._resolver = resolver
        self._forced = False
        self._forcing = False
        self._value: Val | None = None

    def force(self) -> Val:
        if self._forced:
            return cast(Val, self._value)
        if self._forcing:
            raise RuntimeError("recursive table binding forced cyclically")
        self._forcing = True
        try:
            self._value = self._resolver()
            self._forced = True
            return self._value
        finally:
            self._forcing = False


@dataclass(frozen=True)
class CstNum(Val):
    cst: float


@dataclass(frozen=True)
class CstStr(Val):
    cst: Buffer

    @staticmethod
    def from_strlit(s: str) -> CstStr:
        return CstStr(bytes(s, "utf-8"))


@dataclass(frozen=True)
class Clo(Val):
    env: Env
    param: str
    body: Ast

    def apply(self, arg: Val) -> Val:
        from luna.Eval.Context import Context

        return self.env.with_env({self.param: arg}).eval(self.body)


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
    tag: NuTag = field(default_factory=nu)

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
            init = cast(Clo, cast(Clo, clo.apply(init)).apply(k)).apply(v)
        return init
