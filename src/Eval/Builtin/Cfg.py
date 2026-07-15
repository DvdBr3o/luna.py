from Eval.Val import Val, CstNum, Tbl, builtin
from typing import List, cast

@builtin(3)
def if_(vals: List[Val]):
    pred = vals[0]
    br_true = vals[1]
    br_false = vals[2]
