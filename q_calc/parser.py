import logging
import re
from prompt_toolkit import prompt, history, completion
import sys

import numpy as np
import quaternion as qn

logger = logging.getLogger(__name__)

tokens = (
    'NAME','NUMBER',
    'PLUS','MINUS','TIMES','DIVIDE','EQUALS',
    'LPAREN','RPAREN','COMMA'
    )

# Tokens

t_PLUS    = r'\+'
t_MINUS   = r'-'
t_TIMES   = r'\*'
t_DIVIDE  = r'/'
t_EQUALS  = r'='
t_COMMA   = r','
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_NAME    = r'[a-zA-Z_][a-zA-Z0-9_]*'

numbers_pattern = re.compile("([\d\.]+)([ijk]?)")
bases = [qn.quaternion(0,1,0,0),qn.quaternion(0,0,1,0), qn.quaternion(0,0,0,1)]

def t_NUMBER(t):
    r'([\d\.]+)([ijk]?)' # we use these docstrings to define the matching pattern for each token type
    try:
        p = numbers_pattern.split(t.value)
        a1 = float(p[1])
        if p[2] == 'i'  :a1 = a1 * bases[0]
        elif p[2] == 'j':a1 = a1 * bases[1]
        elif p[2] == 'k':a1 = a1 * bases[2]
        else:            a1 = a1 * qn.one
        t.value = a1
    except ValueError:
        raise SyntaxError("Invalid numerical value: {}".format(t.value))
    return t

# Ignored characters
t_ignore = " \t"

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    raise SyntaxError("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

# Build the lexer
import ply.lex as lex

lexer = lex.lex()

# Parsing rules

precedence = (
    ('left', 'COMMA'),
    ('left','PLUS','MINUS'),
    ('left','TIMES','DIVIDE'),
    ('right','UMINUS'),
    ('right', 'NAME')
    )

# dictionary of names
names = { "PI":np.pi, "e":np.e , "i": bases[0], "j": bases[1], "k":bases[2]}
# the default ones should not be writable
consts = set(names.keys())

def p_statement_assign(t):
    'statement : NAME EQUALS expression' # and these to define
    if t[1] not in consts:
        names[t[1]] = t[3]

def p_statement_expr(t):
    'statement : expression'
    print(t[1])

def list_safe(t):
    if type(t) == list:
        if len(t) > 0:
            return t[-1]
        else:
            return np.nan
    else:
        return t

def inner(q1, q2):
    comp1 = qn.as_float_array(q1)
    comp2 = qn.as_float_array(q2)
    return sum((x*y for x,y in zip(comp1, comp2)))

def outer(q1, q2):
    return (q1*q2 - q2*q1)/2


functions = {
    'cos': np.cos,
    'arccos': np.arccos,
    'sin': np.sin,
    'arcsin': np.arcsin,
    'sqrt': np.sqrt,
    'tan':np.tan,
    'arctan':np.arctan,
    'norm': np.abs,
    'exp': np.exp,
    'conj':np.conjugate,
    'pow': np.power,
    'dot': inner,
    'cross': outer
}


def quaternion_downconvert(q):
    comp = qn.as_float_array(q)
    if comp[2] != 0 or comp[3] != 0: return q
    elif comp[1] != 0: return np.complex(comp[0], comp[1])
    else: return comp[0]

def p_experssion_func(t):
    r'expression : NAME LPAREN expression RPAREN'
    if t[1] in functions:
        func_to_call = functions[t[1]]
        if t[3] is None:
            t[0] = func_to_call()
        else:
            if type(t[3]) == list: pargs = [quaternion_downconvert(q) for q in t[3]]
            else: pargs = quaternion_downconvert(t[3])
            try:
                t[0] = func_to_call(pargs)
            except TypeError as ex:
                if type(t[3]) == list: t[0] = func_to_call(*pargs)
                else: raise ex
    else:
        raise RuntimeError("unknown function: %s"% t[1])

def p_expression_binop(t):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression COMMA expression
                  | expression DIVIDE expression'''
    if   t[2] == '+': t[0] = list_safe(t[1]) + list_safe(t[3])
    elif t[2] == '-': t[0] = list_safe(t[1]) - list_safe(t[3])
    elif t[2] == '*': t[0] = list_safe(t[1]) * list_safe(t[3])
    elif t[2] == '/': t[0] = list_safe(t[1]) / list_safe(t[3])
    elif t[2] == ',':
        if type(t[1]) == list:
            t[0] = [*t[1], t[3]]
        else:
            t[0] = [t[1], t[3]]


def p_expression_uminus(t):
    'expression : MINUS expression %prec UMINUS'
    t[0] = -list_safe(t[2])

def p_expression_group(t):
    'expression : LPAREN expression RPAREN'
    t[0] = t[2]

def p_expression_empty_set(t):
    'expression : LPAREN RPAREN'
    t[0] = None

def p_expression_number(t):
    'expression : NUMBER'
    t[0] = t[1]

def p_expression_name(t):
    'expression : NAME'
    try:
        t[0] = names[t[1]]
    except LookupError:
        raise RuntimeError("Undefined name '%s'" % t[1])
        t[0] = 0

def p_error(t):
    raise SyntaxError("Syntax error at '%s'" % t.value)

import ply.yacc as yacc

# write_tables=False makes PLY stop generating the parser python file
parser = yacc.yacc(debug=False, write_tables=False)

def main():
    cmd_history=history.InMemoryHistory()
    func_completer = completion.WordCompleter(functions.keys())
    while True:
        try:
            s = prompt('Q>', history=cmd_history, completer=func_completer)
            parser.parse(s)
        except EOFError:
            break
        except RuntimeError as ex:
            print(ex, file=sys.stderr)
            continue
        except SyntaxError as ex:
            print(ex, file=sys.stderr)
            continue
        except TypeError as ex:
            print(ex, file=sys.stderr)
            continue

if __name__ == '__main__':
    main()
