import Parse.Rule as Rule
import Parse.Ast as Ast

def test_ident():
    assert Rule.val_ident.parse("hello_world") == Ast.Ident("hello_world")
    assert Rule.val_ident.parse("hello123") == Ast.Ident("hello123")
    assert Rule.op_ident.parse("+=") == Ast.Ident("+=")
    assert Rule.op_ident.parse("**") == Ast.Ident("**")
