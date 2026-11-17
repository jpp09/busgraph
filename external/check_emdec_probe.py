"""Run only the reviewed route-list parser against captured HTTP responses."""
import ast
import asyncio
from pathlib import Path
import re

root = Path(__file__).resolve().parent
source = root / 'emdec-gtfs' / 'linhas.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
functions = [node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
             and node.name in {'fix_route_name', 'linhas'}]
assert len(functions) == 2
for node in functions:
    node.decorator_list = []  # No cache or third-party imports.
module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
for capture in sorted(root.glob('emdec-gtfs-probe*.html')):
    async def fetch_url(url):
        return capture.read_text(encoding='utf-8', errors='replace')
    namespace = {'re': re, 'fetch_url': fetch_url}
    exec(compile(module, str(source), 'exec'), namespace)
    routes = asyncio.run(namespace['linhas']())
    print(f'{capture.name}: {len(routes)} routes extracted')
