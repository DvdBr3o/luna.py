import luna.Parse.Ast as Ast
from luna.Eval.Context import eval
import luna.Eval.Val as Val
import luna.Eval.Builtin as Builtin
from luna.Eval.Context import Context
import luna.Parse.Rule as Rule
from luna.Parse.Ast import (
    Apply,
    FieldAccess,
    IndexAccess,
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


def test_builtin_string():
    nil = Val.Tbl({})
    """
    "hello world!" .len
    """
    assert eval(
        chain_apply(InstantVal(Builtin.String.len_(nil)), [StrLit("hello world!")])
    ) == Val.CstNum(12)

    """
    "hello world!" .sub 6 12
    """
    assert eval(
        chain_apply(
            InstantVal(Builtin.String.sub(nil)),
            [
                StrLit("hello world!"),
                NumLit("6"),
                NumLit("12"),
            ],
        )
    ) == Val.CstStr.from_strlit("world!")


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
    nil .if "true" "false" -- "false"
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
    ) == Val.CstStr.from_strlit("false")

    """
    1 .if "true" "false" -- "true"
    """
    assert eval(
        chain_apply(
            Ident("if"),
            [
                NumLit("1"),
                StrLit("true"),
                StrLit("false"),
            ],
        )
    ) == Val.CstStr.from_strlit("true")

    """
    {} .if "true" "false" -- "true"
    """
    assert eval(
        chain_apply(
            Ident("if"),
            [
                Table({NumLit("1"): StrLit("hello")}),
                StrLit("true"),
                StrLit("false"),
            ],
        )
    ) == Val.CstStr.from_strlit("true")


def test_table_index_eval_variants():
    tbl = Table(
        {
            NumLit("1"): StrLit("hello"),
            StrLit("a"): StrLit("world"),
        }
    )
    assert eval(IndexAccess(tbl, NumLit("1"))) == Val.CstStr.from_strlit("hello")
    assert eval(FieldAccess(tbl, "a")) == Val.CstStr.from_strlit("world")
    assert eval(Apply(tbl, NumLit("1"))) == Val.CstStr.from_strlit("hello")
    assert eval(Apply(tbl, StrLit("a"))) == Val.CstStr.from_strlit("world")


def test_table_index_eval_dynamic_and_missing():
    ast = LetIn(
        ident="value",
        expr=Table({}),
        body=LetIn(
            ident="tbl",
            expr=Table({Ident("value"): StrLit("!"), NumLit("1"): StrLit("hello")}),
            body=Table(
                {
                    StrLit("dynamic"): Apply(Ident("tbl"), Ident("value")),
                    StrLit("indexed"): IndexAccess(Ident("tbl"), Ident("value")),
                    StrLit("missing"): FieldAccess(Ident("tbl"), "missing"),
                    StrLit("nil_ref"): Ident("nil"),
                }
            ),
        ),
    )
    result = eval(ast)
    assert isinstance(result, Val.Tbl)
    assert result.at(Val.CstStr.from_strlit("dynamic")) == Val.CstStr.from_strlit("!")
    assert result.at(Val.CstStr.from_strlit("indexed")) == Val.CstStr.from_strlit("!")
    assert result.at(Val.CstStr.from_strlit("missing")) == result.at(
        Val.CstStr.from_strlit("nil_ref")
    )


def test_table_literal_parse_and_eval_nested_indexing():
    ast = Rule.expr.parse(
        """
value = {}
tbl =
    k6:
        k61: "nested"
    k6.k62: "branch"
    k6[value]: "dynamic"
tbl
        """.strip()
    )
    result = eval(ast)
    assert isinstance(result, Val.Tbl)
    k6 = result.at(Val.CstStr.from_strlit("k6"))
    assert isinstance(k6, Val.Tbl)
    assert k6.at(Val.CstStr.from_strlit("k61")) == Val.CstStr.from_strlit("nested")
    assert k6.at(Val.CstStr.from_strlit("k62")) == Val.CstStr.from_strlit("branch")
    assert (
        eval(
            Rule.expr.parse(
                """
value = {}
tbl =
    k6[value]: "dynamic"
tbl.k6[value]
                """.strip()
            )
        )
        == Val.CstStr.from_strlit("dynamic")
    )


def test_table_literal_local_scope_is_order_independent_and_shadows_outer_env():
    assert (
        eval(
            Rule.expr.parse(
                """
k6 = "outer"
tbl =
    k5: k6.k61
    k6:
        k61: "inner"
tbl.k5
                """.strip()
            )
        )
        == Val.CstStr.from_strlit("inner")
    )


def test_env_eval_meta_field_for_primitives_and_tables():
    env = Context().env
    assert env.eval_meta_field(Val.CstNum(1), Val.CstStr.from_strlit("+")) == Builtin.Number.add
    assert env.eval_meta_field(
        Val.CstStr.from_strlit("hello"), Val.CstStr.from_strlit("len")
    ) == env.lookup("String").at(Val.CstStr.from_strlit("len"))

    meta = env.lookup("meta")
    assert meta is not None
    table = Val.Tbl(
        {
            meta: Val.Tbl(
                {
                    Val.CstStr.from_strlit("greet"): Val.CstStr.from_strlit("world")
                }
            )
        }
    )
    assert env.eval_meta_field(
        table, Val.CstStr.from_strlit("greet")
    ) == Val.CstStr.from_strlit("world")


def test_eval_operator_dispatch():
    assert eval(Rule.expr.parse("1 + 2")) == Val.CstNum(3)
    assert eval(Rule.expr.parse("(x -> x + 1) 41")) == Val.CstNum(42)
