from __future__ import annotations
from parsy import regex, string, generate, forward_declaration, Parser
import Parse.Ast as Ast

expr = forward_declaration()

sp = regex(r'\s*')

def embraced(rule: Parser, l: str, r: str) -> Parser:
    @generate
    def parser():
        yield string(l)
        yield sp
        res = yield rule
        yield sp
        yield string(r)
        return res 
        
    return parser

def parenthesised(rule: Parser) -> Parser:
    return embraced(rule, '(', ')')
def bracketed(rule: Parser) -> Parser:
    return embraced(rule, '[', ']')
def braced(rule: Parser) -> Parser:
    return embraced(rule, '{', '}')
    
@generate
def val_ident():
    ident = yield regex(r'[a-z_A-Z][a-zA-Z_0-9]*')
    return Ast.Ident(ident)

@generate
def op_ident():
    ident = yield regex(r'[!@#$%^&*+-?/|~<>][!@#$%^&*+-?/|~<>=]*')
    return Ast.Ident(ident)
    
@generate
def _lambda_tbl_dstr_param_inner():
    pass

lambda_param = val_ident | braced(_lambda_tbl_dstr_param_inner)

@generate
def lambda_lit():
    """
    lambda := lambda_param >> sp >>  "->" >> sp >> expr
    """
    param = yield lambda_param
    yield sp
    yield string("->")
    yield sp
    body = yield expr
    return Ast.Lambda(
        param = param,
        body = body,
    )
