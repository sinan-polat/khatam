"""Photoreal product shots for KHATAM with Blender Cycles.

1. Export the live 3D models as GLB (see export.py: it mounts each product in the shop's three.js viewer
   and saves glb/<id>.glb with the gold layer as a texture).
2. Run:  python blender_render.py <glb-folder> <out-folder> [id ...]
Writes <id>.png (transparent, soft floor shadow) at 1800 x 1800.
"""
import sys, os, math
import bpy
from mathutils import Vector

GLB, OUT = sys.argv[1], sys.argv[2]
IDS = sys.argv[3:] or [f[:-4] for f in sorted(os.listdir(GLB)) if f.endswith('.glb')]
RES = int(os.environ.get('RES', 1800)); SAMPLES = int(os.environ.get('SAMPLES', 160))

# camera direction per product (from the object centre): x right, y back, z up
VIEW = {'bayt': (0.42, -1.0, 0.30), 'usra': (0.5, -1.0, 1.0), 'eidiyya': (0.5, -1.0, 0.75), 'mubarak': (0.45, -1.0, 0.38),
        'maktaba': (0.45, -1.0, 0.35), 'tabaq': (0.35, -1.0, 1.05), 'gaveaeske': (0.45, -1.0, 0.6)}

def hexlin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1]

def node(nt, kind, loc=(0, 0), **inp):
    n = nt.nodes.new(kind); n.location = loc
    for k, v in inp.items(): n.inputs[k].default_value = v
    return n

