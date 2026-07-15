from Eval.Val import Val, CstNum, Tbl, builtin
from typing import List, cast

@builtin(2)
def cat(vals: List[Val]):
    match (vals[0], vals[1]):
        case (Tbl(t1), Tbl(t2)):
            return Tbl({ **t1, **t2 })
        case _:
            raise

@builtin(3)
def but(vals: List[Val]):
    try:
        return cast(Tbl, vals[0]).but(vals[1], vals[2])
    finally:
        raise

@builtin(2)
def without(vals: List[Val]):
    try:
        return cast(Tbl, vals[0]).without(vals[1])
    finally:
        raise