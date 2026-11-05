import bpy
import math
import os
import sys
import random
from mathutils import Vector

# ------------------------------------------------------------
# THE WILDHEART — procedural cinematic magical wooden staff
# Blender 4.5 LTS | 1280x720 | 8 seconds | 24 fps
# No external assets required.
# ------------------------------------------------------------

def cli_output_dir():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = "output"
    for i, item in enumerate(args):
        if item == "--output-dir" and i + 1 < len(args):
            out = args[i + 1]
    return os.path.abspath(out)

OUT = cli_output_dir()
FRAMES_DIR = os.path.join(OUT, "frames")
os.makedirs(FRAMES_DIR, exist_ok=True)

random.seed(73)
FPS = 60
DURATION_SECONDS = 8
LAST_FRAME = FPS * DURATION_SECONDS
PREVIEW_ONLY = "--preview-only" in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.materials, bpy.data.curves, bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
    # Keep Blender's datablocks clean between runs.
    pass

def set_principled(mat, color, metallic=0.0, roughness=0.45, emission=None, emission_strength=0.0):
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1.0)
    bs.inputs["Metallic"].default_value = metallic
    bs.inputs["Roughness"].default_value = roughness
    if emission is not None:
        if "Emission Color" in bs.inputs:
            bs.inputs["Emission Color"].default_value = (*emission, 1.0)
            bs.inputs["Emission Strength"].default_value = emission_strength
        else:
            bs.inputs["Emission"].default_value = (*emission, 1.0)
            bs.inputs["Emission Strength"].default_value = emission_strength
    return mat

def make_wood():
    m = bpy.data.materials.new("Heartwood | procedural walnut, ridged grain")
    m.use_nodes = True
    n = m.node_tree.nodes
    l = m.node_tree.links
    bs = n.get("Principled BSDF")
    bs.inputs["Roughness"].default_value = 0.68
    bs.inputs["Metallic"].default_value = 0.04
    tex = n.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 3.8
    tex.inputs["Detail"].default_value = 7.0
    tex.inputs["Roughness"].default_value = 0.78
    tex.inputs["Distortion"].default_value = 2.6
    mapping = n.new("ShaderNodeVectorMath")
    mapping.operation = "MULTIPLY"
    mapping.inputs[1].default_value = (2.4, 2.4, 0.38)
    coord = n.new("ShaderNodeTexCoord")
    l.new(coord.outputs["Generated"], mapping.inputs[0])
    l.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.16
    ramp.color_ramp.elements[0].color = (0.035, 0.012, 0.008, 1)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = (0.34, 0.13, 0.045, 1)
    e = ramp.color_ramp.elements.new(0.48)
    e.color = (0.12, 0.043, 0.018, 1)
    l.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.27
    bump.inputs["Distance"].default_value = 0.075
    l.new(tex.outputs["Fac"], bump.inputs["Height"])
    l.new(bump.outputs["Normal"], bs.inputs["Normal"])
    return m

def make_orb_material(name, phase):
    # Pure emissive marbling keeps the jewel saturated instead of washing it out
    # under the strong cinematic area lights.
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes
    l = m.node_tree.links
    n.clear()

    output = n.new("ShaderNodeOutputMaterial")
    output.location = (620, 80)
    texcoord = n.new("ShaderNodeTexCoord")
    texcoord.location = (-620, 80)

    noise = n.new("ShaderNodeTexNoise")
    noise.location = (-390, 80)
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = 2.15
    noise.inputs["Detail"].default_value = 7.0
    noise.inputs["Roughness"].default_value = 0.78
    noise.inputs["Distortion"].default_value = 4.2
    noise.inputs["W"].default_value = phase
    l.new(texcoord.outputs["Generated"], noise.inputs["Vector"])

    ramp = n.new("ShaderNodeValToRGB")
    ramp.location = (-100, 80)
    cr = ramp.color_ramp
    cr.elements.remove(cr.elements[1])
    stops = [
        (0.10, (0.004, 0.012, 0.18, 1)),
        (0.30, (0.004, 0.30, 0.90, 1)),
        (0.45, (0.005, 0.82, 0.70, 1)),
        (0.59, (0.34, 0.008, 0.82, 1)),
        (0.73, (0.92, 0.018, 0.30, 1)),
        (0.88, (1.00, 0.28, 0.018, 1)),
    ]
    cr.elements[0].position = stops[0][0]
    cr.elements[0].color = stops[0][1]
    for pos, color in stops[1:]:
        el = cr.elements.new(pos)
        el.color = color
    l.new(noise.outputs["Fac"], ramp.inputs["Fac"])

    emission = n.new("ShaderNodeEmission")
    emission.location = (300, 80)
    emission.inputs["Strength"].default_value = 0.9
    l.new(ramp.outputs["Color"], emission.inputs["Color"])
    l.new(emission.outputs["Emission"], output.inputs["Surface"])

    # Animate the 4D coordinate so the colored currents flow inside the sphere.
    for frame, value in ((1, phase), (FPS * 4, phase + 2.1), (LAST_FRAME, phase + 4.2)):
        noise.inputs["W"].default_value = value
        noise.inputs["W"].keyframe_insert(data_path="default_value", frame=frame)
    return m

