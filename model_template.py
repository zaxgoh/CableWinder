"""Parametric winder reconstruction in native STL coordinates, millimetres.

The pin and bore are revolved features. Measured periodic profiles describe
the compound channel and latch transitions, not the STL's triangle faces.
Edit named dimensions or profile control points, then rerun build_model().
"""
from build123d import *

# Dimensions in millimetres. Reference height 16.6000004.
height = 16.6
reference_height = 16.6
body_center_x = -144.682
body_center_y = 22.603
pin_center_x = -132.756
pin_center_y = 34.177
xy_scale = 1.0
core_floor_thickness = 0.6
core_reference_radius = 27.5
core_embed_inset = 0.2
ring_bridge_height = 2.6
bridge_bore_relief = 0.2  # local join clearance; avoids a nearly coincident annular ledge
pin_waist_radius = 4.584
pin_head_radius = 7.084
pin_end_radius = 6.784
pin_end_chamfer = 0.3
pin_head_shoulder = 1.0
pin_waist_start = 3.5
bore_waist_radius = 5.084
bore_head_radius = 7.584
bore_end_radius = 7.884
bore_end_chamfer = 0.3
bore_head_shoulder = 1.2
bore_waist_start = 3.7
cutter_margin = 1.0
profile_approximation_tolerance = 0.02
profile_segments = 16
profile_span_samples = 16
feature_overlap = 0.15
latch_cleanup_offset_x = 28.782
latch_cleanup_offset_y = -1.753
latch_cleanup_width = 1.4
latch_cleanup_length = 2.1
latch_cleanup_depth = 0.3

def section_face(record, z_override=None, radial_inset=0.0):
    z = record['z'] if z_override is None else z_override
    section_scale=xy_scale*(1-radial_inset/core_reference_radius)
    xyz = [(body_center_x+(x-body_center_x)*section_scale,
            body_center_y+(y-body_center_y)*section_scale,
            z*height/reference_height) for x,y in record['points']]
    # Approximate the faceted section with short, low-degree spline spans.
    vectors=[Vector(*p) for p in xyz]
    count=len(vectors)
    edges=[]
    for segment in range(profile_segments):
        start=segment*count//profile_segments
        end=(segment+1)*count//profile_segments
        points=[vectors[j%count] for j in range(start,end+1)]
        smooth=Edge.make_spline_approx(points,
                     tol=profile_approximation_tolerance,min_deg=3,max_deg=3)
        fit_points=[smooth@(j/profile_span_samples) for j in range(profile_span_samples+1)]
        edges.append(Edge.make_spline(fit_points,
                     parameters=[float(j) for j in range(profile_span_samples+1)]))
    return Face(Wire(edges))

def profile_loft(records, bottom=None, top=None, bottom_inset=0.0):
    faces = [section_face(rec,
             bottom if j==0 and bottom is not None else
             top if j==len(records)-1 and top is not None else None,
             radial_inset=bottom_inset if j==0 else 0.0)
             for j,rec in enumerate(records)]
    with BuildPart() as feature:
        loft(sections=faces, ruled=True)
    return feature.part

def revolved_feature(radial_stations, cx, cy):
    # radius-height coordinates in a local XZ sketch, then revolve about Z.
    pts=[(0,radial_stations[0][1])]+radial_stations+[(0,radial_stations[-1][1])]
    plane=Plane(origin=(cx,cy,0),x_dir=(1,0,0),z_dir=(0,-1,0))
    with BuildPart() as feature:
        with BuildSketch(plane):
            with BuildLine():
                Polyline(*pts,close=True)
            make_face()
        revolve(axis=Axis((cx,cy,0),(0,0,1)))
    return feature.part

def build_model():
    core_floor=profile_loft(PROFILES['core_floor'],top=core_floor_thickness)
    core_hook=profile_loft(PROFILES['core_hook'],bottom=core_floor_thickness-feature_overlap,
                            bottom_inset=core_embed_inset)
    with BuildPart() as core_build:
        insert(core_floor)
        insert(core_hook)
    core_blank=core_build.part
    bore_stations=[(bore_end_radius,-cutter_margin),
        (bore_end_radius,0), (bore_head_radius,bore_end_chamfer),
        (bore_head_radius,bore_head_shoulder),
        (bore_waist_radius,bore_waist_start),
        (bore_waist_radius,height-bore_waist_start),
        (bore_head_radius,height-bore_head_shoulder),
        (bore_head_radius,height-bore_end_chamfer),
        (bore_end_radius,height),(bore_end_radius,height+cutter_margin)]
    bore=revolved_feature(bore_stations,pin_center_x,pin_center_y)
    with BuildPart() as core_build:
        insert(core_blank)
        insert(bore,mode=Mode.SUBTRACT)
    core=core_build.part

    ring_floor=profile_loft(PROFILES['ring_floor_outer'],top=ring_bridge_height)
    inner=[(r+bridge_bore_relief if j==len(PROFILES['ring_floor_inner'])-1 else r,
            ring_bridge_height if j==len(PROFILES['ring_floor_inner'])-1 else z)
           for j,(z,r) in enumerate(PROFILES['ring_floor_inner'])]
    inner=[(inner[0][0],-cutter_margin)]+inner+[(inner[-1][0],ring_bridge_height+cutter_margin)]
    ring_bore=revolved_feature(inner,body_center_x,body_center_y)
    with BuildPart() as ring_base:
        insert(ring_floor)
        insert(ring_bore,mode=Mode.SUBTRACT)
    ring_open=profile_loft(PROFILES['ring_open'],bottom=ring_bridge_height-feature_overlap)
    with BuildPart() as ring_build:
        insert(ring_base.part)
        insert(ring_open)
    ring=ring_build.part
    with BuildPart() as ring_finish:
        insert(ring)
        with Locations((body_center_x+latch_cleanup_offset_x,
                        body_center_y+latch_cleanup_offset_y,height-latch_cleanup_depth)):
            Box(latch_cleanup_width,latch_cleanup_length,latch_cleanup_depth+cutter_margin,
                align=(Align.CENTER,Align.CENTER,Align.MIN),mode=Mode.SUBTRACT)
    ring=ring_finish.part

    pin_stations=[(pin_end_radius,0),(pin_head_radius,pin_end_chamfer),
        (pin_head_radius,pin_head_shoulder),(pin_waist_radius,pin_waist_start),
        (pin_waist_radius,height-pin_waist_start),
        (pin_head_radius,height-pin_head_shoulder),
        (pin_head_radius,height-pin_end_chamfer),(pin_end_radius,height)]
    pin=revolved_feature(pin_stations,pin_center_x,pin_center_y)
    return core,ring,pin

# PROFILE_DATA

core, ring, pin = build_model()
result = Compound(children=[core, ring, pin])
