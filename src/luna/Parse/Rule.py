from __future__ import annotations

import ast as py_ast
from dataclasses import dataclass
from typing import Sequence

from parsy import eof, forward_declaration, generate, regex, seq, string

import luna.Parse.Ast as Ast


def _table_field_key(name: str) -> Ast.StrLit:
    # table_field_key := ident_text -> string-literal key
    return Ast.StrLit(name)


def _table_numeric_key(num: str) -> Ast.NumLit:
    # table_numeric_key := num_text -> number-literal key
    return Ast.NumLit(num)


def _nested_table_from_path(path: Sequence[Ast.Ast], value: Ast.Ast) -> Ast.Table:
    # nested_table := key_path ':' value -> {k1: {k2: ... value}}
    if not path:
        raise ValueError("table path cannot be empty")
    expr = value
    for key in reversed(path[1:]):
        expr = Ast.Table({key: expr})
    return Ast.Table({path[0]: expr})


def _merge_table_ast(lhs: Ast.Table, rhs: Ast.Table) -> Ast.Table:
    # table_merge := table table -> merged table, recursively merging child tables.
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


def _strip_comments_and_split_lines(src: str) -> list[str]:
    # source_lines := (normal | quoted_string | block_string | comment)* -> line*
    # comment := '--' not-newline* | '--' ws? '[[' any* ']]'
    lines: list[str] = []
    buf: list[str] = []
    i = 0
    state = "normal"
    escaped = False

    while i < len(src):
        ch = src[i]

        if state == "normal":
            if src.startswith("--", i):
                j = i + 2
                while j < len(src) and src[j] == " ":
                    j += 1
                if src.startswith("[[", j):
                    i = j + 2
                    state = "block_comment"
                    continue
                while i < len(src) and src[i] != "\n":
                    i += 1
                continue
            if src.startswith("[[", i):
                buf.append("[[")
                i += 2
                state = "block_string"
                continue
            if ch == '"':
                buf.append(ch)
                i += 1
                state = "quoted"
                escaped = False
                continue
            if ch == "\n":
                lines.append("".join(buf))
                buf = []
                i += 1
                continue
            if ch == "\r":
                i += 1
                continue
            buf.append(ch)
            i += 1
            continue

        if state == "quoted":
            buf.append(ch)
            i += 1
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                state = "normal"
            continue

        if state == "block_string":
            if src.startswith("]]", i):
                buf.append("]]")
                i += 2
                state = "normal"
                continue
            if ch == "\r":
                i += 1
                continue
            buf.append(ch)
            i += 1
            continue

        if state == "block_comment":
            if src.startswith("]]", i):
                i += 2
                state = "normal"
                continue
            if ch == "\n":
                lines.append("".join(buf))
                buf = []
                i += 1
                continue
            i += 1
            continue

    lines.append("".join(buf))
    return lines


def _indent_width(line: str) -> int:
    # indent_width := (' ' -> 1 | '\t' -> 4)* before first non-space char
    width = 0
    for ch in line:
        if ch == " ":
            width += 1
        elif ch == "\t":
            width += 4
        else:
            break
    return width


def _is_blank(line: str) -> bool:
    # blank_line := ws eof
    return not line.strip()


def _is_continuation_line(text: str) -> bool:
    # continuation_line := ws ('.' | '\\') rest
    stripped = text.lstrip()
    return bool(stripped) and stripped[0] in ".\\"


def _delimiter_delta(text: str) -> int:
    # delimiter_delta := count(open_delim) - count(close_delim), ignoring strings.
    delta = 0
    i = 0
    state = "normal"
    escaped = False

    while i < len(text):
        ch = text[i]
        if state == "normal":
            if text.startswith("[[", i):
                i += 2
                state = "block_string"
                continue
            if ch == '"':
                i += 1
                state = "quoted"
                escaped = False
                continue
            if ch in "({[":
                delta += 1
            elif ch in ")}]":
                delta -= 1
            i += 1
            continue
        if state == "quoted":
            i += 1
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                state = "normal"
            continue
        if state == "block_string":
            if text.startswith("]]", i):
                i += 2
                state = "normal"
                continue
            i += 1
            continue

    return delta


class _SingleRule:
    def __init__(self, fn):
        self.fn = fn

    def parse(self, text: str):
        return self.fn(text)


