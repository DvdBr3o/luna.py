from __future__ import annotations

import ast as py_ast
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

import luna.Parse.Ast as Ast


@dataclass(frozen=True)
class Token:
    kind: str
    value: str = ""


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def _is_ident_part(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _is_op_start(ch: str) -> bool:
    return ch in "!@#$%^&*+-?/|~<>"


def _table_field_key(name: str) -> Ast.StrLit:
    return Ast.StrLit(name)


def _table_numeric_key(num: str) -> Ast.NumLit:
    return Ast.NumLit(num)


def _nested_table_from_path(path: Sequence[Ast.Ast], value: Ast.Ast) -> Ast.Table:
    if not path:
        raise ValueError("table path cannot be empty")
    expr = value
    for key in reversed(path[1:]):
        expr = Ast.Table({key: expr})
    return Ast.Table({path[0]: expr})


def _merge_table_ast(lhs: Ast.Table, rhs: Ast.Table) -> Ast.Table:
    merged = dict(lhs.tbl)
    for key, value in rhs.tbl.items():
        if key in merged:
            current = merged[key]
            if isinstance(current, Ast.Table) and isinstance(value, Ast.Table):
                merged[key] = _merge_table_ast(current, value)
            elif current != value:
                raise ValueError(f"conflicting table declarations for key {key!r}")
        else:
            merged[key] = value
    return Ast.Table(merged)


class _Tokenizer:
    def __init__(self, src: str) -> None:
        self.src = src
        self.i = 0
        self.tokens: List[Token] = []
        self.indents = [0]
        self.line_start = True
        self.pending_space = False

    def _peek(self, n: int = 0) -> str:
        j = self.i + n
        return self.src[j] if j < len(self.src) else ""

    def _emit(self, kind: str, value: str = "") -> None:
        self.tokens.append(Token(kind, value))

    def tokenize(self) -> List[Token]:
        while self.i < len(self.src):
            if self.line_start:
                indent = 0
                while self._peek() == " ":
                    indent += 1
                    self.i += 1
                while self._peek() == "\t":
                    indent += 4
                    self.i += 1
                if self.src.startswith("--[[", self.i) or self.src.startswith("-- [[", self.i):
                    end = self.src.find("]]", self.i + 4)
                    self.i = len(self.src) if end < 0 else end + 2
                    continue
                if self.src.startswith("--", self.i):
                    end = self.src.find("\n", self.i)
                    self.i = len(self.src) if end < 0 else end
                    continue
                if self._peek() == "\n":
                    self.i += 1
                    continue
                if indent > self.indents[-1]:
                    self.indents.append(indent)
                    self._emit("INDENT")
                else:
                    while indent < self.indents[-1]:
                        self.indents.pop()
                        self._emit("DEDENT")
                self.line_start = False
                self.pending_space = indent > 0
                continue
            ch = self._peek()
            if ch in " \t":
                self.pending_space = True
                self.i += 1
                continue
            if ch == "\r":
                self.i += 1
                continue
            if ch == "\n":
                j = self.i + 1
                while j < len(self.src) and self.src[j] in " \t":
                    j += 1
                if j < len(self.src) and self.src[j] == "." and j + 1 < len(self.src) and _is_ident_start(self.src[j + 1]):
                    self.i = j
                    self.pending_space = True
                    self.line_start = False
                    continue
                self._emit("NEWLINE")
                self.i += 1
                self.line_start = True
                self.pending_space = False
                continue
            if self.src.startswith("--[[", self.i) or self.src.startswith("-- [[", self.i):
                end = self.src.find("]]", self.i + 4)
                self.i = len(self.src) if end < 0 else end + 2
                continue
            if self.src.startswith("--", self.i):
                end = self.src.find("\n", self.i)
                self.i = len(self.src) if end < 0 else end
                continue
            if self.src.startswith("[[", self.i):
                end = self.src.find("]]", self.i + 2)
                if end < 0:
                    raise ValueError("Unclosed block string")
                self._emit("STR", self.src[self.i + 2 : end])
                self.i = end + 2
                self.pending_space = False
                continue
            if ch == '"':
                j = self.i + 1
                esc = False
                while j < len(self.src):
                    c = self.src[j]
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == '"':
                        break
                    j += 1
                if j >= len(self.src):
                    raise ValueError("Unclosed string")
                self._emit("STR", py_ast.literal_eval(self.src[self.i : j + 1]))
                self.i = j + 1
                self.pending_space = False
                continue
            if ch in "{}()[],:=":
                self._emit(ch)
                self.i += 1
                self.pending_space = False
                continue
            if self.src.startswith("->", self.i):
                self._emit("ARROW")
                self.i += 2
                self.pending_space = False
                continue
            if ch == ".":
                j = self.i + 1
                if j < len(self.src) and _is_ident_start(self._peek(1)):
                    while j < len(self.src) and _is_ident_part(self.src[j]):
                        j += 1
                    if self.pending_space:
                        self._emit("DISPATCH", self.src[self.i + 1 : j])
                    else:
                        self._emit(".", self.src[self.i + 1 : j])
                    self.i = j
                    self.pending_space = False
                    continue
                if j < len(self.src) and self.src[j].isdigit() and not self.pending_space:
                    while j < len(self.src) and self.src[j].isdigit():
                        j += 1
                    self._emit(".", self.src[self.i + 1 : j])
                    self.i = j
                    self.pending_space = False
                    continue
                self._emit(".")
                self.i += 1
                self.pending_space = False
                continue
            if _is_ident_start(ch):
                j = self.i + 1
                while j < len(self.src) and _is_ident_part(self.src[j]):
                    j += 1
                self._emit("IDENT", self.src[self.i:j])
                self.i = j
                self.pending_space = False
                continue
            if _is_op_start(ch):
                j = self.i + 1
                while j < len(self.src) and self.src[j] in "!@#$%^&*+-?/|~<>=":
                    j += 1
                self._emit("OP", self.src[self.i:j])
                self.i = j
                self.pending_space = False
                continue
            if ch.isdigit() or (ch == "-" and self._peek(1).isdigit()):
                j = self.i + 1 if ch == "-" else self.i
                while j < len(self.src) and self.src[j].isdigit():
                    j += 1
                if j < len(self.src) and self.src[j] == "." and j + 1 < len(self.src) and self.src[j + 1].isdigit():
                    j += 1
                    while j < len(self.src) and self.src[j].isdigit():
                        j += 1
                self._emit("NUM", self.src[self.i:j])
                self.i = j
                self.pending_space = False
                continue
            raise ValueError(f"Unexpected char {ch!r}")
        while len(self.indents) > 1:
            self.indents.pop()
            self._emit("DEDENT")
        self._emit("EOF")
        return self.tokens


class _Parser:
    def __init__(self, src: str) -> None:
        self.tokens = _Tokenizer(src).tokenize()
        self.i = 0

    def _peek(self, n: int = 0) -> Token:
        j = self.i + n
        return self.tokens[j] if j < len(self.tokens) else Token("EOF")

    def _accept(self, kind: str, value: str | None = None) -> Optional[Token]:
        tok = self._peek()
        if tok.kind == kind and (value is None or tok.value == value):
            self.i += 1
            return tok
        return None

    def _expect(self, kind: str, value: str | None = None) -> Token:
        tok = self._accept(kind, value)
        if tok is None:
            raise ValueError(f"expected {kind}")
        return tok

    def _skip_newlines(self) -> None:
        while self._accept("NEWLINE"):
            pass

    def parse(self) -> Ast.Ast:
        expr = self._parse_block()
        self._skip_newlines()
        self._expect("EOF")
        return expr

    def _parse_block(self, stop: Iterable[str] = ()) -> Ast.Ast:
        stop = set(stop)
        stmts: List[object] = []
        self._skip_newlines()
        while (
            self._peek().kind not in stop
            and self._peek().kind not in {"EOF", "}", "DEDENT"}
        ):
            if self._peek().kind == "NEWLINE":
                self._skip_newlines()
                continue
            stmts.append(self._parse_stmt())
            self._skip_newlines()
        return self._collapse_block(stmts)

    def _collapse_block(self, stmts: List[object]) -> Ast.Ast:
        if not stmts:
            return Ast.Table({})
        lets = [stmt for stmt in stmts if isinstance(stmt, tuple) and stmt[0] == "let"]
        exprs = [
            Ast.Table(stmt[1])
            if isinstance(stmt, tuple) and stmt[0] == "table"
            else stmt
            for stmt in stmts
            if not (isinstance(stmt, tuple) and stmt[0] == "let")
        ]
        if len(exprs) > 1 and all(isinstance(expr, Ast.Table) for expr in exprs):
            tbl = Ast.Table({})
            for expr in exprs:
                tbl = _merge_table_ast(tbl, expr)
            expr = tbl
        else:
            expr = exprs[-1] if exprs else Ast.Table({})
        for stmt in reversed(lets):
            expr = Ast.LetIn(stmt[1], stmt[2], expr)
        return expr

    def _parse_indented_block(self) -> Ast.Ast:
        self._expect("INDENT")
        body = self._parse_block()
        self._expect("DEDENT")
        return body

    def _parse_stmt(self):
        if self._looks_like_let():
            pat = self._parse_pattern()
            self._expect("=")
            if self._accept("NEWLINE"):
                value = self._parse_indented_block()
            else:
                value = self._parse_expr()
            return ("let", pat, value)
        if self._looks_like_table_item():
            return self._parse_table_items()
        return self._parse_expr()

    def _looks_like_let(self) -> bool:
        save = self.i
        try:
            self._parse_pattern()
            ok = self._accept("=") is not None
            return ok
        except Exception:
            return False
        finally:
            self.i = save

    def _looks_like_table_item(self) -> bool:
        save = self.i
        try:
            self._parse_table_key_path()
            return self._accept(":") is not None
        except Exception:
            return False
        finally:
            self.i = save

    def _parse_pattern(self):
        if self._accept("{"):
            positional = []
            named = []
            self._skip_newlines()
            if not self._accept("}"):
                while True:
                    if self._accept(":"):
                        name = self._expect("IDENT").value
                        named.append((name, name))
                    else:
                        first = self._expect("IDENT").value
                        if self._accept(":"):
                            key = self._expect("IDENT").value
                            named.append((first, key))
                        else:
                            positional.append(Ast.IdentPattern(first))
                    if self._accept("}"):
                        break
                    self._accept(",")
                    self._skip_newlines()
            return Ast.TablePattern(tuple(positional), tuple(named))
        return Ast.IdentPattern(self._expect("IDENT").value)

    def _parse_table_path_atom(self):
        if self._accept("["):
            key = self._parse_expr()
            self._expect("]")
            return key
        tok = self._peek()
        if tok.kind == "IDENT":
            self.i += 1
            return _table_field_key(tok.value)
        if tok.kind == "NUM":
            self.i += 1
            return _table_numeric_key(tok.value)
        raise ValueError("expected table key")

    def _parse_table_key_path(self):
        path = [self._parse_table_path_atom()]
        while True:
            dot = self._accept(".")
            if dot is not None:
                if not dot.value:
                    raise ValueError("expected table field after '.'")
                if dot.value.lstrip("-").isdigit():
                    path.append(_table_numeric_key(dot.value))
                else:
                    path.append(_table_field_key(dot.value))
                continue
            if self._accept("["):
                path.append(self._parse_expr())
                self._expect("]")
                continue
            break
        return path

    def _parse_table_items(self):
        tbl = Ast.Table({})
        positional_index = 1
        saw_positional = False
        while True:
            if self._looks_like_table_item():
                key_path = self._parse_table_key_path()
                self._expect(":")
                if self._accept("NEWLINE"):
                    value = self._parse_indented_block()
                else:
                    value = self._parse_expr()
                if (
                    len(key_path) == 1
                    and isinstance(key_path[0], Ast.NumLit)
                    and key_path[0].lit.isdigit()
                ):
                    if saw_positional:
                        raise ValueError(
                            "implicit list entries conflict with explicit numeric table keys"
                        )
                tbl = _merge_table_ast(tbl, _nested_table_from_path(key_path, value))
            else:
                value = self._parse_expr()
                saw_positional = True
                tbl = _merge_table_ast(
                    tbl,
                    Ast.Table({_table_numeric_key(str(positional_index)): value}),
                )
                positional_index += 1
            if not self._accept(","):
                break
        return ("table", tbl.tbl)

    def _parse_atom(self):
        tok = self._peek()
        if tok.kind == "NUM":
            self.i += 1
            return Ast.NumLit(tok.value)
        if tok.kind == "STR":
            self.i += 1
            return Ast.StrLit(tok.value)
        if tok.kind == "IDENT":
            self.i += 1
            return Ast.Ident(tok.value)
        if tok.kind == "OP":
            self.i += 1
            return Ast.Ident(tok.value)
        if tok.kind == "(":
            self.i += 1
            expr = self._parse_expr()
            self._expect(")")
            return expr
        if tok.kind == "{":
            self.i += 1
            tbl = Ast.Table({})
            positional_index = 1
            saw_positional = False
            self._skip_newlines()
            if not self._accept("}"):
                while True:
                    if self._looks_like_table_item():
                        key_path = self._parse_table_key_path()
                        self._expect(":")
                        if self._accept("NEWLINE"):
                            value = self._parse_indented_block()
                        else:
                            value = self._parse_expr()
                        if (
                            len(key_path) == 1
                            and isinstance(key_path[0], Ast.NumLit)
                            and key_path[0].lit.isdigit()
                        ):
                            if saw_positional:
                                raise ValueError(
                                    "implicit list entries conflict with explicit numeric table keys"
                                )
                        tbl = _merge_table_ast(
                            tbl,
                            _nested_table_from_path(key_path, value),
                        )
                    else:
                        value = self._parse_expr()
                        saw_positional = True
                        tbl = _merge_table_ast(
                            tbl,
                            Ast.Table(
                                {_table_numeric_key(str(positional_index)): value}
                            ),
                        )
                        positional_index += 1
                    self._skip_newlines()
                    if self._accept("}"):
                        break
                    self._accept(",")
                    self._skip_newlines()
            return tbl
        raise ValueError(f"unexpected token {tok.kind}")

    def _parse_lambda_if_any(self):
        save = self.i
        try:
            pat = self._parse_pattern()
            if self._accept("ARROW"):
                if self._peek().kind == "NEWLINE":
                    self._skip_newlines()
                    body = self._parse_indented_block()
                else:
                    body = self._parse_expr()
                return Ast.Lambda(param=pat, body=body)
        except Exception:
            pass
        self.i = save
        return None

    def _parse_expr(self):
        if self._looks_like_table_item():
            return Ast.Table(self._parse_table_items()[1])
        lam = self._parse_lambda_if_any()
        if lam is not None:
            return lam
        return self._parse_operator_expr()

    def _parse_operator_expr(self):
        expr = self._parse_postfix()
        while self._peek().kind == "OP":
            op = Ast.Ident(self._expect("OP").value)
            rhs = self._parse_postfix()
            expr = Ast.chain_apply(op, [expr, rhs])
        return expr

    def _parse_postfix(self):
        expr = self._parse_atom()
        while True:
            dot = self._accept(".")
            if dot is not None:
                field = dot.value or self._expect("IDENT").value
                if field.lstrip("-").isdigit():
                    expr = Ast.IndexAccess(expr, Ast.NumLit(field))
                else:
                    expr = Ast.FieldAccess(expr, field)
                continue
            if self._accept("["):
                index = self._parse_expr()
                self._expect("]")
                expr = Ast.IndexAccess(expr, index)
                continue
            if self._peek().kind == "DISPATCH":
                name = self._expect("DISPATCH").value
                args = [expr]
                while True:
                    if self._peek().kind in {"EOF", "NEWLINE", "}", ")", "DEDENT"}:
                        break
                    if self._peek().kind == ",":
                        break
                    if self._peek().kind == "DISPATCH":
                        break
                    if self._peek().kind == "OP":
                        break
                    if self._peek().kind == "IDENT" and self._peek(1).kind == ":":
                        break
                    arg = self._parse_postfix_atomish()
                    args.append(arg)
                expr = Ast.chain_apply(Ast.Ident(name), args)
                continue
            if self._peek().kind == "NEWLINE" and self._peek(1).kind == "INDENT" and self._peek(2).kind == "DISPATCH":
                self._expect("NEWLINE")
                self._expect("INDENT")
                continue
            if self._peek().kind == "DEDENT":
                break
            if self._peek().kind in {"NUM", "STR", "IDENT", "(", "{"}:
                arg = self._parse_postfix_atomish()
                expr = Ast.Apply(expr, arg)
                continue
            break
        return expr

    def _parse_postfix_atomish(self):
        lam = self._parse_lambda_if_any()
        if lam is not None:
            return lam
        return self._parse_atom()


class _SingleRule:
    def __init__(self, fn):
        self.fn = fn

    def parse(self, text: str):
        return self.fn(text)


def _parse_ident(text: str, kind: str):
    p = _Tokenizer(text).tokenize()
    if len(p) != 2 or p[0].kind != kind or p[1].kind != "EOF":
        raise ValueError("parse error")
    return Ast.Ident(p[0].value)


def _parse_num(text: str):
    return _Parser(text).parse()


def _parse_str(text: str):
    return _Parser(text).parse()


def _parse_expr(text: str):
    return _Parser(text).parse()


val_ident = _SingleRule(lambda text: _parse_ident(text, "IDENT"))
op_ident = _SingleRule(lambda text: _parse_ident(text, "OP"))
numlit = _SingleRule(_parse_num)
strlit = _SingleRule(_parse_str)
lambda_lit = _SingleRule(lambda text: _Parser(text).parse())
expr = _SingleRule(_parse_expr)
