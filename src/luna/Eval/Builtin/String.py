from luna.Eval.Val import Val, CstStr, CstNum, Tbl, builtin
from typing import List


def cat(nil: Tbl):
    @builtin(2)
    def cat_impl(vals: List[Val]):
        [s1, s2] = vals
        match (s1, s2):
            case (CstStr(cs1), CstStr(cs2)):
                return CstStr(b"".join([cs1, cs2]))
            case _:
                return nil

    return cat_impl


def but(nil: Tbl):
    @builtin(3)
    def but_impl(vals: List[Val]):
        [s, idx, bt] = vals
        match (s, idx, bt):
            case (CstStr(cst), CstNum(id), CstNum(b)):
                ss = bytearray(cst)
                ss[int(id)] = int(b)
                return CstStr(ss)
            case _:
                return nil

    return but_impl


def len_(
    nil: Tbl,
):  # TODO: Maybe no nil return? Assure first arg `CstStr` & then no other illegal state?
    @builtin(1)
    def len_impl(vals: List[Val]):
        [s] = vals
        match s:
            case CstStr(cst):
                return CstNum(len(bytearray(cst)))
            case _:
                return nil

    return len_impl


def at(nil: Tbl):
    @builtin(1)
    def at_impl(vals: List[Val]):
        [s, idx] = vals
        match (s, idx):
            case (CstStr(cst), CstNum(id)):
                return CstNum(memoryview(cst)[int(id)])
            case _:
                return nil

    return at_impl


def sub(nil: Tbl):
    @builtin(3)
    def sub_impl(vals: List[Val]):
        [s, beg, end] = vals
        match (s, beg, end):
            case (CstStr(cst), CstNum(b), CstNum(e)):
                return CstStr(memoryview(cst)[int(b) : int(e)])
            case _:
                return nil

    return sub_impl


def equal(nil: Tbl, true: Tbl):
    @builtin(2)
    def equal_impl(vals: List[Val]):
        match (vals[0], vals[1]):
            case (CstStr(lhs), CstStr(rhs)):
                return true if bytes(lhs) == bytes(rhs) else nil
            case _:
                return nil

    return equal_impl


def same(nil: Tbl, true: Tbl):
    @builtin(2)
    def same_impl(vals: List[Val]):
        match (vals[0], vals[1]):
            case (CstStr(lhs), CstStr(rhs)):
                return true if bytes(lhs) == bytes(rhs) else nil
            case _:
                return nil

    return same_impl
