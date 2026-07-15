from Eval.Val import Val, Tag, builtin
from typing import List

@builtin(1)
def nu(vals: List[Val]):
    return Tag()