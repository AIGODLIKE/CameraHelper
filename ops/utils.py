import bpy
import bmesh
from pathlib import Path

from ..prefs.get_pref import get_pref

# 用于处理曲线的几何节点组 -----------------------------------------------------
C_GET_CURVE_ATTR = 'get_curve_attr'
C_GET_CURVE_EVAL_POS = 'get_curve_eval_pos'


# -----------------------------------------------------------------------------


def meas_time(func):
    """计时装饰器

    :param func:
    :return: func
    """

    def wrapper(*args, **kwargs):
        import time
        t = time.time()
        func(*args, **kwargs)
        end = time.time()
        # print(f'函数 "{func.__name__}" 花费 {(end - t) * 1000}ms')

    return wrapper


def get_geo_node_file(filename='process.blend') -> Path:
    """几何节点组的文件路径

    :param filename:
    :return:
    """
    return Path(__file__).parent.joinpath('nodes', filename)


def get_mesh_obj_coords(context, obj, deps=None) -> list:
    """获取mesh对象的位置

    :param obj:bpy.types.Object
    :return:list
    """
    depsg_eval = deps if deps else context.evaluated_depsgraph_get()  # deps 由外部传入，防止冻结

    obj_eval = obj.evaluated_get(depsg_eval)
    return [v.co for v in obj_eval.data.vertices]


def get_mesh_obj_attrs(context, obj, deps=None) -> dict:
    """获取mesh对象的属性值

    :param obj:bpy.types.Object
    :param attr:
    :return:list
    """
    attr_dict = dict()

    depsg_eval = deps if deps else context.evaluated_depsgraph_get()  # deps 由外部传入，防止冻结
    depsg_eval.update()
    obj_eval = obj.evaluated_get(depsg_eval)

    for name, attr in obj_eval.data.attributes.items():
        attr_data = attr.data
        try:
            attr_dict[name] = [v.value for v in attr_data.values()]
        except:
            attr_dict[name] = [v.vector for v in attr_data.values()]

    # print(attr_dict)

    return attr_dict



def view3d_find():
    # returns first 3d view, normally we get from context
    for area in bpy.context.window.screen.areas:
        if area.type == 'VIEW_3D':
            v3d = area.spaces[0]
            rv3d = v3d.region_3d
            for region in area.regions:
                if region.type == 'WINDOW':
                    return region, rv3d
    return None, None

def view3d_camera_border(scene,region,rv3d):
    obj = scene.camera
    cam = obj.data

    frame = cam.view_frame(scene=scene)

    # move from object-space into world-space
    frame = [obj.matrix_world @ v for v in frame]

    # move into pixelspace
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    frame_px = [location_3d_to_region_2d(region, rv3d, v) for v in frame]
    return frame_px



class Cam():
    """
    相机实用类
    """

    def __init__(self, cam):
        self.cam = cam
        self.startLocation = cam.location.copy()
        self.startAngle = cam.data.angle

    def restore(self):
        self.cam.location = self.startLocation.copy()
        self.cam.data.angle = self.startAngle

    def limit_angle_range(self, value):
        max_view_radian = 3.0  # 172d
        min_view_radian = 0.007  # 0.367d
        self.cam.data.angle = max(min(self.cam.data.angle + value, max_view_radian), min_view_radian)

    def get_angle(self):
        return self.cam.data.angle

    def offsetLocation(self, localCorrectionVector):
        self.cam.location = self.cam.location + (localCorrectionVector @ self.cam.matrix_world.inverted())

    def get_local_point(self, point):
        return self.cam.matrix_world.inverted() @ point


# 以下所有方法都会出发depsgraph更新，无法用于实时动画set/get
###############################################################################

def get_geo_node_group(filename='process.blend', node_group=C_GET_CURVE_ATTR):
    """获取几何节点组

    :param filename:
    :param node_group:name of node group
    :return: bpy.types.NodeGroup
    """
    fp = get_geo_node_file(filename)
    if node_group in bpy.data.node_groups:  # 版本控制:将会重新曲线按钮用于更新节点版本
        return bpy.data.node_groups[node_group]

    with bpy.data.libraries.load(str(fp), link=False) as (data_from, data_to):
        data_to.node_groups = [node_group]

    ng = data_to.node_groups[0]

    return ng

