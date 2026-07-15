from __future__ import annotations
from Eval.Context import Context
import Eval.Val as Val
from dataclasses import dataclass
from typing import Dict
from abc import ABC, abstractmethod
from exceptions import LunaError

# Exceptions

class IdentNotFoundError(LunaError):
    def __init__(self, ident: str) -> None:
        super().__init__(f"Ident `{ident}` not found!")

# Ast 

class Ast(ABC):
    @abstractmethod
    def eval(self, ctx: Context) -> Val.Val:
        pass

@dataclass(frozen = True)
class NumLit(Ast):
    lit: str

    def eval(self, ctx):
        return Val.CstNum(int(self.lit))

@dataclass(frozen = True)
class StrLit(Ast):
    lit: str

    def eval(self, ctx):
        return Val.CstStr(self.lit)

@dataclass(frozen = True)
class Ident(Ast):
    ident: str

    def eval(self, ctx: Context):
        val = ctx.env.lookup(self.ident)
        if val is not None:
            return val
        else:
            raise IdentNotFoundError(self.ident)

@dataclass(frozen = True)
class LetIn(Ast):
    ident: str
    expr: Ast
    body: Ast

    def eval(self, ctx: Context):
        return (
            ctx
                .with_env({
                    self.ident: self.expr.eval(ctx)
                })
                .eval(self.body)
        )

@dataclass(frozen = True)
class Table(Ast):
    tbl: Dict[Ast, Ast]

    def eval(self, ctx):
        return Val.Tbl({ ctx.eval(k): ctx.eval(v) for k, v in self.tbl.items() })

@dataclass(frozen = True)
class Lambda(Ast):
    param: str
    body: Ast

    def eval(self, ctx):
        return Val.Clo(
            env = ctx.env,
            param = self.param,
            body = self.body,
        )

@dataclass(frozen = True)
class Apply(Ast):
    applyer: Ast
    applyee: Ast

    def eval(self, ctx):
        from Eval.Val import Clo, Tbl, BltClo, BltCloCont
        match (ctx.eval(self.applyer), ctx.eval(self.applyee)):
            case (Clo(env, param, body), applyee):
                return (
                    ctx
                        # .with_env(env._env)
                        .with_env({ param: applyee })
                        .eval(body)
                )
            case (Tbl() as tbl, applyee):
                raise NotImplementedError()
            case (BltClo(arity, fn), applyee):
                print("BltClo")
                if arity == 1:
                    return fn([applyee])
                else:
                    return BltCloCont(BltClo(arity, fn), 1, [applyee])
            case (BltCloCont(BltClo(arity, fn), argc, argv), applyee):
                print(f"BltCloCont {argc}")
                if argc + 1 == arity:
                    return fn([*argv, applyee])
                else:
                    return BltCloCont(BltClo(arity, fn), argc + 1, [*argv, applyee])
            case _:
                raise

@dataclass(frozen = True)
class InstantVal(Ast):
    val: Val.Val
    
    def eval(self, ctx: Context) -> Val.Val:
        return self.val