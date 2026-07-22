import argparse
import sys
from collections.abc import Buffer
from pathlib import Path

from luna.Eval.Context import Context
from luna.Eval.Val import BltClo, BltCloCont, Clo, CstNum, CstStr, Tbl, Val
from luna.Exceptions import LunaError
from luna.Parse.Rule import expr


class CliUsageError(LunaError):
    pass


def stringify(val: Val) -> str:
    match val:
        case CstNum(cst):
            if isinstance(cst, float) and cst.is_integer():
                return str(int(cst))
            return str(cst)
        case CstStr(cst):
            if isinstance(cst, Buffer):
                return bytes(cst).decode("utf-8")
            return str(cst)
        case Tbl(tbl):
            inner = ", ".join(
                f"{stringify(key)}: {stringify(value)}" for key, value in tbl.items()
            )
            return f"{{{inner}}}"
        case Clo() as clo:
            return f"{clo}"
        case BltClo():
            return "<builtin>"
        case BltCloCont():
            return "<builtin-cont>"
        case _:
            return repr(val)


def eval_arg(context: Context, arg_expr: str) -> Val:
    return context.eval(expr.parse(arg_expr))


def run_module(
    module_ref: str, arg_exprs: list[str] | None = None, cwd: Path | None = None
) -> Val:
    context = Context(path=cwd or Path.cwd())
    module_context = context.child_for_module(module_ref)
    result = module_context.eval(module_context.parse_path(module_context.path))
    arg_exprs = arg_exprs or []

    if not arg_exprs:
        if isinstance(result, Clo):
            raise CliUsageError(
                f"Module `{module_ref}` evaluated to a closure, but no CLI arg was provided."
            )
        return result

    for arg_expr in arg_exprs:
        if not isinstance(result, Clo):
            raise CliUsageError(
                f"Module `{module_ref}` accepted fewer CLI args than provided."
            )
        result = result.apply(eval_arg(module_context, arg_expr))

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="luna CLI v0.1.0")
    parser.add_argument("module", help="module path in a.b.c style")
    parser.add_argument(
        "args",
        nargs="*",
        help="luna expressions passed into the module result from left to right when it is a closure",
    )
    args = parser.parse_args(argv)

    try:
        result = run_module(args.module, args.args)
    except LunaError as err:
        print(str(err), file=sys.stderr)
        return 1

    print(stringify(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