def emission_mat(name, color, strength):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    em = n.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    m.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m

def curve_obj(name, points, radii, material, bevel=0.04, resolution=8):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 16
    cu.bevel_depth = bevel
    cu.bevel_resolution = resolution
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (p[0], p[1], p[2], 1)
        sp.points[i].radius = radii[i] if i < len(radii) else 1.0
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    if material:
        ob.data.materials.append(material)
    return ob

def uv_sphere(name, loc, scale, material, segments=48, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    if material:
        ob.data.materials.append(material)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob

def torus(name, loc, major, minor, material, rotation=(0, 0, 0), major_segments=96):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=major_segments, minor_segments=16,
        location=loc, major_radius=major, minor_radius=minor,
        rotation=rotation
    )
    ob = bpy.context.object
    ob.name = name
    if material:
        ob.data.materials.append(material)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob

def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

def add_area(name, loc, target, power, color, size):
    bpy.ops.object.light_add(type="AREA", location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.data.energy = power
    ob.data.color = color
    ob.data.shape = "DISK"
    ob.data.size = size
    aim(ob, target)
    return ob

def animate_rotation(ob, axis, start, end, first=1, last=LAST_FRAME):
    ob.rotation_euler[axis] = start
    ob.keyframe_insert(data_path="rotation_euler", frame=first)
    ob.rotation_euler[axis] = end
    ob.keyframe_insert(data_path="rotation_euler", frame=last)
    if ob.animation_data and ob.animation_data.action:
        for fc in ob.animation_data.action.fcurves:
            for key in fc.keyframe_points:
                key.interpolation = "LINEAR"

# Materials
wood = make_wood()
bark_dark = set_principled(bpy.data.materials.new("Deep bark"), (0.035, 0.012, 0.009), roughness=0.78)
gold = set_principled(bpy.data.materials.new("Old elven gold"), (0.62, 0.31, 0.075), metallic=0.86, roughness=0.22)
gold_light = set_principled(bpy.data.materials.new("Bright champagne gold"), (0.92, 0.63, 0.22), metallic=0.78, roughness=0.17)
leaf_mats = [
    set_principled(bpy.data.materials.new("Jade leaves"), (0.018, 0.20, 0.105), metallic=0.12, roughness=0.3),
    set_principled(bpy.data.materials.new("Emerald leaves"), (0.025, 0.37, 0.19), metallic=0.08, roughness=0.28),
    set_principled(bpy.data.materials.new("Moonlit teal leaves"), (0.035, 0.27, 0.31), metallic=0.22, roughness=0.24),
]
orb_mat = make_orb_material("Prismatic living light | animated iridescence", 0.0)
core_mat = emission_mat("Orb inner heart", (0.025, 0.22, 0.95), 0.65)
cyan_glow = emission_mat("Aether cyan", (0.12, 0.74, 1.0), 3.0)
mint_glow = emission_mat("Spirit mint", (0.15, 1.0, 0.58), 2.3)
violet_glow = emission_mat("Arcane violet", (0.48, 0.16, 1.0), 2.5)
warm_glow = emission_mat("Ancient amber", (1.0, 0.48, 0.10), 1.6)

# Scene and world
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.eevee.taa_render_samples = 4
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 80
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = LAST_FRAME
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False
scene.render.image_settings.compression = 10
scene.render.filepath = os.path.join(FRAMES_DIR, "frame_")
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = 0.15
scene.view_settings.gamma = 1.0

world = bpy.data.worlds.new("Blue hour in the ancient grove") if not bpy.data.worlds else bpy.data.worlds[0]
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.012, 0.027, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.22

# The main staff: asymmetrical, naturally grown, with twisting root grain.
trunk_points = [
    (0.00, 0.00, -0.02), (-0.06, 0.015, 0.34), (0.045, 0.0, 0.78),
    (-0.02, 0.035, 1.18), (0.10, 0.015, 1.62), (0.07, -0.015, 2.05),
    (-0.02, 0.025, 2.50), (0.055, 0.0, 2.92), (0.13, 0.0, 3.34),
    (0.06, 0.015, 3.72), (0.0, 0.02, 4.02), (0.07, 0.0, 4.28),
]
trunk_r = [0.95, 1.05, 0.82, 0.74, 0.72, 0.66, 0.61, 0.58, 0.55, 0.51, 0.46, 0.40]
trunk = curve_obj("01 | Living heartwood staff", trunk_points, trunk_r, wood, bevel=0.18, resolution=12)

# Split roots at the base.
root_branches = [
    [(-0.01, 0.0, 0.12), (-0.22, -0.015, 0.05), (-0.39, -0.05, -0.03), (-0.55, -0.08, -0.02)],
    [(0.0, 0.0, 0.18), (0.18, -0.10, 0.10), (0.31, -0.17, -0.02), (0.48, -0.24, -0.01)],
    [(0.0, 0.04, 0.27), (-0.10, 0.19, 0.12), (-0.18, 0.31, -0.02), (-0.28, 0.39, -0.02)],
    [(0.0, 0.03, 0.22), (0.11, 0.16, 0.12), (0.19, 0.29, 0.01), (0.28, 0.42, -0.02)],
]
for i, pts in enumerate(root_branches):
    curve_obj(f"Root tendril {i+1}", pts, [0.85, 0.72, 0.42, 0.05], wood, bevel=0.10, resolution=10)

# Branches climb and wrap around the crystal.
branch_specs = [
    [(0.02, 0.015, 3.72), (-0.22, -0.02, 3.98), (-0.48, -0.02, 4.20), (-0.60, -0.01, 4.48), (-0.52, 0.0, 4.76), (-0.31, 0.0, 4.93)],
    [(0.03, 0.02, 3.93), (0.27, 0.0, 4.13), (0.51, 0.02, 4.39), (0.58, 0.0, 4.68), (0.43, 0.0, 4.93), (0.22, 0.0, 5.02)],
    [(0.05, 0.0, 4.12), (-0.08, 0.15, 4.37), (-0.12, 0.28, 4.66), (0.0, 0.34, 4.89), (0.18, 0.30, 5.05)],
    [(0.08, 0.0, 4.05), (0.19, -0.17, 4.30), (0.24, -0.28, 4.61), (0.12, -0.32, 4.88), (-0.08, -0.27, 5.02)],
]
for i, pts in enumerate(branch_specs):
    curve_obj(f"02 | Orb cradle branch {i+1}", pts, [0.78, 0.68, 0.48, 0.28, 0.16, 0.04][:len(pts)], wood, bevel=0.105 if i < 2 else 0.075, resolution=10)

# Two stronger foreground roots visibly embrace the orb instead of hiding behind it.
front_cradles = [
    [(-0.10, -0.12, 4.18), (-0.42, -0.78, 4.42), (-0.70, -0.86, 4.72), (-0.78, -0.88, 5.05), (-0.70, -0.82, 5.36), (-0.42, -0.72, 5.58)],
    [(0.10, -0.10, 4.18), (0.42, -0.78, 4.42), (0.70, -0.86, 4.72), (0.78, -0.88, 5.05), (0.70, -0.82, 5.36), (0.42, -0.72, 5.58)],
]
for i, pts in enumerate(front_cradles):
    curve_obj(f"02b | Foreground living root {i+1}", pts, [0.82, 0.72, 0.55, 0.38, 0.22, 0.035], wood, bevel=0.125, resolution=12)
    # A fine amber sap line follows the outside edge of each root.
    sap_pts = [(x * 1.025, y - 0.026, z) for x, y, z in pts[1:]]
    curve_obj(f"Root sap vein {i+1}", sap_pts, [0.7, 0.65, 0.5, 0.3, 0.02], warm_glow, bevel=0.009, resolution=5)

# Fine twig curls and small leaves on upper branches.
for i in range(9):
    side = -1 if i % 2 == 0 else 1
    z = 3.88 + i * 0.115
    x = side * (0.18 + 0.06 * math.sin(i * 1.7))
    pts = [(x * 0.45, 0.0, z), (x, 0.02, z + 0.10), (x * 1.38, 0.05, z + 0.17)]
    curve_obj(f"Twig curl {i+1}", pts, [0.62, 0.34, 0.02], wood, bevel=0.032, resolution=6)

# Leaf meshes: elongated, tapered ellipsoids oriented along vectors.
def make_leaf(name, loc, direction, size, material):
    ob = uv_sphere(name, loc, (size * 0.30, size * 0.075, size), material, 24, 16)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = Vector(direction).to_track_quat("Z", "Y")
    return ob

leaf_positions = [
    (-0.37, -0.02, 4.10, -1), (-0.53, 0.0, 4.30, -1), (-0.47, 0.02, 4.63, -1),
    (-0.28, 0.02, 4.84, -1), (-0.10, 0.02, 4.98, -1), (0.34, 0.0, 4.18, 1),
    (0.52, 0.02, 4.38, 1), (0.50, 0.02, 4.68, 1), (0.34, 0.01, 4.90, 1),
    (0.16, 0.0, 5.05, 1), (-0.12, 0.22, 4.64, -1), (0.20, -0.24, 4.72, 1),
]
for i, (x, y, z, side) in enumerate(leaf_positions):
    make_leaf(f"Emerald leaf {i+1}", (x, y, z), (side * 0.85, 0.08, 0.50), 0.22 + (i % 3) * 0.035, leaf_mats[i % len(leaf_mats)])

# Delicate gold bindings along the lower grip, with inset details.
for i, z in enumerate([0.38, 0.48, 0.59, 1.08, 1.18, 1.28, 2.16, 2.24]):
    ob = torus(f"03 | Gold grip binding {i+1}", (0.0, 0.0, z), 0.135 - 0.004 * (z / 5), 0.018, gold_light)
    ob.scale.z = 0.82
# Tiny hammered gold studs on the bindings.
for i in range(8):
    angle = i * math.tau / 8
    uv_sphere(f"Binding rivet {i+1}", (0.135 * math.cos(angle), 0.135 * math.sin(angle), 1.16), (0.025, 0.025, 0.025), gold_light, 16, 12)

# Central orb, inner luminous heart, and concentric arcane geometry.
ORB = (0.0, 0.0, 5.02)
uv_sphere("04 | The Wildheart — prismatic orb", ORB, (0.72, 0.72, 0.72), orb_mat, 128, 96)
uv_sphere("Luminous core beneath the glass", (0.0, -0.012, 5.02), (0.29, 0.29, 0.29), core_mat, 96, 64)

# Thin orbital rings at different inclinations.
ring1 = torus("05 | Equatorial orbit", ORB, 0.84, 0.018, gold_light, (math.radians(68), math.radians(12), 0))
ring2 = torus("06 | Aether orbit", ORB, 0.92, 0.012, cyan_glow, (math.radians(22), math.radians(63), math.radians(15)))
ring3 = torus("07 | Inner rune orbit", ORB, 0.74, 0.014, violet_glow, (math.radians(78), math.radians(-22), 0))
animate_rotation(ring1, 2, 0, math.tau, 1, LAST_FRAME)
animate_rotation(ring2, 1, 0, -math.tau, 1, LAST_FRAME)
animate_rotation(ring3, 0, 0, math.tau, 1, LAST_FRAME)

# Curving gold filigree arcs echo the branches without obscuring the orb.
for k in range(3):
    pts = []
    radii = []
    for j in range(65):
        t = j / 64
        a = -1.1 + t * 2.25 + k * 2.094
        rr = 0.73 + 0.035 * math.sin(t * math.pi * 2 + k)
        pts.append((rr * math.cos(a), rr * math.sin(a), 5.02 + 0.14 * math.sin(a * 1.15 + k * 1.7)))
        radii.append(0.65 + 0.25 * math.sin(math.pi * t))
    ob = curve_obj(f"Orb filigree strand {k+1}", pts, radii, gold, bevel=0.012, resolution=5)
    animate_rotation(ob, 2, 0.0, (1 if k % 2 == 0 else -1) * 0.45, 1, LAST_FRAME)

# Spiral of aether winding around the shaft and rising to the orb.
for k, mat in enumerate([cyan_glow, violet_glow]):
    pts = []
    rs = []
    for j in range(170):
        t = j / 169
        angle = t * math.tau * 2.35 + k * math.pi
        z = 0.68 + t * 3.55
        radius = 0.20 + 0.08 * math.sin(t * math.pi)
        pts.append((radius * math.cos(angle), radius * math.sin(angle), z))
        rs.append(0.7 + 0.25 * math.sin(t * math.pi))
    ob = curve_obj(f"08 | Rising aether spiral {k+1}", pts, rs, mat, bevel=0.018, resolution=5)
    animate_rotation(ob, 2, 0, (1 if k == 0 else -1) * 0.32, 1, LAST_FRAME)

# A glowing runic halo just above the topmost branches.
halo = torus("Crown halo", (0, 0, 5.02), 1.08, 0.009, mint_glow, (math.radians(90), 0, 0))
animate_rotation(halo, 2, 0, -math.tau, 1, LAST_FRAME)

# Small suspended motes, each with a subtle vertical drift.
for i in range(78):
    a = random.random() * math.tau
    r = random.uniform(0.75, 2.05)
    z = random.uniform(0.25, 5.9)
    loc = (math.cos(a) * r, math.sin(a) * r, z)
    mat = [cyan_glow, mint_glow, violet_glow, warm_glow][i % 4]
    s = random.uniform(0.012, 0.034)
    p = uv_sphere(f"09 | Floating spirit mote {i+1:02d}", loc, (s, s, s), mat, 12, 8)
    p.location.z = z - 0.08
    p.keyframe_insert(data_path="location", frame=1)
    p.location.z = z + 0.08
    p.keyframe_insert(data_path="location", frame=LAST_FRAME)
    if p.animation_data and p.animation_data.action:
        for fc in p.animation_data.action.fcurves:
            for key in fc.keyframe_points:
                key.interpolation = "SINE"

# Small pointed leaflets and buds clustered around the crystal cradle.
for i in range(16):
    a = i * math.tau / 16
    loc = (0.69 * math.cos(a), 0.69 * math.sin(a), 4.95 + 0.11 * math.sin(a * 2))
    uv_sphere(f"Amber seed {i+1}", loc, (0.034, 0.034, 0.034), gold_light, 16, 12)

# Stone-and-root pedestal.
stone = set_principled(bpy.data.materials.new("Obsidian mossstone"), (0.018, 0.035, 0.046), metallic=0.28, roughness=0.3)
bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=1.02, depth=0.20, location=(0, 0, -0.20))
ped = bpy.context.object
ped.name = "10 | Mossstone display plinth"
ped.data.materials.append(stone)
bev = ped.modifiers.new("Soft cut stone edges", "BEVEL")
bev.width = 0.075
bev.segments = 4
ped.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
for p in ped.data.polygons:
    p.use_smooth = True
