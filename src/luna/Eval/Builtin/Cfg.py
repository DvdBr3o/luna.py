from luna.Eval.Val import Val, CstNum, Tbl, BltClo, builtin
import luna.Eval.Builtin as Builtin
from typing import List, cast


def if_(nil: Val) -> BltClo:
    @builtin(3)
    def if_impl(vals: List[Val]):
        try:
            pred = vals[0]
            br_true = vals[1]
            br_false = vals[2]

            if cast(Tbl, pred).tag == cast(Tbl, nil).tag:
                return br_false
            else:
                return br_true
        except:
            raise

    return if_impl