@dataclass(frozen=True)
class _PendingLambda:
    params: tuple[Ast.Pattern, ...]


@dataclass(frozen=True)
class _PendingApplyLambda:
    applyer: Ast.Ast
    params: tuple[Ast.Pattern, ...]


@dataclass(frozen=True)
class _LineLet:
    pattern: Ast.Pattern
    value: Ast.Ast | _PendingLambda | _PendingApplyLambda | None


@dataclass(frozen=True)
class _LineTableItem:
    path: Sequence[Ast.Ast]
    value: Ast.Ast | _PendingLambda | _PendingApplyLambda | None


# ws := (" " | "\t")*
_WS = regex(r"[ \t]*")
# ws1 := (" " | "\t")+
_WS1 = regex(r"[ \t]+")
# ident_text := [A-Za-z_][A-Za-z0-9_]*
_IDENT_TEXT = regex(r"[A-Za-z_][A-Za-z0-9_]*")
# op_text := one-or-more symbolic operator chars.
_OP_TEXT = regex(r"[!@#$%^&*+\-?/|~<>=]+")
# num_text := "-"? digit+ ("." digit+)?
_NUM_TEXT = regex(r"-?\d+(?:\.\d+)?")
# field_segment := ident_text | digit+
_FIELD_SEGMENT = regex(r"[A-Za-z_][A-Za-z0-9_]*|\d+")
# dispatch_path := ident_text ("." ident_text)*
_DISPATCH_PATH = _IDENT_TEXT.sep_by(string("."), min=1).map(".".join)
# comma := ws >> "," >> ws
_COMMA = _WS >> string(",") << _WS


def _parse_quoted(text: str) -> Ast.StrLit:
    # quoted_value := Python-literal-decoded quoted_string
    return Ast.StrLit(py_ast.literal_eval(text))


def _parse_block_string(text: str) -> Ast.StrLit:
    # block_string_value := '[[' body ']]' -> body
    return Ast.StrLit(text[2:-2])


# expr := lambda | operator_expr
expr_parser = forward_declaration()
# pattern := table_pattern | ident_pattern
pattern_parser = forward_declaration()
# table_key_path := table_key_atom (("." field_segment) | ("[" expr "]"))*
table_key_path_parser = forward_declaration()
# atom := value_atom | op_ident
atom_parser = forward_declaration()
# value_atom := table_literal | paren_expr | block_string | string | num | ident
value_atom_parser = forward_declaration()
# lambda := pattern >> ws >> "->" >> ws >> expr
lambda_parser = forward_declaration()
# atomic_expr := (lambda | atom) tight_suffix*
atomic_expr_parser = forward_declaration()
# apply_arg := (lambda | value_atom) tight_suffix*
apply_arg_parser = forward_declaration()
# postfix_expr := atomic_expr (free_dispatch | self_dispatch | apply_suffix)*
postfix_expr_parser = forward_declaration()
# lambda_head := pattern ("->" pattern)* "->" eof
lambda_head_parser = forward_declaration()


# quoted_string := '"' escaped-or-normal-char* '"'
_quoted_string = regex(r'"(?:\\.|[^"\\])*"').map(_parse_quoted)
# block_string := "[[" any* "]]"
_block_string = regex(r"(?s)\[\[.*?\]\]").map(_parse_block_string)
# numlit := num_text
_numlit = _NUM_TEXT.map(Ast.NumLit)
# val_ident := ident_text
_val_ident = _IDENT_TEXT.map(Ast.Ident)
# op_ident := op_text
_op_ident = _OP_TEXT.map(Ast.Ident)


# table_pattern := "{" >> ws >> (":" ident | ident (":" ident)?)
#                  (comma (":" ident | ident (":" ident)?))* >> ws >> "}"
@generate
def _table_pattern():
    yield string("{")
    yield _WS
    positional: list[Ast.Pattern] = []
    named: list[tuple[str, str]] = []

    if (yield string("}").result(True).optional()) is True:
        return Ast.TablePattern((), ())

    while True:
        named_self = yield (string(":") >> _WS >> _IDENT_TEXT).optional()
        if named_self is not None:
            named.append((named_self, named_self))
        else:
            first = yield _IDENT_TEXT
            target = yield (_WS >> string(":") >> _WS >> _IDENT_TEXT).optional()
            if target is None:
                positional.append(Ast.IdentPattern(first))
            else:
                named.append((first, target))
        yield _WS
        if (yield string("}").result(True).optional()) is True:
            break
        yield _COMMA

    return Ast.TablePattern(tuple(positional), tuple(named))


