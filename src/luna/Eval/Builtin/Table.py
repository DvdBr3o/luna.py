from luna.Eval.Val import Val, CstNum, Tbl, Clo, builtin
from typing import List, cast


@builtin(2)
def cat(vals: List[Val]):
    match (vals[0], vals[1]):
        case (Tbl(t1), Tbl(t2)):
            return Tbl({**t1, **t2})
        case _:
            raise


@builtin(3)
def but(vals: List[Val]):
    try:
        return cast(Tbl, vals[0]).but(vals[1], vals[2])
    except:
        raise


@builtin(2)
def without(vals: List[Val]):
    try:
        return cast(Tbl, vals[0]).without(vals[1])
    except:
        raise


@builtin(3)
def fold(vals: List[Val]):
    try:
        return cast(Tbl, vals[0]).fold(vals[1], cast(Clo, vals[2]))
    except:
        raise


def equal(nil: Tbl, true: Tbl):
    @builtin(2)
    def equal_impl(vals: List[Val]):
        match (vals[0], vals[1]):
            case (Tbl(lhs), Tbl(rhs)):
                return true if lhs == rhs else nil
            case _:
                return nil

    return equal_impl


def same(nil: Tbl, true: Tbl):
    @builtin(2)
    def same_impl(vals: List[Val]):
        match (vals[0], vals[1]):
            case (Tbl() as lhs, Tbl() as rhs):
                return true if lhs.tag == rhs.tag else nil
            case _:
                return nil

    return same_impl
