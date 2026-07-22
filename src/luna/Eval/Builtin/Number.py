from luna.Eval.Val import Val, CstNum, Tbl, builtin
from typing import List


@builtin(2)
def add(vals: List[Val]) -> Val:
    match (vals[0], vals[1]):
        case (CstNum(num0), CstNum(num1)):
            return CstNum(num0 + num1)
        case _:
            raise


@builtin(2)
def mns(vals: List[Val]) -> Val:
    match (vals[0], vals[1]):
        case (CstNum(num0), CstNum(num1)):
            return CstNum(num0 - num1)
        case _:
            raise


@builtin(2)
def mlt(vals: List[Val]) -> Val:
    match (vals[0], vals[1]):
        case (CstNum(num0), CstNum(num1)):
            return CstNum(num0 * num1)
        case _:
            raise


@builtin(2)
def div(vals: List[Val]) -> Val:
    match (vals[0], vals[1]):
        case (CstNum(num0), CstNum(num1)):
            return CstNum(num0 / num1)
        case _:
            raise


def equal(nil: Tbl, true: Tbl):
    @builtin(2)
    def equal_impl(vals: List[Val]) -> Val:
        match (vals[0], vals[1]):
            case (CstNum(num0), CstNum(num1)):
                return true if num0 == num1 else nil
            case _:
                return nil

    return equal_impl


def same(nil: Tbl, true: Tbl):
    @builtin(2)
    def same_impl(vals: List[Val]) -> Val:
        match (vals[0], vals[1]):
            case (CstNum(num0), CstNum(num1)):
                return true if num0 == num1 else nil
            case _:
                return nil

    return same_impl