# pattern := table_pattern | ident_text
pattern_parser.become(_table_pattern | _IDENT_TEXT.map(Ast.IdentPattern))


# table_key_atom := "[" >> ws >> expr >> ws >> "]" | ident_text | num_text
_table_key_atom = (
    (string("[") >> _WS >> expr_parser << _WS << string("]"))
    | _IDENT_TEXT.map(_table_field_key)
    | _NUM_TEXT.map(_table_numeric_key)
)


# table_key_path := table_key_atom (("." field_segment) | ("[" ws expr ws "]"))*
@generate
def _table_key_path():
    first = yield _table_key_atom
    path = [first]
    while True:
        seg = yield (
            (string(".") >> _FIELD_SEGMENT).map(lambda item: ("dot", item))
            | (string("[") >> _WS >> expr_parser << _WS << string("]")).map(
                lambda item: ("index", item)
            )
        ).optional()
        if seg is None:
            break
        if seg[0] == "dot":
            value = seg[1]
            path.append(
                _table_numeric_key(value) if value.isdigit() else _table_field_key(value)
            )
        else:
            path.append(seg[1])
    return path


# table_key_path := table_key_atom (("." field_segment) | ("[" ws expr ws "]"))*
table_key_path_parser.become(_table_key_path)


def _build_inline_table(items: list[tuple[str, object]]) -> Ast.Table:
    table = Ast.Table({})
    positional_index = 1
    saw_positional = False

    for kind, payload in items:
        if kind == "kv":
            path, value = payload
            if (
                len(path) == 1
                and isinstance(path[0], Ast.NumLit)
                and path[0].lit.isdigit()
                and saw_positional
            ):
                raise ValueError(
                    "implicit list entries conflict with explicit numeric table keys"
                )
            table = _merge_table_ast(table, _nested_table_from_path(path, value))
            continue

        saw_positional = True
        table = _merge_table_ast(
            table,
            Ast.Table({_table_numeric_key(str(positional_index)): payload}),
        )
        positional_index += 1

    return table


# table_literal_item := (table_key_path >> ws >> ":" >> ws >> expr) | expr
@generate
def _table_literal_item():
    keyed = yield (
        (table_key_path_parser << _WS << string(":") << _WS).bind(
            lambda path: expr_parser.map(lambda value: ("kv", (path, value)))
        )
    ).optional()
    if keyed is not None:
        return keyed
    return ("pos", (yield expr_parser))


# table_literal := "{" >> ws >> (table_literal_item (comma table_literal_item)*)? >> ws >> "}"
@generate
def _table_literal():
    yield string("{")
    yield _WS
    if (yield string("}").result(True).optional()) is True:
        return Ast.Table({})
    items = yield _table_literal_item.sep_by(_COMMA, min=1)
    yield _WS
    yield string("}")
    return _build_inline_table(items)


# paren_expr := "(" >> ws >> expr >> ws >> ")"
@generate
def _paren_expr():
    yield string("(")
    yield _WS
    inner = yield expr_parser
    yield _WS
    yield string(")")
    return inner


# value_atom := table_literal | paren_expr | block_string | quoted_string | numlit | val_ident
value_atom_parser.become(
    _table_literal
    | _paren_expr
    | _block_string
    | _quoted_string
    | _numlit
    | _val_ident
)

# atom := value_atom | op_ident
atom_parser.become(
    value_atom_parser
    | _op_ident
)


# lambda := pattern >> ws >> "->" >> ws >> expr
@generate
def _lambda_expr():
    param = yield pattern_parser
    yield _WS
    yield string("->")
    yield _WS
    body = yield expr_parser
    return Ast.Lambda(param=param, body=body)


# lambda := pattern >> ws >> "->" >> ws >> expr
lambda_parser.become(_lambda_expr)


