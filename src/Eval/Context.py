from __future__ import annotations
from typing import Dict, Optional
import Eval.Val as Val

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

class Context:
    env: Env
    
    def __init__(self, env: Env = Env()) -> None:
        self.env = env
    
    def with_env(self, env: Dict[str, Val.Val]) -> "Context":
        self.env = self.env.derive(env)
        return self
