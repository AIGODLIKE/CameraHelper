import bpy
import bgl
import gpu
import math
import mathutils
import ast

from bpy_extras.view3d_utils import location_3d_to_region_2d
from gpu_extras.batch import batch_for_shader

import numpy as np

shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')


class CubicBezier(object):
    def __init__(self, points):
        self.points = np.array(points).astype(np.float32)

    def at(self, t):
        pt = 1 * (1 - t) ** 3 * self.points[0]
        pt += 3 * t ** 1 * (1 - t) ** 2 * self.points[1]
        pt += 3 * t ** 2 * (1 - t) ** 1 * self.points[2]
        pt += 1 * t ** 3 * self.points[3]
        return pt

    def split(self, t):
        p1, p2, p3, p4 = self.points

        p12 = (p2 - p1) * t + p1
        p23 = (p3 - p2) * t + p2
        p34 = (p4 - p3) * t + p3
        p123 = (p23 - p12) * t + p12
        p234 = (p34 - p23) * t + p23
        p1234 = (p234 - p123) * t + p123

        return [p1, p12, p123, p1234, p234, p34, p4]


def bezier_from_spline(spline, matrix):
    spline_beziers = []

    pt_count = len(spline.bezier_points)
    for i in range(pt_count if spline.use_cyclic_u else pt_count - 1):
        bezier_points = [matrix @ spline.bezier_points[i].co,
                         matrix @ spline.bezier_points[i].handle_right,
                         matrix @ spline.bezier_points[i - pt_count + 1].handle_left,
                         matrix @ spline.bezier_points[i - pt_count + 1].co
                         ]

        spline_beziers.append(CubicBezier(bezier_points))

    return spline_beziers


class CameraMotionPath():

    def __init__(self, context):
        pass

    def __call__(self, context):
        self.draw(context)

    def draw(self, context):
        self.draw_callback_bezier_3d(context)

    def draw_callback_bezier_3d(self, context):
        self.motion_path = context.object.motion_cam.path
        if self.motion_path is None: return
        if context.object.motion_cam.path_points == '': return

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glEnable(bgl.GL_DEPTH_TEST)

        points = context.object.motion_cam.path_points.split('$')
        pts = [eval(p) for p in points]

        bgl.glLineWidth(3)
        shader.bind()
        shader.uniform_float("color", (1, 0, 0, 0.5))
        batch = batch_for_shader(shader, 'LINES', {"pos": pts})
        batch.draw(shader)

        # restore opengl defaults
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_BLEND)
        bgl.glDisable(bgl.GL_LINE_SMOOTH)
        bgl.glEnable(bgl.GL_DEPTH_TEST)
