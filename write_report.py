from pathlib import Path
import ast, json, hashlib
import nbformat

OUT=Path(__file__).parent
v=json.loads((OUT/'verification.json').read_text())
assert v['pass'], 'Final numerical comparison must pass before writing the report.'
nb=nbformat.read(OUT/'reconstruction.ipynb',as_version=4)
code_cells=[c for c in nb.cells if c.cell_type=='code']
assert all(c.execution_count is not None for c in code_cells)
assert not [o for c in code_cells for o in c.outputs if o.output_type=='error']
gate=json.loads((OUT/'step_gate.json').read_text())
assert gate['banked']
parameters=[]
for node in ast.parse((OUT/'model_template.py').read_text()).body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
        try:value=ast.literal_eval(node.value)
        except (ValueError,TypeError):continue
        if isinstance(value,(int,float)):parameters.append((node.targets[0].id,value))
rows='\n'.join(f'| `{name}` | {value:g} |' for name,value in parameters)
euler=' / '.join(str(x) for x in v['euler'])
body_euler=' / '.join(str(x) for x in v['body_euler'])
extent=', '.join(f'{x:+.5f}' for x in v['extent_delta'])
volume_delta=100*(v['volume_ratio']-1)
adaptive=sum(v.get('adaptive_brep_volumes',{}).values())
migration_path=OUT/'api_migration_check.json'
migration_note=''
if migration_path.exists():
    migration=json.loads(migration_path.read_text())
    assert migration['passed'] and migration['stl_sha256']==v['rebuilt_sha256']
    migration_note=f'''\n## Builder API migration validation\n\nThe nine builder operations now use `insert()` in the source template, both generated\nPython modules, and the notebook. Official release notes document `add()` as a deprecated\nwrapper around `insert()`: https://github.com/gumyr/build123d/releases.\n\nThe MCP module rebuilt successfully on build123d 0.13.0. The notebook completed a fresh-kernel\nRun All on build123d {migration['local_build123d_version']} with no deprecated builder warnings.\nAll geometry verification values match the pre-migration baseline exactly, and the exported\nSTL is byte-for-byte identical. The written and reimported STEP gate passed again.\nSee `api_migration_check.json` and `api_migration_baseline.json` for regression evidence.\n'''
