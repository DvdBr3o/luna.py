from Parse.Ast import NumLit
import Parse.Ast as Ast
from Eval.Context import Context
import Eval.Val as Val

def test_eval():
    ctx = Context()
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
    val = ast.eval(ctx)
    print(f"{val}")
    
def main():
    pass

if __name__ == "__main__":
    test_eval()
