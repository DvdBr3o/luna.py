from luna.Eval.Val import Val, Tbl, CstStr, builtin
from typing import List, Dict, cast


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
        if script is CstStr:
            return luna_eval(expr.parse(str(cast(CstStr, script).cst)))
        else:
            # TODO: Use `Optional` instead of nil, since the script can be evaled into `nil`.
            return nil

    return eval_impl


def type_(typetable: Dict[str, Tbl]):
    """
    type: Val |-> Tbl

    where `Tbl` being type of result is actually for tagging.
    """

    @builtin(1)
    def type_impl(vals: List[Val]):
        return typetable[vals[0].__class__.__name__]

    return type_impl
