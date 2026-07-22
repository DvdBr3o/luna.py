import luna.Parse.Rule as Rule
import luna.Parse.Ast as Ast


def test_ident():
    assert Rule.val_ident.parse("hello_world") == Ast.Ident("hello_world")
    assert Rule.val_ident.parse("hello123") == Ast.Ident("hello123")
    assert Rule.op_ident.parse("+=") == Ast.Ident("+=")
    assert Rule.op_ident.parse("**") == Ast.Ident("**")
    assert Rule.lambda_lit.parse("x -> 1") == Ast.Lambda(
        param=Ast.IdentPattern("x"), body=Ast.NumLit("1")
    )


def test_expr_literals_and_comments():
    assert Rule.expr.parse("1") == Ast.NumLit("1")
    assert Rule.expr.parse('"hello world!"') == Ast.StrLit("hello world!")
    assert Rule.expr.parse("[[first line\nsecond line]]") == Ast.StrLit(
        "first line\nsecond line"
    )
    assert Rule.expr.parse("-- overall comment\n1") == Ast.NumLit("1")
    assert Rule.expr.parse("-- [[\nmultiline\n]]\n1") == Ast.NumLit("1")


def test_expr_apply_and_table():
    assert Rule.expr.parse('func val "arg1" 2') == Ast.chain_apply(
        Ast.Ident("func"),
        [
            Ast.Ident("val"),
            Ast.StrLit("arg1"),
            Ast.NumLit("2"),
        ],
    )
    assert Rule.expr.parse("x + y") == Ast.chain_apply(
        Ast.Ident("+"),
        [
            Ast.Ident("x"),
            Ast.Ident("y"),
        ],
    )
    assert Rule.expr.parse("(+) x y") == Ast.chain_apply(
        Ast.Ident("+"),
        [
            Ast.Ident("x"),
            Ast.Ident("y"),
        ],
    )
    assert Rule.expr.parse("{ l1, k1: v1 }") == Ast.Table(
        {
            Ast.NumLit("1"): Ast.Ident("l1"),
            Ast.StrLit("k1"): Ast.Ident("v1"),
        }
    )
    assert Rule.expr.parse("foo.bar") == Ast.FieldAccess(
        Ast.Ident("foo"), "bar"
    )
    assert Rule.expr.parse("foo.1") == Ast.IndexAccess(
        Ast.Ident("foo"),
        Ast.NumLit("1"),
    )
    assert Rule.expr.parse('foo["bar"]') == Ast.IndexAccess(
        Ast.Ident("foo"),
        Ast.StrLit("bar"),
    )
    assert Rule.expr.parse("foo[bar].baz") == Ast.FieldAccess(
        Ast.IndexAccess(Ast.Ident("foo"), Ast.Ident("bar")),
        "baz",
    )
    assert Rule.expr.parse('"1, 2, 3"\n    .split ","\n    .stol') == Ast.Apply(
        Ast.Ident("stol"),
        Ast.chain_apply(
            Ast.Ident("split"),
            [
                Ast.StrLit("1, 2, 3"),
                Ast.StrLit(","),
            ],
        ),
    )
    assert Rule.expr.parse("lib: cffi.lib \"vulkan\"") == Ast.Table(
        {
            Ast.StrLit("lib"): Ast.Apply(
                Ast.FieldAccess(Ast.Ident("cffi"), "lib"),
                Ast.StrLit("vulkan"),
            )
        }
    )
    assert Rule.expr.parse("val .free_dispatch_f1 arg1 arg2 .free_dispatch_f2") == Ast.Apply(
        Ast.Ident("free_dispatch_f2"),
        Ast.chain_apply(
            Ast.Ident("free_dispatch_f1"),
            [
                Ast.Ident("val"),
                Ast.Ident("arg1"),
                Ast.Ident("arg2"),
            ],
        ),
    )