# lambda_head := pattern >> ws >> "->" (ws pattern ws "->")* >> ws >> eof
@generate
def _lambda_head_expr():
    first = yield pattern_parser
    params = [first]
    yield _WS
    yield string("->")
    while True:
        param = yield (_WS >> pattern_parser << _WS << string("->")).optional()
        if param is None:
            break
        params.append(param)
    yield _WS
    yield eof
    return _PendingLambda(tuple(params))


# lambda_head := pattern >> ws >> "->" (ws pattern ws "->")* >> ws >> eof
lambda_head_parser.become(_lambda_head_expr)


# tight_suffix := ("." field_segment) | ("[" >> ws >> expr >> ws >> "]")
@generate
def _tight_suffix():
    return (
        yield (
            (string(".") >> _FIELD_SEGMENT).map(lambda item: ("dot", item))
            | (string("[") >> _WS >> expr_parser << _WS << string("]")).map(
                lambda item: ("index", item)
            )
        )
    )


# atomic_expr := (lambda | atom) tight_suffix*
@generate
def _atomic_expr():
    current = yield (lambda_parser | atom_parser)
    for kind, payload in (yield _tight_suffix.many()):
        if kind == "dot":
            current = (
                Ast.IndexAccess(current, Ast.NumLit(payload))
                if payload.isdigit()
                else Ast.FieldAccess(current, payload)
            )
        else:
            current = Ast.IndexAccess(current, payload)
    return current


# atomic_expr := (lambda | atom) tight_suffix*
atomic_expr_parser.become(_atomic_expr)


# apply_arg := (lambda | value_atom) tight_suffix*
@generate
def _apply_arg():
    current = yield (lambda_parser | value_atom_parser)
    for kind, payload in (yield _tight_suffix.many()):
        if kind == "dot":
            current = (
                Ast.IndexAccess(current, Ast.NumLit(payload))
                if payload.isdigit()
                else Ast.FieldAccess(current, payload)
            )
        else:
            current = Ast.IndexAccess(current, payload)
    return current


# apply_arg := (lambda | value_atom) tight_suffix*
apply_arg_parser.become(_apply_arg)


# free_dispatch := ws1 >> "." >> dispatch_path
@generate
def _free_dispatch_suffix():
    yield _WS1
    yield string(".")
    path = yield _DISPATCH_PATH
    return lambda cur: Ast.Apply(Ast.Ident("." + path), cur)


# self_dispatch := ws1 >> "\\" >> dispatch_path
@generate
def _self_dispatch_suffix():
    yield _WS1
    yield string("\\")
    path = yield _DISPATCH_PATH
    return lambda cur: Ast.Apply(Ast.Ident("\\" + path), cur)


# apply_suffix := ws1 >> apply_arg
@generate
def _apply_suffix():
    yield _WS1
    arg = yield apply_arg_parser
    return lambda cur: Ast.Apply(cur, arg)


# postfix_expr := atomic_expr (free_dispatch | self_dispatch | apply_suffix)*
@generate
def _postfix_expr():
    current = yield atomic_expr_parser
    for suffix in (yield (_free_dispatch_suffix | _self_dispatch_suffix | _apply_suffix).many()):
        current = suffix(current)
    return current


# postfix_expr := atomic_expr (free_dispatch | self_dispatch | apply_suffix)*
postfix_expr_parser.become(_postfix_expr)


# operator_expr := postfix_expr (ws1 op_text ws1 postfix_expr)*
@generate
def _operator_expr():
    current = yield postfix_expr_parser
    rest = yield seq(op=_WS1 >> _OP_TEXT << _WS1, rhs=postfix_expr_parser).many()
    for part in rest:
        current = Ast.chain_apply(Ast.Ident(part["op"]), [current, part["rhs"]])
    return current


# expr := lambda | operator_expr
expr_parser.become(lambda_parser | _operator_expr)


# expr_line := ws >> expr >> ws >> eof
_expr_line = _WS >> expr_parser << _WS << eof


# let_line := pattern >> ws >> assignment_equal >> raw-rest >> eof
# assignment_equal := "=" !op_char
@generate
def _let_line():
    pat = yield pattern_parser
    yield _WS
    yield regex(r"=(?![!@#$%^&*+\-?/|~<>=])")
    rest = yield regex(r".*")
    yield eof
    return ("let", pat, rest)


