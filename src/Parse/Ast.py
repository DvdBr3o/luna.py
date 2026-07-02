from __future__ import annotations
from Eval.Context import Context
import Eval.Val as Val
from dataclasses import dataclass
from typing import Union, Dict
from abc import ABC, abstractmethod

class Ast(ABC):
    @abstractmethod
    def eval(self, ctx: Context) -> Val.Val:
        pass

@dataclass(frozen=True)
class NumLit(Ast):
    lit: str
    
    def eval(self, ctx):
        return Val.CstNum(self.lit)

@dataclass(frozen=True)
class StrLit(Ast):
    lit: str
    
    def eval(self, ctx):
        return Val.CstStr(self.lit)
    
@dataclass(frozen=True)
class Ident(Ast):
    ident: str

    def eval(self, ctx: Context):
        val = ctx.env.lookup(self.ident) 
        if val is not None:
            return val
        else:
            raise 

@dataclass(frozen=True)
class LetIn(Ast):
    ident: str
    expr: Ast
    body: Ast
    
    def eval(self, ctx: Context):
        return self.body.eval(ctx.with_env({
            self.ident: self.expr.eval(ctx)
        }))
    
@dataclass(frozen=True)
class Table(Ast):
    tbl: Dict[Ast, Ast]
    
    def eval(self, ctx):
        return Val.Tbl({ k.eval(ctx): v.eval(ctx) for k, v in self.tbl.items() })

@dataclass(frozen=True)
class Lambda(Ast):
    param: str
    body: Ast
    
    def eval(self, ctx):
        return Val.Clo(
            env = ctx.env,
            param = self.param,
            body = self.body
        )

@dataclass(frozen=True)
class Apply(Ast):
    applyer: Ast
    applyee: Ast
    
    def eval(self, ctx):
        match (self.applyer, self.applyee):
            case (Lambda(param, body), _):
                return body.eval(ctx.with_env({ param: self.applyee.eval(ctx) }))
            case _:
                raise
