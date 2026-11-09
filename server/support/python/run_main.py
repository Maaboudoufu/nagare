"""Run a lesson's main.py the way in-browser Python (Pyodide) does: top-level `await` is allowed.
Usage: python3 run_main.py main.py"""
import ast
import asyncio
import os
import sys
import types

path = os.path.abspath(sys.argv[1])
sys.argv = sys.argv[1:]
sys.path[0] = os.path.dirname(path)  # import the lesson's own files, like `python3 main.py` would
code = compile(open(path).read(), path, "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
module = types.ModuleType("__main__")
module.__file__ = path
sys.modules["__main__"] = module
result = eval(code, module.__dict__)
if asyncio.iscoroutine(result):  # the file used top-level await
    asyncio.run(result)
