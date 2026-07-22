from luna.Eval.Val import Val, Tbl, BltClo, Clo, builtin
from typing import List, cast


def if_(nil: Tbl) -> BltClo:
    @builtin(3)
    def if_impl(vals: List[Val]):
        [pred, br_true, br_false] = vals

        match pred:
            case Tbl() as pred:
                if pred.tag == nil.tag:
                    return br_false
                else:
                    return br_true
            case _:
                return br_true

    return if_impl


def and_(nil: Tbl) -> BltClo:
    @builtin(2)
    def and_impl(vals: List[Val]):
        [lhs, rhs] = vals
        if lhs is Tbl and cast(Tbl, lhs).tag == nil.tag:
            return nil
        else:
            match rhs:
                case Clo(env, param, body):
                    return env.with_env({param: nil}).eval(body)
                case _:
                    return rhs

    return and_impl


def or_(nil: Tbl) -> BltClo:
    @builtin(2)
    def or_impl(vals: List[Val]):
        [lhs, rhs] = vals
        if lhs is Tbl and cast(Tbl, lhs).tag == nil.tag:
            return rhs
        else:
            match rhs:
                case Clo(env, param, body):
                    return env.with_env({param: nil}).eval(body)
                case _:
                    return rhs

    return or_impl