def pla(hexc):
    m = bpy.data.materials.new('pla_' + hexc); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = node(nt, 'ShaderNodeOutputMaterial', (600, 0))
    b = node(nt, 'ShaderNodeBsdfPrincipled', (300, 0), **{'Base Color': hexlin(hexc), 'Roughness': 0.52, 'Specular IOR Level': 0.45,
            'Sheen Weight': 0.0, 'Sheen Roughness': 0.6})
    # micro texture of printed PLA + rounded, catching edges (bevel normal)
    tc = node(nt, 'ShaderNodeTexCoord', (-700, 0))
    nz = node(nt, 'ShaderNodeTexNoise', (-500, 0), Scale=900.0, Detail=6.0, Roughness=0.6)
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    bev = node(nt, 'ShaderNodeBevel', (-300, -200), Radius=0.00045); bev.samples = 8
    bump = node(nt, 'ShaderNodeBump', (0, -100), Strength=0.035, Distance=0.0002)
    nt.links.new(nz.outputs['Fac'], bump.inputs['Height']); nt.links.new(bev.outputs['Normal'], bump.inputs['Normal'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    # slight roughness variation
    mr = node(nt, 'ShaderNodeMapRange', (0, 150), **{'To Min': 0.46, 'To Max': 0.6})
    nt.links.new(nz.outputs['Fac'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], b.inputs['Roughness'])
    nt.links.new(b.outputs['BSDF'], out.inputs['Surface']); return m

def gold_decal(img):
    m = bpy.data.materials.new('gold'); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = node(nt, 'ShaderNodeOutputMaterial', (800, 0))
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.location = (-600, 0); tex.image = img; tex.interpolation = 'Cubic'
    img.colorspace_settings.name = 'Non-Color'
    g = node(nt, 'ShaderNodeBsdfPrincipled', (200, 0), **{'Base Color': hexlin('d9a441'), 'Metallic': 1.0, 'Roughness': 0.22})
    # silk PLA: brushed, slightly uneven sheen
    tc = node(nt, 'ShaderNodeTexCoord', (-800, -300))
    nz = node(nt, 'ShaderNodeTexNoise', (-600, -300), Scale=600.0, Detail=4.0)
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    mr = node(nt, 'ShaderNodeMapRange', (-300, -300), **{'To Min': 0.16, 'To Max': 0.3})
    nt.links.new(nz.outputs['Fac'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], g.inputs['Roughness'])
    # raised gold: bump from the mask (softened)
    bump = node(nt, 'ShaderNodeBump', (-100, -150), Strength=0.6, Distance=0.0004)
    nt.links.new(tex.outputs['Color'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], g.inputs['Normal'])
    tr = node(nt, 'ShaderNodeBsdfTransparent', (200, 200))
    mx = node(nt, 'ShaderNodeMixShader', (500, 0))
    sep = node(nt, 'ShaderNodeSeparateColor', (-300, 100)); nt.links.new(tex.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Red'], mx.inputs['Fac']); nt.links.new(tr.outputs['BSDF'], mx.inputs[1]); nt.links.new(g.outputs['BSDF'], mx.inputs[2])
    nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
    m.blend_method = 'HASHED' if hasattr(m, 'blend_method') else None
    return m

def metal(hexc):
    m = bpy.data.materials.new('metal'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = hexlin(hexc); b.inputs['Metallic'].default_value = 1; b.inputs['Roughness'].default_value = 0.25
    return m

def area(name, loc, target, size, energy, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, 'AREA'); l.size = size; l.energy = energy; l.color = color
    o = bpy.data.objects.new(name, l); bpy.context.scene.collection.objects.link(o); o.location = loc
    d = Vector(target) - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); return o

def render(pid):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=os.path.join(GLB, pid + '.glb'))
    objs = [o for o in sc.objects if o.type == 'MESH']
    # three.js units are mm -> metres
    root = [o for o in sc.objects if o.parent is None]
    for o in root: o.scale = [s * 0.001 for s in o.scale]; o.location = [v * 0.001 for v in o.location]
    bpy.context.view_layer.update()
    cache = {}
    for o in objs:
        for slot in o.material_slots:
            mt = slot.material; n = mt.name if mt else ''
            if n.startswith('GOLDDECAL'):
                img = next(nd.image for nd in mt.node_tree.nodes if nd.type == 'TEX_IMAGE'); slot.material = gold_decal(img)
            elif n.startswith('METAL_'):
                slot.material = cache.setdefault(n, metal(n[7:13]))
            elif n.startswith('PLA_'):
                slot.material = cache.setdefault(n, pla(n[5:11]))
        print('MAT', o.name, [s.material.name for s in o.material_slots])
        for p in o.data.polygons: p.use_smooth = False
    # bounds
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (lo + hi) / 2; r = (hi - lo).length / 2; print('R', r)
    # floor = shadow catcher
    bpy.ops.mesh.primitive_plane_add(size=r * 30, location=(c.x, c.y, lo.z))
    fl = bpy.context.active_object; fl.is_shadow_catcher = True
    # camera
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 85
    d = Vector(VIEW.get(pid, (0.5, -1, 0.45))).normalized()
    fov = 2 * math.atan(cam.data.sensor_width / 2 / cam.data.lens)
    dist = r / math.sin(fov / 2) * 1.08
    cam.location = c + d * dist; cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start = dist / 100; cam.data.clip_end = dist * 10
    # studio light: big soft key top-left, warm rim from behind, cool low fill, soft overhead
    k = r * 1.0
    area('key', c + Vector((-2.2, -1.6, 2.6)) * r * 2.2, c, r * 3.2, 900 * k * k * 0.9, (1, 0.96, 0.9))
    area('rim', c + Vector((2.4, 2.2, 1.6)) * r * 2.2, c, r * 2.0, 650 * k * k * 0.9, (1, 0.9, 0.75))
    area('fill', c + Vector((2.6, -1.8, 0.6)) * r * 2.2, c, r * 3.0, 220 * k * k * 0.9, (0.9, 0.94, 1))
    area('top', c + Vector((0, 0, 3.2)) * r * 2.2, c, r * 4.0, 250 * k * k * 0.9)
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Strength'].default_value = 0.9
    # studio environment: bright soft top, dark floor, a warm band — gives metal real reflections to show
    wt = w.node_tree; tc = wt.nodes.new('ShaderNodeTexCoord'); sp = wt.nodes.new('ShaderNodeSeparateXYZ'); ramp = wt.nodes.new('ShaderNodeValToRGB')
    wt.links.new(tc.outputs['Generated'], sp.inputs['Vector']); wt.links.new(sp.outputs['Z'], ramp.inputs['Fac'])
    el = ramp.color_ramp.elements; el[0].position = 0.42; el[0].color = (0.015, 0.013, 0.012, 1); el[1].position = 0.75; el[1].color = (1.0, 0.95, 0.88, 1)
    mid = el.new(0.53); mid.color = (0.35, 0.28, 0.2, 1)
    wt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    # render settings
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
    sc.cycles.use_adaptive_sampling = True; sc.cycles.max_bounces = 8; sc.cycles.transparent_max_bounces = 16
    sc.render.film_transparent = True; sc.render.resolution_x = sc.render.resolution_y = RES
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = -0.1
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.render.filepath = os.path.join(OUT, pid + '.png')
    bpy.ops.render.render(write_still=True)
    print('rendered', pid)

os.makedirs(OUT, exist_ok=True)
for pid in IDS: render(pid)
