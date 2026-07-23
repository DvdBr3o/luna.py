from luna.Eval.Val import Val, Tbl, CstStr, CstNum, Clo, BltClo, BltCloCont, builtin
from typing import List, Dict


def eval(nil: Tbl):
    @builtin(1)
    def eval_impl(vals: List[Val]):
        """
        eval: String |-> Val

        evaluate string script into luna `Val`.
        """
        from luna.Eval.Context import eval as luna_eval
        from luna.Parse.Rule import expr

        [script] = vals
        if isinstance(script, CstStr):
            return luna_eval(expr.parse(bytes(script.cst).decode("utf-8")))
        # TODO: Use `Optional` instead of nil, since the script can be evaled into `nil`.
        return nil

    return eval_impl


@builtin(1)
def decltype(vals: List[Val]):
    """
    decltype: Val |-> String
    """
    match vals[0]:
        case CstNum():
            return CstStr.from_strlit("Number")
        case CstStr():
            return CstStr.from_strlit("String")
        case Tbl():
            return CstStr.from_strlit("Table")
        case Clo():
            return CstStr.from_strlit("Closure")
        case BltClo():
            return CstStr.from_strlit("BuiltinClosure")
        case BltCloCont():
            return CstStr.from_strlit("BuiltinClosureContinuation")

    return decltype
