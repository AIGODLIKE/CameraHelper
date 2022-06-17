import bpy
from bpy.types import PropertyGroup, Operator, Panel, UIList
from bpy.props import CollectionProperty, PointerProperty, FloatProperty, IntProperty, StringProperty, BoolProperty
from pathlib import Path


def get_active_motion_item(obj):
    """

    :param obj: bpy.types.Object
    :return: bpy.types.Object.motion_cam.list.item / NONE
    """
    if len(obj.motion_cam.list) > 0:
        return obj.motion_cam.list[obj.motion_cam.list_index]


# 用于过滤用户选项，相机或者普通物体
def poll_camera(self, obj):
    if obj != self.id_data:
        return obj.type == 'CAMERA' if self.filter_camera else True


def interpolate_cam(tg_obj, from_obj, to_obj, fac):
    influence = fac

    use_euler = tg_obj.motion_cam.use_euler
    use_lens = tg_obj.motion_cam.use_lens

    # 限定变化
    if use_euler:
        from_quart = from_obj.matrix_world.to_quaternion().copy()
        to_quart = to_obj.matrix_world.to_quaternion().copy()
        tg_quart = from_quart.slerp(to_quart, influence)
        tg_obj.rotation_euler = tg_quart.to_euler()

    if from_obj.type == to_obj.type == 'CAMERA' and use_lens:
        tg_lens = (1 - influence) * from_obj.data.lens + influence * to_obj.data.lens
        tg_obj.data.lens = tg_lens