report=f'''# Earphone cable winder reconstruction

**Result:** passes the requested numerical comparison at the supplied parameter values.
This is an approximate parametric redesign. The original CAD history was not recovered.

## Target and achieved

| Check | Target | Achieved |
|---|---|---|
| Bidirectional checked Hausdorff | ≤ 0.5 mm | **{v['hausdorff']:.6f} mm** |
| Exported volume difference | within 1% | **{volume_delta:+.6f}%** |
| Overall Euler number, original / rebuilt | equal | **{euler}** |
| Per-body Euler numbers, original / rebuilt | equal | {body_euler} |
| Bodies, original / rebuilt | 3 / 3 | {v['bodies'][0]} / {v['bodies'][1]} |
| Watertight, original / rebuilt | true / true | {v['watertight'][0]} / {v['watertight'][1]} |
| Extent delta X, Y, Z | each ≤ 0.5 mm absolute | {extent} mm |
| Written and re-imported STEP gate | valid manifold solids | PASS |
| Fresh-kernel notebook Run All | complete without errors | PASS ({len(code_cells)} code cells) |

| Surface-distance statistic | mm |
|---|---:|
| Mean | {v['mean']:.6f} |
| p95 | {v['p95']:.6f} |
| p99 | {v['p99']:.6f} |
| Maximum of surface samples | {v['max']:.6f} |
| Original → rebuilt sample maximum | {v['directional_max'][0]:.6f} |
| Rebuilt → original sample maximum | {v['directional_max'][1]:.6f} |
| Original-vertex maximum | {v['vertex_max'][0]:.6f} |
| Rebuilt-vertex maximum | {v['vertex_max'][1]:.6f} |

Original volume: {v['volume_original']:.6f} mm³. Rebuilt exported volume: {v['volume_rebuilt']:.6f} mm³.
Adaptive BREP volume: {adaptive:.6f} mm³. The notebook uses adaptive integration for spline solids;
build123d's default fixed-quadrature `.volume` can differ noticeably on these detailed faces.

Distances use point-to-triangle nearest-surface queries with rtree: 50,000 deterministic
area-weighted samples in each direction (seeds 20261020 and 20261021), plus every mesh vertex
in both directions. The checked Hausdorff is the largest of these distances. This is the
skill's sampled method with extra vertex checks, not a certified continuous-surface upper bound.
Worst-mismatch coordinates are retained in `verification.json`; raw points and distances are
in `deviation_samples.npz`. Section overlays and the deviation plot were visually inspected.

## Reference, triage, and coordinates

Reference: `earbud_winder_100pct.stl`, explicitly attached in the request. `target_part.stl`
was absent from the working directory. `reference.stl` is an unchanged local copy.

Units are millimetres as supplied. Native XYZ coordinates are preserved: transform = identity.
No translation, rotation, recentering, or unit conversion was applied.

The original has 46,428 triangles, 23,216 vertices, consistent winding, and three watertight
bodies. Bounds are (-177.231155, -9.942570, 0) to (-112.132156, 55.153431, 16.600000) mm.
The three bodies are interpreted as winding core, retaining ring, and captive pin; their
original Euler numbers are 0, 0, and 2. No repairs were applied to the reference.

This was a difficult mechanical/freeform reconstruction. Z is the stacking/revolve axis.
The pin is symmetric to about 0.002 mm; the channel and retaining-ring opening break whole-part
mirror symmetry. The core floor changes topology at Z=0.6 mm and the ring bridge at Z=2.6 mm.

MCP build123d 0.13.0 provided `detect_primitives`. Detection used a cached isolated pin BREP
(2,264 faces versus 46,428 in the full assembly). A half-pin split returned an empty shape,
so the isolated pin was retained as the reduced working region. Detection left 993 faces
unclassified (43.9%) and emitted spurious tilted cylinders. Its output is retained as a report
in `primitive_detection.json`; none of its fragments is used as model code. Levels, normals,
and cross-sections supplied the main measurements.

## Construction and regions treated as freeform

The pin and core bore are clean revolved radial profiles with named waist/head radii,
conical shoulders, and 0.3 mm end bevels. The core and ring are separate builder-mode
features: lower floor/bridge lofts, upper profiles, additive unions, and subtractive bores.

**The winding channel, outer groove, ring opening, and latch transitions are treated as
freeform measured section lofts.** Their controls are in `measured_profiles.json`. They are
not claimed to reproduce the original analytic construction. Profiles are fitted with a
0.02 mm low-degree approximation budget, then resampled onto compatible spline parameters.
Ruled lofts use 0.5 mm height spacing with extra stations at transitions. This can leave
subtle changes in surface slope at section heights; it is an approximation within the stated
measured tolerance. No STL triangles are used as final CAD faces.

## Assumptions, simplifications, and local adjustments

- Functional body names are inferred from the geometry. The assembled positions match the STL.
- Original curved-face faceting is smoothed; individual mesh facets are not reproduced.
  Small circular residuals include source faceting and were not chased.
- No text was identified. End bevels on the pin and bore are represented in their profiles.
- The core's starting profile is embedded 0.2 mm into the floor and overlaps vertically by
  0.15 mm, avoiding a nearly coincident underside lip. Its native placement is retained.
- A 0.2 mm local bore relief is applied at the ring bridge join.
- A local upper-latch relief is 1.4 × 2.1 mm in XY and 0.3 mm deep, centred at
  (-115.900, 20.850) mm. This replaces a numerically troublesome tiny patch and is an intentional
  local approximation. It is included in the final distance/volume checks.
- An experimental cable-tip trim exceeded tolerance and changed topology; it was discarded.
  It is absent from the final model.
- Export cleanup removes only zero-area or duplicate STL triangles. It does not move vertices,
  weld distinct geometry, fill holes, or modify the reference mesh.

The first exported draft passed distance (0.440475 mm) and volume (-0.0643%) but failed
watertightness/Euler checks. Subsequent corrections targeted mesh/CAD join quality. Dense
interpolation and alternate ring correspondence were rejected. The final fixed-parameter,
low-degree profiles and embedded core join pass the STEP gate and the numerical comparison.

## Final parameters

Linear dimensions and coordinate offsets below are in mm; `xy_scale` is dimensionless and
profile segment/sample values are counts. Section Z/XY controls are named by feature in
`measured_profiles.json`.

| Parameter | Value |
|---|---:|
{rows}

## Files and rerunning

- `reconstruction.ipynb`: all ten requested sections, with saved fresh-kernel outputs.
- `model.py`: readable parametric module; section controls are loaded from the adjacent JSON.
- `model_mcp.py`: equivalent embedded-data source for the MCP sandbox.
- `rebuilt.step`, `rebuilt.stl`, `rebuilt.brep`: final CAD, print mesh, and model cache.
- `verification.json`, `deviation.png`, `section_overlays.png`, `preview.png`: evidence.
- `working_pin.brep`, `primitive_detection.json`: cached reduced analysis and detection report.

Use the project `.venv` kernel and Run All from the notebook directory. Detection,
faceted-BREP import, profile remeasurement, model rebuilding, viewer display, and verification
have explicit switches. Default settings rebuild and verify the model. The verification cache
is accepted only for matching reference/export SHA256 hashes.

Reference SHA256: `{v['reference_sha256']}`.
Verified STL SHA256: `{v['rebuilt_sha256']}`.
{migration_note}
'''
(OUT/'report.md').write_text(report,encoding='utf-8')
print('Report written. Final checked Hausdorff:',v['hausdorff'],'volume delta %:',volume_delta)
