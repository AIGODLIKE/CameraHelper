import numpy as np
from mathutils.geometry import interpolate_bezier

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


def beziers_from_spline(spline, mat):
    spline_beziers = []

    pt_count = len(spline.bezier_points)
    for i in range(pt_count if spline.use_cyclic_u else pt_count - 1):
        bezier_points = [mat @ spline.bezier_points[i].co,
                         mat @ spline.bezier_points[i].handle_right,
                         mat @ spline.bezier_points[i - pt_count + 1].handle_left,
                         mat @ spline.bezier_points[i - pt_count + 1].co
                         ]

        spline_beziers.append(CubicBezier(bezier_points))
    return spline_beziers


def sample_spline_split(spline_beziers, samples=12):
    """对曲线点进行采样，返回采样点"""
    pts = []
    i = 0
    while i < 1:
        i += 1 / samples
        split = spline_beziers.split(i)
        pts.append(split[3])  # 2,4 handle left/right, 3 middle

    return pts