# table_item_line := table_key_path >> ws >> ":" >> raw-rest >> eof
@generate
def _table_item_line():
    path = yield table_key_path_parser
    yield _WS
    yield string(":")
    rest = yield regex(r".*")
    yield eof
    return ("table", path, rest)


# finish_pending_lambda := pending_params + indented_block_expr -> nested Lambda
def _finish_pending_lambda(pending: _PendingLambda, body: Ast.Ast) -> Ast.Ast:
    result = body
    for param in reversed(pending.params):
        result = Ast.Lambda(param=param, body=result)
    return result


# finish_pending_expr := pending_lambda | (applyer pending_lambda)
def _finish_pending_expr(
    pending: _PendingLambda | _PendingApplyLambda, body: Ast.Ast
) -> Ast.Ast:
    lambda_expr = _finish_pending_lambda(_PendingLambda(pending.params), body)
    if isinstance(pending, _PendingApplyLambda):
        return Ast.Apply(pending.applyer, lambda_expr)
    return lambda_expr


# pending_expr := lambda_head | (expr_line >> ws1 >> lambda_head)
def _parse_pending_expr(text: str) -> _PendingLambda | _PendingApplyLambda:
    for i, ch in enumerate(text):
        if i != 0 and not text[i - 1].isspace():
            continue
        suffix = text[i:].strip()
        if not suffix:
            continue
        try:
            pending = lambda_head_parser.parse(suffix)
        except Exception:
            continue
        prefix = text[:i].strip()
        if not prefix:
            return pending
        try:
            return _PendingApplyLambda(_expr_line.parse(prefix), pending.params)
        except Exception:
            continue
    raise ValueError("lambda expression is missing a body")


# value_expr := expr_line | pending_expr | empty
def _parse_value_expr(text: str) -> Ast.Ast | _PendingLambda | _PendingApplyLambda | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return _expr_line.parse(stripped)
    except Exception as expr_error:
        try:
            return _parse_pending_expr(stripped)
        except Exception as lambda_error:
            raise expr_error from lambda_error


# line_expr := let_line | table_item_line | value_expr
def _parse_line_expr(text: str):
    stripped = text.strip()
    if not stripped:
        raise ValueError("empty expression line")
    try:
        kind, pat, rest = _let_line.parse(stripped)
        return _LineLet(pat, _parse_value_expr(rest))
    except Exception:
        pass
    try:
        kind, path, rest = _table_item_line.parse(stripped)
        return _LineTableItem(path, _parse_value_expr(rest))
    except Exception:
        pass
    value = _parse_value_expr(stripped)
    if value is None:
        raise ValueError("empty expression line")
    return value


# blank* := empty-or-whitespace-only line*
def _skip_blank(lines: list[str], index: int) -> int:
    while index < len(lines) and _is_blank(lines[index]):
        index += 1
    return index


# logical_line := physical_line (continued_line | delimiter-balanced-line)*
def _collect_logical_line(lines: list[str], index: int, indent: int) -> tuple[str, int]:
    current = lines[index].strip()
    delimiter_balance = _delimiter_delta(current)
    index += 1
    while True:
        probe = _skip_blank(lines, index)
        if probe >= len(lines):
            return current, probe
        next_line = lines[probe]
        if (
            delimiter_balance <= 0
            and (
                _indent_width(next_line) <= indent
                or not _is_continuation_line(next_line)
            )
        ):
            return current, index
        fragment = next_line.strip()
        current += " " + fragment
        delimiter_balance += _delimiter_delta(fragment)
        index = probe + 1


# block_expr := (let_expr | table_item | expr)* folded into one expression
def _collapse_block(items: list[object]) -> Ast.Ast:
    if not items:
        return Ast.Table({})

    lets = [item for item in items if isinstance(item, _LineLet)]
    exprs = [
        Ast.Table(item.path)
        if isinstance(item, _LineTableItem)
        else item
        for item in items
        if not isinstance(item, _LineLet)
    ]

    if len(exprs) > 1 and all(isinstance(item, Ast.Table) for item in exprs):
        merged = Ast.Table({})
        for item in exprs:
            merged = _merge_table_ast(merged, item)
        result = merged
    else:
        result = exprs[-1] if exprs else Ast.Table({})

    for item in reversed(lets):
        if item.value is None or isinstance(item.value, _PendingLambda):
            raise ValueError("let expression is missing a value")
        result = Ast.LetIn(ident=item.pattern, expr=item.value, body=result)

    return result


