from __future__ import absolute_import

#if __name__ == '__main__' and __package__ is None:
#    from os import sys, path
#    sys.path.append(path.dirname(path.abspath('.')))

import unittest
import ast
import __main__
from ...cmd_run import run
from ... import persistence


persistence.put = lambda x: None
persistence.store_trial = lambda a, b, c, d, e: None


NAME = '<unknown>'

class Args(object):

    def __init__(self):
        self.verbose = False
        self.bypass_modules = True
        self.depth_context = 'non-user'
        self.depth = 1
        self.execution_provenance = 'Tracer'
        self.disasm = False

class TestCallSlicing(unittest.TestCase):

        def setUp(self):
            import __main__
            __main__.__dict__.clear()
            __main__.__dict__.update({'__name__'    : '__main__',
                                      '__file__'    : 'tests/.tests/local.py',
                                      '__builtins__': __builtins__,
                                     })
            metascript = {
                'code': None,
                'path': 'tests/.tests/local.py',
                'compiled': None,
            }

            self.run_args = ('tests/.tests', Args(), metascript, __main__)

        def extract(self, provider):
            result = set()
            for dep in provider.dependencies:
                dependent = provider.variables[dep.dependent]
                supplier = provider.variables[dep.supplier]
                result.add(((dependent.name, dependent.line), (supplier.name, supplier.line)))
            return result

        def test_simple(self):
            self.run_args[2]['code'] = ("def fn(a, b):\n"
                                        "    return a + b\n"
                                        "x = y = 1\n"
                                        "r = fn(x, y)")
            provider = run(*self.run_args)
            result = {
                (("a", 1), ("x", 3)),
                (("b", 1), ("y", 3)),
                (("return", 2), ("a", 1)),
                (("return", 2), ("b", 1)),
                (("call fn", 4), ("return", 2)),
                (("r", 4), ("call fn", 4)),
            }
            self.assertEqual(result, self.extract(provider))

        def test_call_keyword(self):
            self.run_args[2]['code'] = ("def fn(a, b, c=3):\n"
                                        "    return a + b + c\n"
                                        "x = y = 1\n"
                                        "r = fn(x, y, c=y)")
            provider = run(*self.run_args)
            result = {
                (("a", 1), ("x", 3)),
                (("b", 1), ("y", 3)),
                (("c", 1), ("y", 3)),
                (("return", 2), ("a", 1)),
                (("return", 2), ("b", 1)),
                (("return", 2), ("c", 1)),
                (("call fn", 4), ("return", 2)),
                (("r", 4), ("call fn", 4)),
            }
            self.assertEqual(result, self.extract(provider))

        def test_call_keyword_kw(self):
            self.run_args[2]['code'] = ("def fn(a, b, c=3):\n"
                                        "    return a + b + c\n"
                                        "x = y = 1\n"
                                        "z = {'b': 2}\n"
                                        "r = fn(x, c=y, **z)")
            provider = run(*self.run_args)
            result = {
                (("a", 1), ("x", 3)),
                (("b", 1), ("z", 4)),
                (("c", 1), ("y", 3)),
                (("return", 2), ("a", 1)),
                (("return", 2), ("b", 1)),
                (("return", 2), ("c", 1)),
                (("call fn", 5), ("return", 2)),
                (("r", 5), ("call fn", 5)),
            }
            self.assertEqual(result, self.extract(provider))

        def test_call_args(self):
            self.run_args[2]['code'] = ("def fn(a, b, c=3):\n"
                                        "    return a + b + c\n"
                                        "x = 1\n"
                                        "y = [2]\n"
                                        "r = fn(x, *y)")
            provider = run(*self.run_args)
            result = {
                (("a", 1), ("x", 3)),
                (("b", 1), ("y", 4)),
                (("c", 1), ("y", 4)), #ToDo: fix?
                (("return", 2), ("a", 1)),
                (("return", 2), ("b", 1)),
                (("return", 2), ("c", 1)),
                (("call fn", 5), ("return", 2)),
                (("r", 5), ("call fn", 5)),
            }
            self.assertEqual(result, self.extract(provider))

        def test_def_args(self):
            self.run_args[2]['code'] = ("def fn(a, *args):\n"
                                        "    return a + args[0]\n"
                                        "x, y, z = 1, 2, 3\n"
                                        "r = fn(x, y, z)")
            provider = run(*self.run_args)
            result = {
                (("a", 1), ("x", 3)),
                (("args", 1), ("y", 3)),
                (("args", 1), ("z", 3)), #ToDo: fix?
                (("return", 2), ("a", 1)),
                (("return", 2), ("args", 1)),
                (("call fn", 4), ("return", 2)),
                (("r", 4), ("call fn", 4)),
            }
            self.assertEqual(result, self.extract(provider))

        def test_def_args_call_args(self):
            self.run_args[2]['code'] = ("def fn(a, *args):\n"
                                        "    return a + args[0]\n"
                                        "x, y = 1, [2, 3]\n"
                                        "r = fn(x, *y)")
            provider = run(*self.run_args)
            result = {
                (("a", 1), ("x", 3)),
                (("args", 1), ("y", 3)),
                (("return", 2), ("a", 1)),
                (("return", 2), ("args", 1)),
                (("call fn", 4), ("return", 2)),
                (("r", 4), ("call fn", 4)),
            }
            self.assertEqual(result, self.extract(provider))

        def test_def_args_call_kw(self):
            self.run_args[2]['code'] = ("def fn(a, *args):\n"
                                        "    return a\n"
                                        "x = {'a': 1}\n"
                                        "r = fn(**x)")
            provider = run(*self.run_args)
            result = {
                (("a", 1), ("x", 3)),
                (("args", 1), ("x", 3)), #ToDo: fix?
                (("return", 2), ("a", 1)),
                (("call fn", 4), ("return", 2)),
                (("r", 4), ("call fn", 4)),
            }
            self.assertEqual(result, self.extract(provider))

        def test_def_kwargs_call_keywords(self):
            self.run_args[2]['code'] = ("def fn(a, **kwargs):\n"
                                        "    return a + kwargs['b']\n"
                                        "x, y = 1, 1\n"
                                        "r = fn(x, b=y)")
            provider = run(*self.run_args)
            result = {
                (("a", 1), ("x", 3)),
                (("kwargs", 1), ("y", 3)), 
                (("return", 2), ("a", 1)),
                (("return", 2), ("kwargs", 1)),
                (("call fn", 4), ("return", 2)),
                (("r", 4), ("call fn", 4)),
            }
            self.assertEqual(result, self.extract(provider))

        def test_def_kwargs_call_kwargs(self):
            self.run_args[2]['code'] = ("def fn(a, **kwargs):\n"
                                        "    return a + kwargs['b']\n"
                                        "x = {'a': 1, 'b': 2}\n"
                                        "r = fn(**x)")
            provider = run(*self.run_args)
            result = {
                (("a", 1), ("x", 3)),
                (("kwargs", 1), ("x", 3)), 
                (("return", 2), ("a", 1)),
                (("return", 2), ("kwargs", 1)),
                (("call fn", 4), ("return", 2)),
                (("r", 4), ("call fn", 4)),
            }
            self.assertEqual(result, self.extract(provider))

        def test_complex(self):
            self.run_args[2]['code'] = ("def fn(a, b, c, d, " 
                                                "e=5, f=6, g=7, **kwargs):\n"
                                        "    return a\n"
                                        "x, y, z, w, u = 1, 2, [3, 4], 5, 7\n"
                                        "v = {'h': 8}\n"
                                        "r = fn(x, y, *z, e=w, g=u, **v)")
            provider = run(*self.run_args)
            result = {
                (("a", 1), ("x", 3)),
                (("b", 1), ("y", 3)),
                (("c", 1), ("z", 3)),
                (("c", 1), ("v", 4)), #ToDo: fix?
                (("d", 1), ("z", 3)),
                (("d", 1), ("v", 4)), #ToDo: fix?
                (("e", 1), ("w", 3)),
                (("f", 1), ("z", 3)), #ToDo: fix?
                (("f", 1), ("v", 4)), #ToDo: fix?
                (("g", 1), ("u", 3)), 
                (("kwargs", 1), ("z", 3)), #ToDo: fix? 
                (("kwargs", 1), ("v", 4)), 
                (("return", 2), ("a", 1)),
                (("call fn", 5), ("return", 2)),
                (("r", 5), ("call fn", 5)),
            }
            self.assertEqual(result, self.extract(provider))

        def test_nested(self):
            self.run_args[2]['code'] = ("def fn(a):\n"
                                        "    return a\n"
                                        "x = 1\n"
                                        "r = fn(fn(x))")
            provider = run(*self.run_args)
            result = {
                (("a", 1), ("x", 3)),
                (("a", 1), ("call fn", 4)), 
                (("return", 2), ("a", 1)),
                (("call fn", 4), ("return", 2)),
                (("r", 4), ("call fn", 4)),
            }
            self.assertEqual(result, self.extract(provider))
