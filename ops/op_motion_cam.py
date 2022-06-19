import bpy
from bpy.types import PropertyGroup, Operator, Panel, UIList
from bpy.props import CollectionProperty, PointerProperty, FloatProperty, IntProperty, StringProperty, BoolProperty, \
    EnumProperty
from pathlib import Path


def meas_time(func):
    """计时装饰器

    :param func:
    :return:
    """

    def wrapper(*args, **kwargs):
        import time
        t = time.time()
        func(*args, **kwargs)
        end = time.time()
        print(func.__name__, f'花费 {(end - t) / 1000}ms')

    return wrapper


def get_active_motion_item(obj):
    """

    :param obj: bpy.types.Object
    :return: bpy.types.Object.motion_cam.list.item / NONE
    """
    if len(obj.motion_cam.list) > 0:
        return obj.motion_cam.list[obj.motion_cam.list_index]


def interpolate_cam(tg_obj, from_obj, to_obj, fac):
    """用于切换相机的插值

    :param tg_obj:
    :param from_obj:
    :param to_obj:
    :param fac:
    :return:
    """
    influence = fac

    use_euler = tg_obj.motion_cam.use_euler
    use_lens = tg_obj.motion_cam.use_lens
    use_aperture_fstop = tg_obj.motion_cam.use_aperture_fstop
    use_focus_distance = tg_obj.motion_cam.use_focus_distance

    # 限定变化
    if use_euler:
        from_quart = from_obj.matrix_world.to_quaternion().copy()
        to_quart = to_obj.matrix_world.to_quaternion().copy()
        tg_quart = from_quart.slerp(to_quart, influence)
        tg_obj.rotation_euler = tg_quart.to_euler()

    if from_obj.type == to_obj.type == 'CAMERA':
        if use_lens:
            tg_lens = (1 - influence) * from_obj.data.lens + influence * to_obj.data.lens
            tg_obj.data.lens = tg_lens
        if use_aperture_fstop:
            tg_fstop = (1 - influence) * from_obj.data.dof.aperture_fstop + influence * to_obj.data.dof.aperture_fstop
            tg_obj.data.dof.aperture_fstop = tg_fstop
        if use_focus_distance:
            if tg_obj.data.dof.use_dof:

                def get_focus_dis(cam):
                    dis = cam.data.dof.focus_distance
                    obj = cam.data.dof.focus_object
                    if obj:
                        get_loc = lambda ob: ob.matrix_world.translation
                        dis = get_loc(obj).dist(get_loc(cam))

                    return dis

                tg_dis = (1 - influence) * get_focus_dis(from_obj) + influence * get_focus_dis(to_obj)
                tg_obj.data.dof.focus_distance = tg_dis


