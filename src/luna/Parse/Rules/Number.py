import luna.Parse.Ast as Ast
from parsy import regex, generate


numlit = regex(r"-?\d+(?:\.\d+)?").map(Ast.NumLit)
