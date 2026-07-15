import luna.Parse.Rule as Rule
import luna.Parse.Ast as Ast


def test_ident():
    assert Rule.val_ident.parse("hello_world") == Ast.Ident("hello_world")
    assert Rule.val_ident.parse("hello123") == Ast.Ident("hello123")
    assert Rule.op_ident.parse("+=") == Ast.Ident("+=")
    assert Rule.op_ident.parse("**") == Ast.Ident("**")
    assert Rule.lambda_lit.parse("x -> 1") == Ast.Lambda(
        param="x", body=Ast.NumLit("1")
    )
