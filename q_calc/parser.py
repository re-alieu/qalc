import logging
import re

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
        if p[2] == 'i':
            a1 = a1 * bases[0]
        elif p[2] == 'j':
            a1 = a1 * bases[1]
        elif p[2] == 'k':
            a1 = a1 * bases[2]
        t.value = a1
    except ValueError:
        print("Invalid numerical value", t.value)
        t.value = 0
    return t

# Ignored characters
t_ignore = " \t"

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")
    
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
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
    ('left', 'NAME')
    )

# dictionary of names
names = { "PI":np.pi, "e":np.e }

def p_statement_assign(t):
    'statement : NAME EQUALS expression' # and these to define
    names[t[1]] = t[3]

def p_statement_expr(t):
    'statement : expression'
    print(t[1])

def tuple_reduce(t):
    if type(t) == tuple:
        if len(t) > 0:
            return t[-1]
        else:
            return np.nan
    else:
        return t

functions = {
    'cos': np.cos,
    'sin': np.sin,
    'sqrt': np.sqrt,
    'tan':np.tan,
    'arctan':np.arctan,
    'norm': np.abs,
}

def p_experssion_func(t):
    r'expression : NAME expression'
    if t[1] in functions:
        func_to_call = functions[t[1]]
        if type(t[2]) == tuple:
            t[0] = func_to_call(*t[2])
        elif t[2] is None:
            t[0] = func_to_call()
        else:
            t[0] = func_to_call(t[2])
    else:
        print("unknown function:", t[1])
        return np.nan

def p_expression_binop(t):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression COMMA expression
                  | expression DIVIDE expression'''
    if t[2] == '+'  : t[0] = tuple_reduce(t[1]) + tuple_reduce(t[3])
    elif t[2] == '-': t[0] = tuple_reduce(t[1]) - tuple_reduce(t[3])
    elif t[2] == '*': t[0] = tuple_reduce(t[1]) * tuple_reduce(t[3])
    elif t[2] == '/': t[0] = tuple_reduce(t[1]) / tuple_reduce(t[3])
    elif t[2] == t_COMMA:
        if type(t[1]) == tuple:
            t[0] = (*t[1], t[3])
        else:
            t[0] = (t[1], t[3])


def p_expression_uminus(t):
    'expression : MINUS expression %prec UMINUS'
    t[0] = -tuple_reduce(t[2])

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
        print("Undefined name '%s'" % t[1])
        t[0] = 0

def p_error(t):
    print("Syntax error at '%s'" % t.value)

import ply.yacc as yacc

# write_tables=False makes PLY stop generating the parser python file
parser = yacc.yacc(debug=False, write_tables=False)

while True:
    try:
        s = input('calc > ')   # Use raw_input on Python 2
    except EOFError:
        break
    parser.parse(s)