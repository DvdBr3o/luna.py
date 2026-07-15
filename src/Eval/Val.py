from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Callable, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from Eval.Context import Env
    from Parse.Ast import Ast

class Val(ABC):
    pass

@dataclass(frozen = True)
class CstNum(Val):
    cst: float

@dataclass(frozen = True)
class CstStr(Val):
    cst: str
    
@dataclass(frozen = True)
class Tag(Val):
    tag: object = object()
    
    @staticmethod
    def nu() -> Tag:
        return Tag(object())

Nil = Tag()

@dataclass(frozen = True) 
class Clo(Val):
    env: Env
    param: str
    body: Ast

@dataclass(frozen = True)
class BltClo(Val):
    arity:  int
    fn:     Callable[[List[Val]], Val]
    
@dataclass(frozen = True)
class BltCloCont(Val):
    clo: BltClo
    argc: int
    args: List[Val]

def builtin(arity: int):
    def decorator(func: Callable) -> BltClo:
        return BltClo(
            fn = func,
            arity = arity,
        )
    return decorator

@dataclass(frozen = True)
class Tbl(Val):
    tbl: Dict[Val, Val]
    
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
        