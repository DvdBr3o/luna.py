from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from Eval.Context import Env
    from Parse.Ast import Ast
    
class Val(ABC):
    pass

@dataclass(frozen=True)
class CstNum(Val):
    cst: str
    
@dataclass(frozen=True)
class CstStr(Val):
    cst: str
    
@dataclass(frozen=True) 
class Clo(Val):
    env: Env
    param: str
    body: Ast
    
@dataclass(frozen=True)
class Tbl(Val):
    tbl: Dict[Val, Val]
