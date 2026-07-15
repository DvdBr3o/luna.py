from __future__ import annotations
from typing import Dict, Optional
import Eval.Val as Val
import Parse.Ast as Ast
import Eval.Builtin as Builtin

class Env:
    _env: Dict[str, Val.Val]
    _prev: Optional[Env]

    def __init__(self, 
        env: Dict[str, Val.Val] = {}, 
        prev: Optional[Env] = None
    ) -> None:
        self._env = env
        self._prev = prev
    
    def lookup(self, id: str) -> Optional[Val.Val]:
        if id in self._env:
            return self._env[id]
        else:
            if self._prev is not None:
                return self._prev.lookup(id)
            else:
                return None
            
    def derive(self, env: Dict[str, Val.Val]) -> Env:
        return Env(env=env, prev=self)
    
    @staticmethod
    def default():
        from Eval.Val import CstNum, CstStr, Tbl, Clo, Tag
        import Eval.Builtin as Builtin
        
        meta = Tag()
        tag = Tag()
        Nil  = Tbl({
            tag: Tag()
        })
        
        return Env({
            "table": Tbl({
                CstStr("cat"): Builtin.Table.cat,
                CstStr("but"): Builtin.Table.but,
                CstStr("without"): Builtin.Table.without,
            }),
            "num": Tbl({
                CstStr("add"): Builtin.Number.add,
                CstStr("mns"): Builtin.Number.mns,
                CstStr("mlt"): Builtin.Number.mlt,
                CstStr("div"): Builtin.Number.div,
            }),
            "meta": meta,
            "tag": tag,
            "Nil": Nil,
            "nil": Tbl({
                meta: Nil,
            }),
            # "if": 
        })

class Context:
    env: Env
    
    def __init__(self, env: Env = Env.default()) -> None:
        self.env = env

    def with_env(self, env: Dict[str, Val.Val]) -> "Context":
        self.env = self.env.derive(env)
        return self

    def eval(self, ast: Ast.Ast):
        return ast.eval(self)

    def meta(self):
        return eval(Ast.Ident("meta"))
    
def eval(ast: Ast.Ast):
    return Context().eval(ast)
