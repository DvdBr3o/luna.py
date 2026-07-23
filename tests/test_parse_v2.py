def test_number():
    from luna.Parse.Rules.Number import numlit
    import luna.Parse.Ast as Ast

    assert numlit.parse("123") == Ast.NumLit("123")
    assert numlit.parse("-123.12") == Ast.NumLit("-123.12")


# def test_string():
#     from luna.Parse.Rules.String import
