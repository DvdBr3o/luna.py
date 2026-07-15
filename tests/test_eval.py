from Parse.Ast import NumLit
import Parse.Ast as Ast
from Eval.Context import Context, Env, eval
import Eval.Val as Val
from dataclasses import dataclass
from functools import reduce
from typing import Any, List
import Eval.Builtin as Builtin

def test_eval():
    """
    a = 114514
    (x -> a) "hello"
    """
    ast = Ast.LetIn(
        ident = "a",
        expr = Ast.NumLit("114514"),
        body = Ast.Apply(
            applyer = Ast.Lambda(
                param = "x",
                body = Ast.Ident("a")
            ),
            applyee = Ast.StrLit("hello")
        )
    )
    assert eval(ast) == Val.CstNum(114514)

def test_arith_num():
    from Parse.Ast import Apply, NumLit, InstantVal
    
    assert eval(Apply(
        applyer = Apply(
            applyer = InstantVal(Builtin.Number.add),
            applyee = NumLit("1"),
        ),
        applyee = NumLit("2"),
    )) == Val.CstNum(3)
    
    assert eval(Apply(
        applyer = Apply(
            applyer = InstantVal(Builtin.Number.mlt),
            applyee = NumLit("2"),
        ),
        applyee = NumLit("3"),
    )) == Val.CstNum(6)