torus("Pedestal gold inlay", (0, 0, -0.095), 0.84, 0.012, gold_light)
torus("Pedestal lower light channel", (0, 0, -0.235), 0.94, 0.012, cyan_glow)

# A few low moss-like forms around the base.
moss = set_principled(bpy.data.materials.new("Soft forest moss"), (0.018, 0.085, 0.045), roughness=0.94)
for i in range(17):
    a = i * math.tau / 17
    r = random.uniform(0.86, 1.12)
    ob = uv_sphere(f"Moss cushion {i+1}", (r * math.cos(a), r * math.sin(a), -0.085), (0.16, 0.12, 0.055), moss, 20, 12)
    ob.rotation_euler.z = a

# Ground and softly out-of-focus grove silhouettes.
ground = set_principled(bpy.data.materials.new("Midnight forest floor"), (0.008, 0.018, 0.027), metallic=0.12, roughness=0.36)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.32))
floor = bpy.context.object
floor.name = "Infinite midnight ground"
floor.data.materials.append(ground)

silhouette = set_principled(bpy.data.materials.new("Distant grove silhouettes"), (0.006, 0.028, 0.034), roughness=0.9)
for i in range(18):
    x = random.uniform(-8.0, 8.0)
    y = random.uniform(4.0, 9.0)
    h = random.uniform(4.0, 8.0)
    rad = random.uniform(0.13, 0.30)
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=rad, radius2=rad * 0.52, depth=h, location=(x, y, h / 2 - 0.3))
    tree = bpy.context.object
    tree.name = f"Background tree trunk {i+1}"
    tree.data.materials.append(silhouette)
    for j in range(3):
        canopy = uv_sphere(f"Background canopy {i+1}.{j+1}", (x + random.uniform(-0.6, 0.6), y, h * 0.62 + j * 0.45), (random.uniform(0.7, 1.2), 0.6, random.uniform(0.8, 1.4)), silhouette, 20, 12)