def test_expr_table_paths_and_dynamic_keys():
    assert Rule.expr.parse("{ [value]: v7, 1: v8 }") == Ast.Table(
        {
            Ast.Ident("value"): Ast.Ident("v7"),
            Ast.NumLit("1"): Ast.Ident("v8"),
        }
    )
    assert Rule.expr.parse("{ k6.k62: v62, k6[value]: v6v }") == Ast.Table(
        {
            Ast.StrLit("k6"): Ast.Table(
                {
                    Ast.StrLit("k62"): Ast.Ident("v62"),
                    Ast.Ident("value"): Ast.Ident("v6v"),
                }
            )
        }
    )
    assert Rule.expr.parse(
        "{ k6: { k61: v61 }, k6.k62: v62, k6[value]: v6v }"
    ) == Ast.Table(
        {
            Ast.StrLit("k6"): Ast.Table(
                {
                    Ast.StrLit("k61"): Ast.Ident("v61"),
                    Ast.StrLit("k62"): Ast.Ident("v62"),
                    Ast.Ident("value"): Ast.Ident("v6v"),
                }
            )
        }
    )


def test_expr_let_and_lambda():
    assert Rule.expr.parse("a = 1\na + 1") == Ast.LetIn(
        ident=Ast.IdentPattern("a"),
        expr=Ast.NumLit("1"),
        body=Ast.chain_apply(
            Ast.Ident("+"),
            [
                Ast.Ident("a"),
                Ast.NumLit("1"),
            ],
        ),
    )
    assert Rule.expr.parse("x -> x + 1") == Ast.Lambda(
        param=Ast.IdentPattern("x"),
        body=Ast.chain_apply(
            Ast.Ident("+"),
            [
                Ast.Ident("x"),
                Ast.NumLit("1"),
            ],
        ),
    )
    assert Rule.expr.parse("x ->\n    y = x + 1\n    y * 2") == Ast.Lambda(
        param=Ast.IdentPattern("x"),
        body=Ast.LetIn(
            ident=Ast.IdentPattern("y"),
            expr=Ast.chain_apply(
                Ast.Ident("+"),
                [
                    Ast.Ident("x"),
                    Ast.NumLit("1"),
                ],
            ),
            body=Ast.chain_apply(
                Ast.Ident("*"),
                [
                    Ast.Ident("y"),
                    Ast.NumLit("2"),
                ],
            ),
        ),
    )
    assert Rule.expr.parse("{ l1, l2 } = tbl") == Ast.LetIn(
        ident=Ast.TablePattern(
            positional=(Ast.IdentPattern("l1"), Ast.IdentPattern("l2")),
            named=(),
        ),
        expr=Ast.Ident("tbl"),
        body=Ast.Table({}),
    )
    assert Rule.expr.parse("{ :k1, k2_alias: k2 } = tbl") == Ast.LetIn(
        ident=Ast.TablePattern(
            positional=(),
            named=(("k1", "k1"), ("k2_alias", "k2")),
        ),
        expr=Ast.Ident("tbl"),
        body=Ast.Table({}),
    )


def test_expr_module_table():
    assert Rule.expr.parse(
        'cffi = require "cffi"\n\nlib: cffi.lib "vulkan"\nvkCreateInstance: lib .symbol "vkCreateInstance"'
    ) == Ast.LetIn(
        ident=Ast.IdentPattern("cffi"),
        expr=Ast.Apply(
                Ast.Ident("require"),
                Ast.StrLit("cffi"),
            ),
        body=Ast.Table(
            {
                Ast.StrLit("lib"): Ast.Apply(
                    Ast.FieldAccess(Ast.Ident("cffi"), "lib"),
                    Ast.StrLit("vulkan"),
                ),
                Ast.StrLit("vkCreateInstance"): Ast.Apply(
                    Ast.Apply(Ast.Ident("symbol"), Ast.Ident("lib")),
                    Ast.StrLit("vkCreateInstance"),
                ),
            }
        ),
    )
