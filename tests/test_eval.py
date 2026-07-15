from luna.Parse.Ast import NumLit
import luna.Parse.Ast as Ast
from luna.Eval.Context import Context, Env, eval
import luna.Eval.Val as Val
from dataclasses import dataclass
from functools import reduce
from typing import Any, List
import luna.Eval.Builtin as Builtin
from luna.Parse.Ast import (
    Apply,
    NumLit,
    InstantVal,
    LetIn,
    Lambda,
    Ident,
    Table,
    StrLit,
    chain_apply,
)


def test_eval():
    """
    a = 114514
    (x -> a) "hello"
    """
    ast = Ast.LetIn(
        ident="a",
        expr=Ast.NumLit("114514"),
        body=Ast.Apply(
            applyer=Ast.Lambda(param="x", body=Ast.Ident("a")),
            applyee=Ast.StrLit("hello"),
        ),
    )
    assert eval(ast) == Val.CstNum(114514)


def test_builtin_number():
    assert eval(
        Apply(
            applyer=Apply(
                applyer=InstantVal(Builtin.Number.add),
                applyee=NumLit("1"),
            ),
            applyee=NumLit("2"),
        )
    ) == Val.CstNum(3)

    assert eval(
        Apply(
            applyer=Apply(
                applyer=InstantVal(Builtin.Number.mlt),
                applyee=NumLit("2"),
            ),
            applyee=NumLit("3"),
        )
    ) == Val.CstNum(6)

    """
    foo = x -> builtin.number.add x 1
    foo 2
    """
    assert eval(
        LetIn(
            ident="foo",
            expr=Lambda(
                param="x",
                body=Apply(
                    applyer=Apply(
                        applyer=InstantVal(Builtin.Number.add),
                        applyee=Ident("x"),
                    ),
                    applyee=NumLit("1"),
                ),
            ),
            body=Apply(
                applyer=Ident("foo"),
                applyee=NumLit("2"),
            ),
        )
    ) == Val.CstNum(3)


def test_builtin_table():
    """
    fold { a: "hello", b: "world", c: 1 } 0 init -> k -> v -> init + 1
    """
    assert eval(
        chain_apply(
            InstantVal(Builtin.Table.fold),
            [
                Table(
                    {
                        StrLit("a"): StrLit("hello"),
                        StrLit("b"): StrLit("world"),
                        StrLit("c"): NumLit("1"),
                    }
                ),
                NumLit("0"),
                Lambda(
                    "init",
                    Lambda(
                        "k",
                        Lambda(
                            "v",
                            chain_apply(
                                InstantVal(Builtin.Number.add),
                                [Ident("init"), NumLit("1")],
                            ),
                        ),
                    ),
                ),
            ],
        )
    ) == Val.CstNum(3)


def test_builtin_cfg():
    """
    nil .if "true" "false"
    """
    assert eval(
        chain_apply(
            Ident("if"),
            [
                Ident("nil"),
                StrLit("true"),
                StrLit("false"),
            ],
        )
    ) == Val.CstStr("false")