def create_tool_collection(name = 'CameraHelper'):
    if name not in bpy.data.collections:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    coll = bpy.data.collections['CameraHelper']
    coll.hide_viewport = False
    coll.hide_render = False

    return coll

def gen_bezier_curve_from_points(coords: list, curve_name, resolution_u=12, close_spline=False, type='SMOOTH'):
    """根据点集生成贝塞尔曲线

    :param coords:list of tuple(x, y, z)
    :param curve_name: 曲线物体/数据名字
    :param resolution_u: 曲线分割精度
    :param close_spline: 是否闭合曲线
    :return:曲线物体 bpy.types.Object
    """
    # 清理
    if curve_name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[curve_name])

    if curve_name in bpy.data.curves:
        bpy.data.curves.remove(bpy.data.curves[curve_name])

    # 创建曲线
    curve_data = bpy.data.curves.new(curve_name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = resolution_u
    # 创建样条
    # 创建点
    if type == 'SMOOTH':
        spline = curve_data.splines.new('BEZIER')
        spline.bezier_points.add(len(coords) - 1)
    else:
        spline = curve_data.splines.new('POLY')
        spline.points.add(len(coords) - 1)
    # 设置点
    for i, coord in enumerate(coords):
        x, y, z = coord
        if type == 'SMOOTH':
            spline.bezier_points[i].handle_right_type = 'AUTO'
            spline.bezier_points[i].handle_left_type = 'AUTO'
            spline.bezier_points[i].co = (x, y, z)
            spline.bezier_points[i].handle_left = (x, y, z)
            spline.bezier_points[i].handle_right = (x, y, z)
        else:
            spline.points[i].co = (x, y, z, 1)

    # 闭合，或为可选项
    spline.use_cyclic_u = close_spline

    if type == 'SMOOTH':
        # 取消端点影响a
        def map_handle_to_co(pt):
            pt.handle_right_type = 'FREE'
            pt.handle_left_type = 'FREE'
            pt.handle_left = pt.co
            pt.handle_right = pt.co

        map_handle_to_co(spline.bezier_points[0])
        map_handle_to_co(spline.bezier_points[-1])

    # 创建物体
    curve_obj = bpy.data.objects.new(curve_name, curve_data)
    # 链接到场景(否则物体将不会更新)
    # coll = bpy.context.collection
    coll = create_tool_collection()
    coll.objects.link(curve_obj)

    return curve_obj


def set_obj_geo_mod(obj, name='Geo Node', node_group=None):
    """添加几何模型修饰器

    :param obj:bpy.types.Object
    """
    mod = obj.modifiers.new(type='NODES', name=name)
    if mod.node_group:
        bpy.data.node_groups.remove(mod.node_group)
    mod.node_group = node_group

    return mod


def gen_curve_sample_obj(curve_obj, postfix='_sample', node_group=C_GET_CURVE_ATTR):
    """根据曲线物体生属性采样用物体

    :param curve_obj:
    :return:
    """
    tmp_name = curve_obj.name + postfix

    if tmp_name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[tmp_name])
    if tmp_name in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes[tmp_name])

    # 创建mesh
    tmp_mesh = bpy.data.meshes.new(tmp_name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=2, v_segments=1, radius=0.5, calc_uvs=True)
    bm.to_mesh(tmp_mesh)
    bm.free()
    # 创建物体并使用节点修改器
    tmp_obj = bpy.data.objects.new(tmp_name, tmp_mesh)

    ng = get_geo_node_group(node_group=node_group)
    mod = set_obj_geo_mod(tmp_obj, node_group=ng)
    # 设置输入物体
    mod["Input_2"] = curve_obj

    # coll = bpy.context.collection
    coll = create_tool_collection()
    coll.objects.link(tmp_obj)

    return tmp_obj


##############################################################################################

# 集成方法 ---------------------------------------------------------------------------------------------------------

def gen_sample_attr_obj(curve_obj):
    return gen_curve_sample_obj(curve_obj, postfix='_attr', node_group=C_GET_CURVE_ATTR)


def gen_sample_mesh_obj(curve_obj):
    return gen_curve_sample_obj(curve_obj, postfix='_mesh', node_group=C_GET_CURVE_EVAL_POS)

# --------------------------------------------------------------------------------------------------------------------