# Lighting: cool rim, warm wood key, and a strong local aura.
add_area("Warm key | reveals wood grain", (4, -5, 7), (0, 0, 2.6), 1050, (1.0, 0.69, 0.39), 4.0)
add_area("Cool rim | moonlight", (-4, 2, 6), (0, 0, 3.0), 1450, (0.20, 0.63, 1.0), 3.0)
add_area("Soft frontal fill", (-1, -5, 3), (0, 0, 2.6), 460, (0.42, 0.76, 0.78), 5.0)
add_area("Golden branch edge", (3, 1, 4.7), (0, 0, 4.2), 620, (1.0, 0.42, 0.12), 2.0)

bpy.ops.object.light_add(type="POINT", location=(0, -0.15, 5.02))
orb_light = bpy.context.object
orb_light.name = "Prismatic orb | animated radiance"
orb_light.data.energy = 45
orb_light.data.color = (0.18, 0.58, 1.0)
orb_light.data.shadow_soft_size = 1.05
for frame, energy, color in [
    (1, 35, (0.12, 0.52, 1.0)),
    (49, 48, (0.42, 0.18, 1.0)),
    (FPS * 4, 40, (0.12, 1.0, 0.62)),
    (145, 52, (1.0, 0.35, 0.12)),
    (LAST_FRAME, 35, (0.12, 0.52, 1.0)),
]:
    orb_light.data.energy = energy
    orb_light.data.color = color
    orb_light.data.keyframe_insert(data_path="energy", frame=frame)
    orb_light.data.keyframe_insert(data_path="color", frame=frame)