# block := line_expr (indented block as lambda/table/apply body)* until dedent
def _parse_block(lines: list[str], index: int, indent: int) -> tuple[Ast.Ast, int]:
    items: list[object] = []
    index = _skip_blank(lines, index)

    while index < len(lines):
        if _is_blank(lines[index]):
            index += 1
            continue

        current_indent = _indent_width(lines[index])
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError(f"unexpected indentation at line: {lines[index]!r}")

        logical_line, index = _collect_logical_line(lines, index, indent)
        item = _parse_line_expr(logical_line)

        if (
            isinstance(item, _LineLet | _LineTableItem)
            and (
                item.value is None
                or isinstance(item.value, _PendingLambda | _PendingApplyLambda)
            )
        ) or isinstance(item, _PendingLambda | _PendingApplyLambda):
            nested_index = _skip_blank(lines, index)
            if nested_index >= len(lines):
                raise ValueError("expected indented block")
            child_indent = _indent_width(lines[nested_index])
            if child_indent <= indent:
                raise ValueError("expected indented block")
            value, index = _parse_block(lines, nested_index, child_indent)
            if isinstance(item, _LineLet):
                value = (
                    _finish_pending_expr(item.value, value)
                    if isinstance(item.value, _PendingLambda | _PendingApplyLambda)
                    else value
                )
                items.append(_LineLet(item.pattern, value))
            elif isinstance(item, _LineTableItem):
                value = (
                    _finish_pending_expr(item.value, value)
                    if isinstance(item.value, _PendingLambda | _PendingApplyLambda)
                    else value
                )
                items.append(
                    _LineTableItem(_nested_table_from_path(item.path, value).tbl, None)
                )
            else:
                items.append(_finish_pending_expr(item, value))
            continue

        if isinstance(item, _LineTableItem):
            if item.value is None or isinstance(item.value, _PendingLambda | _PendingApplyLambda):
                raise ValueError("table item expression is missing a value")
            items.append(_LineTableItem(_nested_table_from_path(item.path, item.value).tbl, None))
            continue
        if isinstance(item, _LineLet):
            if item.value is None or isinstance(item.value, _PendingLambda | _PendingApplyLambda):
                raise ValueError("let expression is missing a value")
            items.append(item)
            continue
        if isinstance(item, _PendingLambda | _PendingApplyLambda):
            raise ValueError("lambda expression is missing a body")

        nested_index = _skip_blank(lines, index)
        if nested_index < len(lines) and _indent_width(lines[nested_index]) > indent:
            value, index = _parse_block(
                lines,
                nested_index,
                _indent_width(lines[nested_index]),
            )
            item = Ast.Apply(item, value)

        items.append(item)

    return _collapse_block(items), index


# module_expr := comment-stripped block eof
def _parse_expr(text: str):
    lines = _strip_comments_and_split_lines(text)
    ast, index = _parse_block(lines, 0, 0)
    index = _skip_blank(lines, index)
    if index != len(lines):
        raise ValueError("unexpected trailing input")
    return ast


# single_ident := ws >> (val_ident | op_ident) >> ws >> eof
def _parse_ident(text: str, parser):
    return (_WS >> parser << _WS << eof).parse(text)


# public val_ident := ws >> ident_text >> ws >> eof
val_ident = _SingleRule(lambda text: _parse_ident(text, _val_ident))
# public op_ident := ws >> op_text >> ws >> eof
op_ident = _SingleRule(lambda text: _parse_ident(text, _op_ident))
# public numlit := ws >> num_text >> ws >> eof
numlit = _SingleRule(lambda text: (_WS >> _numlit << _WS << eof).parse(text))
# public strlit := ws >> (quoted_string | block_string) >> ws >> eof
strlit = _SingleRule(
    lambda text: (_WS >> (_quoted_string | _block_string) << _WS << eof).parse(text)
)
# public lambda_lit := ws >> lambda >> ws >> eof
lambda_lit = _SingleRule(lambda text: (_WS >> lambda_parser << _WS << eof).parse(text))
# public expr := module_expr
expr = _SingleRule(_parse_expr)
