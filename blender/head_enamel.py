"""Directional relief for the white ceramic feathers, shared by Cycles and glTF."""
from math import pi
from zlib import crc32

import bpy
import numpy as np


TILE_WIDTH, TILE_HEIGHT, GUTTER = 512, 256, 6


def smoothstep(lo, hi, x):
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def feather_tile(variant):
    """Return colour, tangent normal and packed material channels for one stamp."""
    rng = np.random.default_rng(74213 + 3511 * variant)
    width, height = TILE_WIDTH - 2 * GUTTER, TILE_HEIGHT - 2 * GUTTER
    y, x = np.mgrid[:height, :width]
    station = (x + .5) / width
    # PNG scanlines start at the top. Tangent +V points towards the first row.
    cross = 1 - 2 * (y + .5) / height
    side_bias = (-.7, .45, .85, -.30)[variant]
    axis = side_bias * .018 * np.sin(pi * station) * np.sin(1.25 * pi * station + .3)
    d = abs(cross - axis)

    def filtered_noise(x_radius, y_radius):
        samples = rng.normal(0, 1, (height, width))
        fx = np.fft.fftfreq(width)[None, :] * x_radius
        fy = np.fft.fftfreq(height)[:, None] * y_radius
        field = np.fft.ifft2(np.fft.fft2(samples) * np.exp(-2 * pi**2 * (fx**2 + fy**2))).real
        return field / max(field.std(), 1e-8)

    glaze = filtered_noise(23, 15)
    polish = filtered_noise(19, .9)
    channels, shoulders, fine = (np.zeros_like(station) for _ in range(3))
    for sign in (-1, 1):
        distance = sign * (cross - axis)
        # Adjacent barbs share the outward sweep but vary in length and spacing.
        count = (13, 10, 12, 14)[variant] + int(sign > 0)
        starts = np.linspace(-.16, .91, count) + rng.uniform(-.018, .018, count)
        for i, start in enumerate(starts):
            extent = rng.uniform(.68, 1.02)
            onset = rng.uniform(.024, .13)
            sweep = rng.uniform(.115, .192) + .030 * (1 - start)
            path = start + sweep * np.maximum(distance, 0)**.76 + .044 * distance**2
            profile = station - path
            strength = rng.uniform(.57, .97) * (.76 if i % 4 == 0 else 1)
            reach = smoothstep(onset, onset + .09, distance) * (1 - smoothstep(extent - .16, extent, distance))
            reach *= (1 - .64 * smoothstep(.83, 1, station)) * strength
            gauge = rng.uniform(.0044, .0074) * (1 - .24 * np.clip(distance, 0, 1))
            channels = np.maximum(channels, reach * np.exp(-(profile / gauge)**2))
            shoulders = np.maximum(shoulders, reach * np.exp(-((profile + 1.6 * gauge) / (.012 + gauge))**2))
            fine_reach = reach * smoothstep(.065, .31, distance)
            fine = np.maximum(fine, fine_reach * np.exp(-((profile - .021 - .013 * distance) / .0031)**2))
            # Some barb tips split into a shorter, finer etch towards the outer margin.
            if i % 3 != 1:
                split = profile - .031 - .035 * distance**2
                split_reach = fine_reach * smoothstep(.25, .60, distance)
                fine = np.maximum(fine, .66 * split_reach * np.exp(-(split / .0028)**2))

    taper = 1 - smoothstep(.84, 1.03, station)
    shaft_width = .040 - .020 * station
    shaft = np.exp(-(d / shaft_width)**2) * taper
    shaft_bevel = np.exp(-((d - 1.38 * shaft_width) / (.019 - .006 * station))**2) * taper
    lip = np.exp(-((1 - d) / .031)**2) * np.clip(.56 + .18 * glaze, .14, .85)
    root = (1 - smoothstep(.01, .46, station)) * (.3 + .7 * d)
    wear = lip * (.46 + .54 * smoothstep(.28, .85, station))
    # Small, irregular tooling nicks are confined to the rolled trailing hems.
    nicks = np.zeros_like(station)
    for sign in (-1, 1):
        depth = 1 - sign * (cross - axis)
        for anchor in rng.uniform(.48, .97, 4):
            span = rng.uniform(.06, .18)
            cut = station - anchor + rng.uniform(.16, .36) * depth
            end = 1 - smoothstep(.015, span, depth)
            nicks = np.maximum(nicks, end * np.exp(-(cut / .0027)**2))
    wear = np.maximum(wear, .63 * nicks)
    # Wide shallow facets survive minification. Fine cuts resolve at close range.
    relief = .76 * shaft - .30 * shaft_bevel + .40 * shoulders - .67 * channels - .22 * fine
    relief += .026 * polish + .035 * glaze - .20 * lip - .19 * nicks
    dy, dx = np.gradient(relief)
    normal = np.stack((-4.2 * dx, 2.7 * dy, np.ones_like(dx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    normal = (.5 + .5 * normal) * 255

    field = .013 * glaze + .006 * polish + .025 * (1 - d) - .055 * root
    field += .060 * shaft - .146 * shaft_bevel + .055 * shoulders - .203 * channels - .104 * fine
    stock = np.array(((232, 227, 216), (227, 224, 217), (235, 230, 220), (217, 211, 199))[variant])
    color = stock * (1 + field[..., None])
    color += (np.array((161, 153, 136)) - color) * (.47 * wear)[..., None]
    rough = np.clip(.294 + .025 * glaze + .015 * polish + .105 * channels + .055 * root
                    - .074 * shaft - .047 * shoulders - .097 * wear, .155, .50)
    metal = np.clip(.215 + .035 * shoulders + .26 * wear, 0, 1)
    orm = np.stack((np.ones_like(rough), rough, metal), axis=-1) * 255
    return [np.pad(a, ((GUTTER, GUTTER), (GUTTER, GUTTER), (0, 0)), mode='edge')
            for a in (color, normal, orm)]


def add_material(mats, image):
    tiles = [feather_tile(i) for i in range(4)]
    def atlas(channel):
        upper = np.concatenate([tiles[i][channel] for i in (2, 3)], axis=1)
        lower = np.concatenate([tiles[i][channel] for i in (0, 1)], axis=1)
        return np.concatenate((upper, lower))

    material = bpy.data.materials.new('Pearl enamel · engraved head plumage')
    material['stock'] = 'head_enamel'
    material.use_nodes = True
    material.diffuse_color = (.81, .77, .69, 1)
    material.metallic, material.roughness = .215, .294
    tree = material.node_tree
    shader = tree.nodes.get('Principled BSDF')
    def texture(name, channel, color_space, location):
        sampler = tree.nodes.new('ShaderNodeTexImage')
        sampler.image = image('head-plumage-' + name, atlas(channel), color_space)
        sampler.extension = 'EXTEND'
        sampler.label = name
        sampler.location = location
        return sampler.outputs['Color']
    tree.links.new(texture('ivory', 0, 'sRGB', (-700, 300)), shader.inputs['Base Color'])
    normal_map = tree.nodes.new('ShaderNodeNormalMap')
    normal_map.inputs['Strength'].default_value = .84
    normal_map.location = (-320, -280)
    tree.links.new(texture('relief', 1, 'Non-Color', (-700, -300)), normal_map.inputs['Color'])
    tree.links.new(normal_map.outputs['Normal'], shader.inputs['Normal'])
    split = tree.nodes.new('ShaderNodeSeparateColor')
    split.location = (-320, 0)
    tree.links.new(texture('satin', 2, 'Non-Color', (-700, 0)), split.inputs['Color'])
    tree.links.new(split.outputs['Green'], shader.inputs['Roughness'])
    tree.links.new(split.outputs['Blue'], shader.inputs['Metallic'])
    shader.inputs['Coat Weight'].default_value = .34
    shader.inputs['Coat Roughness'].default_value = .175
    mats['head_enamel'] = material


def map_plate(obj, coordinates, shadow_ivory=False):
    """Map all faces of a rigid part into a single inset atlas cell in bind space."""
    seed = crc32(obj.name.encode('utf-8'))
    # Reserve the warmer fourth stock for the lower shadow feathers.
    cell = 3 if shadow_ivory else seed % 3
    flip = bool(seed & 8)
    warp = ((seed >> 5) % 17 - 8) * .006
    du, dv = GUTTER / TILE_WIDTH, GUTTER / TILE_HEIGHT
    mapped = []
    for u, v in coordinates:
        u = u + warp * u * (1 - u)
        v = 1 - v if flip else v
        mapped.append(((cell % 2 + du + u * (1 - 2 * du)) / 2,
                       (cell // 2 + dv + v * (1 - 2 * dv)) / 2))
    layer = obj.data.uv_layers.active.data
    for loop in obj.data.loops:
        layer[loop.index].uv = mapped[loop.vertex_index]