def curve_bezier_from_points(coords: list, curve_name, close_spline=False):
    """穿过点并创建贝塞尔

    :param coords: 一系列点的位置
    :param curve_name: 曲线名
    :param close_spline: 循环曲线
    :return:
    """
    # 清理
    if curve_name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[curve_name])

    if curve_name in bpy.data.curves:
        bpy.data.curves.remove(bpy.data.curves[curve_name])

    # 创建曲线
    curve_data = bpy.data.curves.new(curve_name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 12

    spline = curve_data.splines.new('BEZIER')
    spline.bezier_points.add(len(coords) - 1)

    for i, coord in enumerate(coords):
        x, y, z = coord
        spline.bezier_points[i].handle_right_type = 'AUTO'
        spline.bezier_points[i].handle_left_type = 'AUTO'

        spline.bezier_points[i].co = (x, y, z)
        spline.bezier_points[i].handle_left = (x, y, z)
        spline.bezier_points[i].handle_right = (x, y, z)

    # 闭合，或为可选项
    spline.use_cyclic_u = close_spline

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
    # 链接到场景
    coll = bpy.context.collection
    coll.objects.link(curve_obj)

    return curve_obj


def get_curve_pt_fac(curve):
    """获取控制点再曲线上的factor

    :param curve: bpy.types.Object
    :return res: tuple[Vector]
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

    for coll in curve.users_collection:
        coll.objects.unlink(curve)

    return res


def sample_curve_points(curve):
    deg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(curve.evaluated_get(deg), depsgraph=deg)
    points = list()

    for i, v in enumerate(me.vertices):
        if i == 0 or i == len(me.vertices) - 1:
            points.append(list(v.co))
        else:
            points.append(list(v.co))
            points.append(list(v.co))

    bpy.data.meshes.remove(me)

    return points


def gen_cam_path(self, context):
    """生成相机路径曲线

    :param self:
    :param context:
    :return:
    """

    def process():
        obj = self.id_data
        cam_list = list()
        for item in obj.motion_cam.list:
            cam_list.append(item.camera)

        cam_pts = [cam.matrix_world.translation for cam in cam_list]
        path = curve_bezier_from_points(cam_pts, obj.name + '-MotionPath')
        path.modifiers.clear()

        # # hook
        # for i, cam in enumerate(cam_list):
        #     print(cam.name)
        #     hm = path.modifiers.new(
        #         name=f"Hook_{i}",
        #         type='HOOK',
        #     )
        #     if i == 0:  # bug,使用强制更新
        #         hm = path.modifiers.new(
        #             name=f"Hook_{i}",
        #             type='HOOK',
        #         )
        #
        #     hm.vertex_indices_set([i * 3, i * 3 + 1, i * 3 + 2])
        #     hm.object = cam

        pts_fac = get_curve_pt_fac(path)
        for i, fac in enumerate(pts_fac):
            obj.motion_cam.list[i].fac = fac

        # bind
        obj.motion_cam.path = path
        points = sample_curve_points(path)
        obj.motion_cam.path_points = '$'.join([f'{co}' for co in points])

        # constraint
        if 'Motion Camera' in obj.constraints:
            const = obj.constraints['Motion Camera']
            obj.constraints.remove(const)

        const = obj.constraints.new('FOLLOW_PATH')
        const.name = 'Motion Camera'

        const.use_fixed_location = True
        const.target = path

        d = const.driver_add('offset_factor')
        d.driver.type = 'AVERAGE'

        var1 = d.driver.variables.new()
        var1.targets[0].id = obj
        var1.targets[0].data_path = 'motion_cam.offset_factor'

        # update for driver
        path.data.update_tag()

    process()


def poll_camera(self, obj):
    """用于过滤用户选项，相机或者普通物体

    :param self:
    :param obj:
    :return:
    """
    if obj != self.id_data:
        return obj.type == 'CAMERA' if self.filter_camera else True


class MotionCamItemProps(PropertyGroup):
    filter_camera: BoolProperty(name='Filter Camera', default=True)
    camera: PointerProperty(name='Camera', type=bpy.types.Object, poll=poll_camera, update=gen_cam_path)
    # 储存相机偏移值
    fac: FloatProperty(name='Offset Factor', min=0, max=1)


def get_offset_factor(self):
    return self.get('offset_factor', 0.0)


def set_offset_factor(self, value):
    val = max(min(value, 1), 0)
    self['offset_factor'] = val

    if 'Motion Camera' not in self.id_data.constraints:
        return
    obj = self.id_data
    # obj.constraints['Motion Camera'].offset_factor = value

    for i, item in enumerate(obj.motion_cam.list):
        item_next = obj.motion_cam.list[i + 1] if i < len(obj.motion_cam.list) - 1 else None
        item_pre = obj.motion_cam.list[i - 1] if i > 0 else None
        fac = item.fac

        if item_next:  # 有下一点时，用本点和下一点比较，若value存在当前区间，则在当前相机重进行转换
            from_obj = item.camera
            to_obj = item_next.camera

            if fac <= val < item_next.fac:
                true_fac = (val - fac) / (item_next.fac - fac)

                interpolate_cam(obj, from_obj, to_obj, true_fac)
                break
        else:  # 不存在下一点时，与上一点进行比较
            from_obj = item_pre.camera
            to_obj = item.camera

            if item_pre.fac <= val < fac:
                true_fac = (val - item_pre.fac) / (fac - item_pre.fac)
            else:
                true_fac = 1

            interpolate_cam(obj, from_obj, to_obj, true_fac)
            break


class MotionCamListProp(PropertyGroup):
    # UI
    ui: EnumProperty(items=[('CONTROL', 'Set', ''), ('AFFECT', 'Affect', '')], options={'HIDDEN'})
    update: BoolProperty(update=gen_cam_path)
    # 约束列表
    list: CollectionProperty(name='List', type=MotionCamItemProps)
    list_index: IntProperty(name='List', min=0, default=0)

    # 路径与偏移
    path: PointerProperty(type=bpy.types.Object)
    # 用于绘制的点，通过$合并储存
    path_points: StringProperty()
    # 偏移 用于混合相机其他参数
    offset_factor: FloatProperty(name='Offset Factor', min=0, max=1,
                                 set=set_offset_factor,
                                 get=get_offset_factor)

    # 限定
    use_euler: BoolProperty(name='Rotate', default=True, options={'HIDDEN'})
    use_lens: BoolProperty(name='Focal Length', default=True, options={'HIDDEN'})
    use_focus_distance: BoolProperty(name='Focus Distance', default=True, options={'HIDDEN'})
    use_aperture_fstop: BoolProperty(name='F-Stop', default=True, options={'HIDDEN'})


class CAMHP_UL_CameraList(UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.label(text='', icon='CAMERA_DATA')
        layout.prop(item, 'camera', text='', emboss=True)


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


from mathutils import Vector
from ..gz.draw_utils.bl_ui_draw_op import BL_UI_OT_draw_operator
from ..gz.draw_utils.bl_ui_button import BL_UI_Button

from bpy_extras.view3d_utils import location_3d_to_region_2d


def get_obj_2d_loc(obj, context):
    r3d = context.space_data.region_3d

    x, y = location_3d_to_region_2d(context.region, r3d, obj.matrix_world.translation)
    return x, y


class CAMHP_PT_add_motion_cams(BL_UI_OT_draw_operator, Operator):
    bl_idname = 'camhp.add_motion_cams'
    bl_label = 'Add Motion Camera'

    buttons = list()
    cam = None

    def __init__(self):
        super().__init__()
        self.buttons.clear()

        for obj in bpy.context.view_layer.objects:
            if obj.type != 'CAMERA': continue

            x, y = get_obj_2d_loc(obj, bpy.context)

            btn = BL_UI_Button(x, y, 120, 30)
            btn.bg_color = (0.1, 0.1, 0.1, 0.8)
            btn.hover_bg_color = (0.6, 0.6, 0.6, 0.8)
            btn.text = obj.name
            # button1.set_image("//img/scale_24.png")
            # self.button1.set_image_size((24,24))
            # button1.set_image_position((4, 2))
            btn.set_mouse_down(self.add_motion_cam, obj)
            setattr(btn, 'bind_obj', obj.name)

            self.buttons.append(btn)

    def on_invoke(self, context, event):
        self.init_widgets(context, self.buttons)

        # 创建相机
        cam_data = bpy.data.cameras.new(name='Camera')
        cam = bpy.data.objects.new('Camera', cam_data)
        context.collection.objects.link(cam)
        # 设置
        cam.data.show_name = True
        cam.name = 'Motion Camera'
        self.cam = cam

    def add_motion_cam(self, obj):
        item = self.cam.motion_cam.list.add()
        item.camera = obj
        self.cam.motion_cam.offset_factor = 0.3
        self.cam.update_tag()

        bpy.context.view_layer.objects.active = self.cam
        bpy.context.area.tag_redraw()

    def modal(self, context, event):

        for i, btn in enumerate(self.buttons):
            if hasattr(btn, 'bind_obj'):
                obj_name = getattr(btn, 'bind_obj')
                obj = bpy.data.objects.get(obj_name)

                if obj:
                    x, y = get_obj_2d_loc(obj, context)
                    btn.update(x, y)
                    context.area.tag_redraw()

        return super().modal(context, event)


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

        # layout.use_property_decorate = False
        row = layout.row(align=True)
        row.prop(context.object.motion_cam, 'ui', expand=True)

        if context.object.motion_cam.ui == 'CONTROL':
            self.draw_control(context, layout)
        else:
            self.draw_setttings(context, layout)

    def draw_control(self, context, layout):
        layout.label(text=context.object.name, icon=context.object.type + '_DATA')

        layout.prop(context.object.motion_cam, 'offset_factor', slider=True)

        layout.label(text='Source')
        box = layout.box()
        row = box.row(align=True)

        col = row.column(align=0)

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

    def draw_setttings(self, context, layout):
        col = layout.column()
        col.use_property_split = True

        col.prop(context.object.motion_cam, 'use_euler')
        col.prop(context.object.motion_cam, 'use_lens')

        col.separator()

        box = col.box().column(align=True)
        box.label(text='Depth of Field')
        box.prop(context.object.motion_cam, 'use_focus_distance')
        box.prop(context.object.motion_cam, 'use_aperture_fstop')


def draw_context(self, context):
    if context.object and context.object.type in {'CAMERA', 'EMPTY'}:
        layout = self.layout
        layout.separator()
        op = layout.operator('wm.call_panel', text='Motion Camera')
        op.name = 'CAMHP_PT_MotionCamPanel'
        op.keep_open = True
        layout.separator()


def draw_add_context(self, context):
    if context.mode == 'OBJECT':
        self.layout.operator('camhp.add_motion_cams')


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

    bpy.utils.register_class(CAMHP_PT_add_motion_cams)

    # bpy.types.VIEW3D_MT_object_context_menu.append(draw_context)
    bpy.types.VIEW3D_MT_camera_add.append(draw_add_context)


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

    bpy.utils.unregister_class(CAMHP_PT_add_motion_cams)
    # bpy.types.VIEW3D_MT_object_context_menu.remove(draw_context)
