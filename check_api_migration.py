"""Check the API migration against the pre-migration geometry and notebook run."""
from pathlib import Path
import ast
import hashlib
import json
import build123d
import nbformat

OUT = Path(__file__).parent
baseline = json.loads((OUT / 'api_migration_baseline.json').read_text())
current = json.loads((OUT / 'verification.json').read_text())
assert current['pass']
assert current == baseline, 'Geometry verification changed during the API migration.'
stl_hash = hashlib.sha256((OUT / 'rebuilt.stl').read_bytes()).hexdigest()
assert stl_hash == baseline['rebuilt_sha256'], 'Exported STL changed.'

nb = nbformat.read(OUT / 'reconstruction.ipynb', as_version=4)
cells = [c for c in nb.cells if c.cell_type == 'code']
assert all(c.execution_count is not None for c in cells)
assert not [o for c in cells for o in c.outputs if o.output_type == 'error']
assert not any('add() is deprecated' in str(o) for c in cells for o in c.outputs)

sources = {name: (OUT / name).read_text(encoding='utf-8')
           for name in ('model_template.py', 'model.py', 'model_mcp.py')}
sources['reconstruction.ipynb'] = '\n'.join(c.source for c in cells)
counts = {}
functions = {}
for name, source in sources.items():
    tree = ast.parse(source)
    calls = [n.func.id for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert 'add' not in calls, f'Deprecated builder call remains in {name}'
    counts[name] = calls.count('insert')
    assert counts[name] == 9, (name, counts[name])
    functions[name] = {n.name: ast.dump(n, include_attributes=False)
                       for n in tree.body if isinstance(n, ast.FunctionDef)}
    compile(source, name, 'exec')
for name in sources:
    for function_name, definition in functions['model_template.py'].items():
        assert functions[name][function_name] == definition, (name, function_name)

gate = json.loads((OUT / 'step_gate.json').read_text())
assert gate['banked'], 'Written and reimported STEP gate failed.'
result = {
    'passed': True,
    'local_build123d_version': build123d.__version__,
    'insert_calls_per_artifact': counts,
    'fresh_kernel_code_cells': len(cells),
    'deprecated_builder_calls': 0,
    'deprecated_builder_warnings': 0,
    'model_function_ast_matches': True,
    'verification_identical_to_baseline': True,
    'stl_byte_identical': True,
    'stl_sha256': stl_hash,
    'step_gate_banked': gate['banked'],
    'hausdorff_mm': current['hausdorff'],
    'volume_ratio': current['volume_ratio'],
    'euler': current['euler'],
    'bodies': current['bodies'],
}
(OUT / 'api_migration_check.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
