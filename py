#!/usr/bin/env python
from __future__ import (unicode_literals, absolute_import,
                        print_function, division)
from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE,SIG_DFL) 

import argparse
import sys
import json
import re
from collections import Iterable


def import_matches(query, prefix=''):
    matches = set(re.findall(r"(%s[a-zA-Z_][a-zA-Z0-9_]*)\.?" % prefix, query))
    for module_name in matches:
        try:
            module = __import__(module_name)
            globals()[module_name] = module
            import_matches(query, prefix='%s.' % module_name)
        except ImportError as e:
            pass


def lazy_imports(*args):
    query = ' '.join([x for x in args if x])
    import_matches(query)

    if 'Counter' in query: global Counter; from collections import Counter
    if 'OrderedDict' in query: global OrderedDict; from collections import OrderedDict
    if 'defaultdict' in query: global defaultdict; from collections import defaultdict
    if 'groupby' in query: global groupby; from itertools import groupby


def current_list(input):
    return re.split(r'[^a-zA-Z0-9_\.]', input)


def inspect_source(obj):
    import inspect
    import pydoc
    try:
        pydoc.pager(''.join(inspect.getsourcelines(obj)[0]))
        return None
    except:
        return help(obj)

parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter)

parser.add_argument('expression', nargs='?', default='None')
parser.add_argument('-x', dest='lines_of_stdin', action='store_const',
                    const=True, default=False,
                    help='treat each row as x')
parser.add_argument('-fx', dest='filter_result', action='store_const',
                    const=True, default=False,
                    help='keep rows satisfying condition(x)')
parser.add_argument('-l', dest='list_of_stdin', action='store_const',
                    const=True, default=False,
                    help='treat list of stdin as l')
parser.add_argument('-c', dest='pre_cmd', help='run code before expression')
parser.add_argument('-C', dest='post_cmd', help='run code after expression')
parser.add_argument('-V', '--version', action='version', version='py version 0.3.4', help='version info')
parser.add_argument('--i', '--ignore_exceptions',
                    dest='ignore_exceptions', action='store_const',
                    const=True, default=False,
                    help='')
parser.add_argument('--si', '--split_input', dest='split_input',
                    help='pre-process each row with re.split(delimiter, row)')
parser.add_argument('--so', '--split_output', dest='split_output',
                    help='post-process each row with delimiter.join(row)')
parser.add_argument('--ji' '--json_input',
                    dest='json_input', action='store_const',
                    const=True, default=False,
                    help='pre-process each row with json.loads(row)')
parser.add_argument('--jo' '--json_output',
                    dest='json_output', action='store_const',
                    const=True, default=False,
                    help='post-process each row with json.dumps(row)')

args = parser.parse_args()

if args.json_input:
    stdin = (json.loads(x.rstrip()) for x in sys.stdin)
elif args.split_input:
    stdin = (re.split(args.split_input, x.rstrip()) for x in sys.stdin)
else:
    stdin = (x.rstrip() for x in sys.stdin)

if args.expression:
    args.expression = args.expression.replace("`", "'")
    if args.expression.startswith('?') or args.expression.endswith('?'):
        final_atom = current_list(args.expression.rstrip('?'))[-1]
        first_atom = current_list(args.expression.lstrip('?'))[0]
        if args.expression.startswith('??'):
            import inspect
            args.expression = "inspect_source(%s)" % first_atom
        elif args.expression.endswith('??'):
            import inspect
            args.expression = "inspect_source(%s)" % final_atom
        elif args.expression.startswith('?'):
            args.expression = 'help(%s)' % first_atom
        else:
            args.expression = 'help(%s)' % final_atom
        if args.lines_of_stdin:
            from itertools import islice
            stdin = islice(stdin,1)
if args.pre_cmd:
    args.pre_cmd = args.pre_cmd.replace("`", "'")
if args.post_cmd:
    args.post_cmd = args.post_cmd.replace("`", "'")

lazy_imports(args.expression, args.pre_cmd, args.post_cmd)

if args.pre_cmd:
    exec(args.pre_cmd)

def safe_eval(text, x):
    try:
        return eval(text)
    except:
        return None

if args.lines_of_stdin:
    if args.ignore_exceptions:
        result = (safe_eval(args.expression, x) for x in stdin)
    else:
        result = (eval(args.expression) for x in stdin)
elif args.filter_result:
    if args.ignore_exceptions:
        result = (x for x in stdin if safe_eval(args.expression, x))
    else:
        result = (x for x in stdin if eval(args.expression))
elif args.list_of_stdin:
    l = list(stdin)
    result = eval(args.expression)
else:
    result = eval(args.expression)

def format(output):
    if output == None:
        return None
    elif args.json_output:
        return json.dumps(output)
    elif args.split_output:
        return args.split_output.join(output)
    else:
        return output
    

if isinstance(result, Iterable) and hasattr(result, '__iter__') and not isinstance(result, str):
    for x in result:
        formatted = format(x)
        if formatted is not None:
            try:
                print(formatted)
            except UnicodeEncodeError:
                print(formatted.encode('utf-8'))
else:
    formatted = format(result)
    if formatted is not None:
        try:
            print(formatted)
        except UnicodeEncodeError:
            print(formatted.encode('utf-8'))

if args.post_cmd:
    exec(args.post_cmd)
