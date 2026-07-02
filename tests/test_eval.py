from Eval.Val import Val, Tbl, CstNum

def test_eval():
    val: Val = CstNum("123")
    match val:
        case CstNum(num):
            print(f"Cstnum({num})")
        