def curve_bezier_from_points(coords: list, curve_name, close_spline=False):
    """

    :param coords: 一系列点的位置
    :param curve_name: 曲线名
    :param close_spline: 循环曲线
    :return:
    """
    curve_obj = None
    if curve_name in bpy.data.objects:
        curve_obj = bpy.data.objects[curve_name]

    if curve_name in bpy.data.curves:
        bpy.data.curves.remove(bpy.data.curves[curve_name])

    curve_data = bpy.data.curves.new(curve_name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 12

    # map coords to spline
    spline = curve_data.splines.new('BEZIER')
    spline.bezier_points.add(len(coords) - 1)

    for i, coord in enumerate(coords):
        x, y, z = coord
        spline.bezier_points[i].handle_right_type = 'AUTO'
        spline.bezier_points[i].handle_left_type = 'AUTO'

        spline.bezier_points[i].co = (x, y, z)
        spline.bezier_points[i].handle_left = (x, y, z)
        spline.bezier_points[i].handle_right = (x, y, z)

    spline.use_cyclic_u = close_spline
    # 取消端点影响
    pt_s = spline.bezier_points[0]
    pt_s.handle_right_type = 'FREE'
    pt_s.handle_left_type = 'FREE'
    pt_s.handle_left = pt_s.co
    pt_s.handle_right = pt_s.co

    pt_s = spline.bezier_points[-1]
    pt_s.handle_right_type = 'FREE'
    pt_s.handle_left_type = 'FREE'
    pt_s.handle_left = pt_s.co
    pt_s.handle_right = pt_s.co

    # 创建物体
    if curve_obj:
        bpy.data.objects.remove(curve_obj)

    curve_obj = bpy.data.objects.new(curve_name, curve_data)

    coll = bpy.context.collection
    coll.objects.link(curve_obj)

    return curve_obj


def get_curve_pt_fac(curve):
    """

    :param curve: bpy.types.Object
    :return:
    """

    # 添加几何节点以获取控制点的fac
    mod = curve.modifiers.new(type='NODES', name='tmp')
    if mod.node_group:
        bpy.data.node_groups.remove(mod.node_group)

    # 导入节点预设
    f = Path(__file__).parent.joinpath('nodes', 'process.blend')
    with bpy.data.libraries.load(str(f), link=False) as (data_from, data_to):
        data_to.node_groups = ['get_fac']

    ng = data_to.node_groups[0]
    mod.node_group = ng
    mod["Output_2_attribute_name"] = 'fac'
    curve.update_tag()

    deg = bpy.context.evaluated_depsgraph_get()

    me = bpy.data.meshes.new_from_object(curve.evaluated_get(deg), depsgraph=deg)
    res = tuple(pt.value for pt in me.attributes['fac'].data)
    # clear
    curve.modifiers.remove(curve.modifiers[0])
    bpy.data.node_groups.remove(ng)
    bpy.data.meshes.remove(me)

    return res


def gen_cam_path(self, context):
    obj = self.id_data
    cam_list = list()
    for item in obj.motion_cam.list:
        if item.camera is None: return
        cam_list.append(item.camera)

    cam_pts = [cam.matrix_world.to_translation() for cam in cam_list]
    path = curve_bezier_from_points(cam_pts, obj.name + '-MotionPath')
    pts_fac = get_curve_pt_fac(path)

    for i, fac in enumerate(pts_fac):
        obj.motion_cam.list[i].fac = fac

    # bind
    obj.motion_cam.path = path
    #
    if 'Motion Camera' in obj.constraints:
        const = obj.constraints['Motion Camera']
    else:
        const = obj.constraints.new('FOLLOW_PATH')
        const.name = 'Motion Camera'

    const.use_fixed_location = True
    const.target = path

    d = const.driver_add('offset_factor')
    d.driver.type = 'AVERAGE'

    var1 = d.driver.variables.new()
    var1.targets[0].id = obj
    var1.targets[0].data_path = 'motion_cam.offset_factor'


class MotionCamItemProps(PropertyGroup):
    # 只选择相机
    filter_camera: BoolProperty(name='Filter Camera', default=True)
    camera: PointerProperty(name='Camera', type=bpy.types.Object, poll=poll_camera, update=gen_cam_path)
    fac: FloatProperty(name='Factor', min=0, max=1)


def get_offset_factor(self):
    return self.get('offset_factor', 0.0)


def set_offset_factor(self, value):
    self['offset_factor'] = value

    if 'Motion Camera' not in self.id_data.constraints: return

    obj = self.id_data
    # obj.constraints['Motion Camera'].offset_factor = value

    for i, item in enumerate(obj.motion_cam.list):
        item_next = obj.motion_cam.list[i + 1] if i < len(obj.motion_cam.list) - 1 else None
        item_pre = obj.motion_cam.list[i - 1] if i > 0 else None
        fac = item.fac

        if item_next:
            from_obj = item.camera
            to_obj = item_next.camera

            if fac <= value < item_next.fac:
                true_fac = (value - fac) / (item_next.fac - fac)

                interpolate_cam(obj, from_obj, to_obj, true_fac)
                break
        else:
            from_obj = item_pre.camera
            to_obj = item.camera

            if item_pre.fac <= value < fac:
                true_fac = (value - item_pre.fac) / (fac - item_pre.fac)
            else:
                true_fac = 1

            interpolate_cam(obj, from_obj, to_obj, true_fac)
            break


class MotionCamListProp(PropertyGroup):
    # 约束列表
    list: CollectionProperty(name='List', type=MotionCamItemProps)
    list_index: IntProperty(name='List', min=0, default=0)

    #
    path: PointerProperty(type=bpy.types.Object)
    offset_factor: FloatProperty(name='Offset Factor', min=0, max=1,
                                 set=set_offset_factor,
                                 get=get_offset_factor)

    # 限定
    use_euler: BoolProperty(name='Rotate', default=True)
    use_lens: BoolProperty(name='Lens', default=True)


class CAMHP_UL_CameraList(UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=False)
        row.use_property_decorate = False

        row.prop(item, 'camera')


class ListAction:
    """Add / Remove / Copy current config"""
    bl_options = {'INTERNAL', 'UNDO'}

    index: IntProperty()
    action = None

    def execute(self, context):
        m_cam = context.object.motion_cam

        if self.action == 'ADD':
            new_item = m_cam.list.add()
            new_item.name = f'Motion{len(m_cam.list)}'
            new_item.influence = 0.5
            # correct index
            old_index = m_cam.list_index
            new_index = len(m_cam.list) - 1
            m_cam.list_index = new_index

            for i in range(old_index, new_index - 1):
                bpy.ops.camhp.move_up_motion_cam()

        elif self.action == 'REMOVE':
            m_cam.list.remove(self.index)
            m_cam.list_index = self.index - 1 if self.index != 0 else 0

        elif self.action == 'COPY':
            src_item = m_cam.list[self.index]

            new_item = m_cam.list.add()

            for key in src_item.__annotations__.keys():
                value = getattr(src_item, key)
                setattr(new_item, key, value)

            old_index = m_cam.list_index
            new_index = len(m_cam.list) - 1
            m_cam.list_index = len(m_cam.list) - 1

            for i in range(old_index, new_index - 1):
                bpy.ops.camhp.move_up_motion_cam()

        return {'FINISHED'}


class ListMove:
    bl_options = {'INTERNAL', 'UNDO'}

    index: IntProperty()
    action = None

    def execute(self, context):
        m_cam = context.object.motion_cam

        my_list = m_cam.list
        index = m_cam.list_index
        neighbor = index + (-1 if self.action == 'UP' else 1)
        my_list.move(neighbor, index)
        self.move_index(context)

        return {'FINISHED'}

    def move_index(self, context):
        m_cam = context.object.motion_cam
        index = m_cam.list_index
        new_index = index + (-1 if self.action == 'UP' else 1)
        m_cam.list_index = max(0, min(new_index, len(m_cam.list) - 1))


class CAMHP_OT_add_motion_cam(ListAction, Operator):
    """"""
    bl_idname = 'camhp.add_motion_cam'
    bl_label = 'Add'

    action = 'ADD'


class CAMHP_OT_remove_motion_cam(ListAction, Operator):
    """"""
    bl_idname = 'camhp.remove_motion_cam'
    bl_label = 'Remove'

    action = 'REMOVE'


class CAMHP_OT_copy_motion_cam(ListAction, Operator):
    """"""
    bl_idname = 'camhp.copy_motion_cam'
    bl_label = 'Copy'

    action = 'COPY'


class CAMHP_OT_move_up_motion_cam(ListMove, Operator):
    """"""
    bl_idname = 'camhp.move_up_motion_cam'
    bl_label = 'Move Up'

    action = 'UP'


class CAMHP_OT_move_down_motion_cam(ListMove, Operator):
    """"""
    bl_idname = 'camhp.move_down_motion_cam'
    bl_label = 'Move Down'

    action = 'DOWN'


class CAMHP_PT_MotionCamPanel(Panel):
    bl_label = 'Motion Camera'
    bl_space_type = 'PROPERTIES'
    bl_idname = 'CAMHP_PT_MotionCamPanel'
    bl_context = "object"
    bl_region_type = 'WINDOW'

    @classmethod
    def poll(self, context):
        return context.object and context.object.type in {'EMPTY', 'CAMERA'}

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        # layout.use_property_decorate = False
        layout.label(text=context.object.name, icon=context.object.type + '_DATA')

        row = layout.row(align=True)

        col = row.column(align=1)
        col.template_list(
            "CAMHP_UL_CameraList", "The list",
            context.object.motion_cam, "list",
            context.object.motion_cam, "list_index", )

        col_btn = row.column(align=1)

        col_btn.operator('camhp.add_motion_cam', text='', icon='ADD')

        d = col_btn.operator('camhp.remove_motion_cam', text='', icon='REMOVE')
        d.index = context.object.motion_cam.list_index

        col_btn.separator()

        col_btn.operator('camhp.move_up_motion_cam', text='', icon='TRIA_UP')
        col_btn.operator('camhp.move_down_motion_cam', text='', icon='TRIA_DOWN')

        col_btn.separator()

        c = col_btn.operator('camhp.copy_motion_cam', text='', icon='DUPLICATE')
        c.index = context.object.motion_cam.list_index

        # m_cam = get_active_motion_item(context.object)
        #
        # layout.prop(m_cam, 'camera')

        col.prop(context.object.motion_cam, 'offset_factor', slider=True)

        # col.prop(m_cam, 'use_loc')
        # col.prop(m_cam, 'use_euler')
        # col.prop(m_cam, 'use_lens')


def draw_context(self, context):
    if context.object and context.object.type in {'CAMERA', 'EMPTY'}:
        layout = self.layout
        layout.separator()
        op = layout.operator('wm.call_panel', text='Motion Camera')
        op.name = 'CAMHP_PT_MotionCamPanel'
        op.keep_open = True
        layout.separator()


def register():
    bpy.utils.register_class(MotionCamItemProps)
    bpy.utils.register_class(MotionCamListProp)
    bpy.types.Object.motion_cam = PointerProperty(type=MotionCamListProp)
    # list action
    bpy.utils.register_class(CAMHP_OT_add_motion_cam)
    bpy.utils.register_class(CAMHP_OT_remove_motion_cam)
    bpy.utils.register_class(CAMHP_OT_copy_motion_cam)
    bpy.utils.register_class(CAMHP_OT_move_up_motion_cam)
    bpy.utils.register_class(CAMHP_OT_move_down_motion_cam)

    # UI
    bpy.utils.register_class(CAMHP_UL_CameraList)
    bpy.utils.register_class(CAMHP_PT_MotionCamPanel)
    # bpy.types.VIEW3D_MT_object_context_menu.append(draw_context)


def unregister():
    del bpy.types.Object.motion_cam
    bpy.utils.unregister_class(MotionCamListProp)
    bpy.utils.unregister_class(MotionCamItemProps)
    # List
    bpy.utils.unregister_class(CAMHP_OT_add_motion_cam)
    bpy.utils.unregister_class(CAMHP_OT_remove_motion_cam)
    bpy.utils.unregister_class(CAMHP_OT_copy_motion_cam)
    bpy.utils.unregister_class(CAMHP_OT_move_up_motion_cam)
    bpy.utils.unregister_class(CAMHP_OT_move_down_motion_cam)

    # UI
    bpy.utils.unregister_class(CAMHP_UL_CameraList)
    bpy.utils.unregister_class(CAMHP_PT_MotionCamPanel)
    # bpy.types.VIEW3D_MT_object_context_menu.remove(draw_context)