# Camera: gentle, continuous orbit around the artifact.
bpy.ops.object.empty_add(type="SPHERE", location=(0, 0, 2.70))
focus = bpy.context.object
focus.name = "Camera focus | Wildheart"
bpy.ops.object.camera_add(location=(7.4, -13.6, 6.1))
cam = bpy.context.object
cam.name = "11 | Cinematic orbit camera"
cam.data.lens = 46
cam.data.sensor_width = 36
cam.data.dof.use_dof = True
cam.data.dof.focus_object = focus
cam.data.dof.aperture_fstop = 5.6
aim(cam, focus.location)
scene.camera = cam
for frame, loc in [
    (1, (7.4, -13.6, 6.1)),
    (FPS * 4, (8.0, -13.0, 6.0)),
    (LAST_FRAME, (7.1, -13.7, 6.35)),
]:
    cam.location = loc
    aim(cam, focus.location)
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)
if cam.animation_data and cam.animation_data.action:
    for fc in cam.animation_data.action.fcurves:
        for key in fc.keyframe_points:
            key.interpolation = "BEZIER"
            key.handle_left_type = "AUTO"
            key.handle_right_type = "AUTO"

# A subtle camera-facing haze of light: composited glow on bright magical details.
scene.use_nodes = True
nodes = scene.node_tree.nodes
nodes.clear()
rl = nodes.new("CompositorNodeRLayers")
glare = nodes.new("CompositorNodeGlare")
glare.glare_type = "FOG_GLOW"
glare.quality = "HIGH"
glare.threshold = 1.35
glare.size = 8
comp = nodes.new("CompositorNodeComposite")
scene.node_tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
scene.node_tree.links.new(glare.outputs["Image"], comp.inputs["Image"])

# Output settings and final saved scene.
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_percentage = 100
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "wildheart_staff.blend"))

# First render a small contact sheet for visual quality inspection.
if PREVIEW_ONLY:
    scene.render.resolution_percentage = 25
    scene.eevee.taa_render_samples = 8
    check_dir = os.path.join(OUT, "check")
    os.makedirs(check_dir, exist_ok=True)
    for frame in (1, FPS * 4, LAST_FRAME):
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(check_dir, f"check_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
    print("PREVIEW_COMPLETE", flush=True)
    sys.exit(0)

# Deterministic full-resolution frame rendering: workflow encodes these to H.264 MP4.
for frame in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(frame)
    scene.render.filepath = os.path.join(FRAMES_DIR, f"frame_{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
    if frame % 24 == 0:
        print(f"PROGRESS: rendered {frame}/{scene.frame_end}", flush=True)

print("RENDER_COMPLETE", flush=True)

# Build trigger: render workflow should run on this commit.
