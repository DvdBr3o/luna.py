from luna.Eval.Val import Val, CstStr, Tbl, builtin
from typing import List
from pathlib import Path


def load(nil: Tbl, current: Path):
    @builtin(1)
    def load_impl(vals: List[Val]):
        """
        load: String |-> String

        load byte string from path given in string literal. Paths are in filesystem
        style (e.g. "a/b/c.ext").
        """
        [path] = vals
        # raise NotImplementedError()
        match path:
            case CstStr(cst):
                target = current / str(cst)
                if not target.exists():
                    return nil
                return CstStr(target.read_bytes())

    return load_impl


def require(nil: Tbl, current: Path):
    @builtin(1)
    def require_impl(vals: List[Val]):
        """
        require: String |-> Val

        load bytes from path and parse them into luna `Val`. Paths are in module
        style (e.g. "a.b.c").
        """
        from luna.Eval.Builtin.Meta import eval

        [path] = vals
        match path:
            case CstStr(cst):
                eval(nil).fn(
                    [
                        load(nil, current).fn(
                            [
                                CstStr.from_strlit(
                                    str(Path(*str(cst).split(".")).with_suffix(".luna"))
                                )
                            ]
                        )
                    ]
                )

    return require_impl
