import bpy
import mathutils
from bpy.types import PropertyGroup, Operator, Panel, UIList
from bpy.props import CollectionProperty, PointerProperty, FloatProperty, IntProperty, StringProperty, BoolProperty, \
    EnumProperty

from .utils import meas_time, get_mesh_obj_attrs
from .utils import gen_bezier_curve_from_points, gen_sample_attr_obj, gen_sample_mesh_obj

C_ATTR_FAC = 'factor'
C_ATTR_LENGTH = 'length'
G_STATE_UPDATE = False  # 用于保护曲线更新的状态


def parse_data_path(src_obj, scr_data_path):
    """解析来自用户的data_path

    :param src_obj:
    :param scr_data_path:
    :return:
    """

    def get_obj_and_attr(obj, data_path):
        path = data_path.split('.')
        if len(path) == 1 and hasattr(obj, path[0]):
            return obj, path[0]
        else:
            if path[0] == '':
                return obj, ''
            if not hasattr(obj, path[0]):
                return obj, None

            back_obj = getattr(obj, path[0])
            back_path = '.'.join(path[1:])

            return get_obj_and_attr(back_obj, back_path)

    return get_obj_and_attr(src_obj, scr_data_path)


def get_active_motion_item(obj):
    """

    :param obj: bpy.types.Object
    :return: bpy.types.Object.motion_cam.list.item / NONE
    """
    if len(obj.motion_cam.list) > 0:
        return obj.motion_cam.list[obj.motion_cam.list_index]


def mix_value(val1, val2, fac):
    return (1 - fac) * val1 + fac * val2


def get_interpolate_euler(from_obj, to_obj, fac):
    from_quart = from_obj.matrix_world.to_quaternion().copy()
    to_quart = to_obj.matrix_world.to_quaternion().copy()
    return from_quart.slerp(to_quart, fac).to_euler()


def get_interpolate_lens(from_obj, to_obj, fac):
    return mix_value(from_obj.data.lens, to_obj.data.lens, fac)


def get_interpolate_fstop(from_obj, to_obj, fac):
    return mix_value(from_obj.data.dof.aperture_fstop, to_obj.data.dof.aperture_fstop, fac)


def get_interpolate_focal(from_obj, to_obj, fac):
    def get_focus_dis(cam):
        dis = cam.data.dof.focus_distance
        obj = cam.data.dof.focus_object
        if obj:
            get_loc = lambda ob: ob.matrix_world.translation
            dis = get_loc(obj).dist(get_loc(cam))

        return dis

    return mix_value(get_focus_dis(from_obj), get_focus_dis(to_obj), fac)


def interpolate_cam(tg_obj, from_obj, to_obj, fac):
    """用于切换相机的插值

    :param tg_obj:
    :param from_obj:
    :param to_obj:
    :param fac:
    :return:
    """
    affect = tg_obj.motion_cam.affect
    use_euler = affect.use_euler

    use_sub_camera = affect.use_sub_camera

    use_lens = affect.use_lens
    use_aperture_fstop = affect.use_aperture_fstop
    use_focus_distance = affect.use_focus_distance

    # 限定变化, 位置变化由曲线约束
    if use_euler:
        tg_obj.rotation_euler = get_interpolate_euler(from_obj, to_obj, fac)

    # 子级为相机
    if use_sub_camera and affect.sub_camera and affect.sub_camera.type == 'CAMERA':
        cam = affect.sub_camera
    elif tg_obj.type == 'CAMERA':
        cam = tg_obj
    else:
        cam = None

    # print(cam)
    if cam is None: return

    # 相机变化
    if from_obj.type == to_obj.type == 'CAMERA':
        # is_sub_camera
        if use_lens:
            cam.data.lens = get_interpolate_lens(from_obj, to_obj, fac)
        if use_aperture_fstop:
            cam.data.dof.aperture_fstop = get_interpolate_fstop(from_obj, to_obj, fac)
        if use_focus_distance and cam.data.dof.use_dof:
            cam.data.dof.focus_distance = get_interpolate_focal(from_obj, to_obj, fac)

    # 自定义
    for item in affect.custom_props:
        if item.data_path == '': continue

        src_obj, src_attr = parse_data_path(cam.data, item.data_path)
        _from_obj, from_attr = parse_data_path(from_obj.data, item.data_path)
        _to_obj, to_attr = parse_data_path(to_obj.data, item.data_path)
        if from_attr is None or to_attr is None or src_attr is None: continue

        from_value = getattr(_from_obj, from_attr)
        to_value = getattr(_to_obj, to_attr)

        try:
            if isinstance(from_value, float):
                setattr(src_obj, src_attr, mix_value(from_value, to_value, fac))
            elif isinstance(from_value, mathutils.Vector):
                setattr(src_obj, src_attr, from_value.copy().lerp(to_value, fac))
            elif isinstance(from_value, mathutils.Matrix):
                setattr(src_obj, src_attr, from_value.copy().lerp(to_value, fac))
            elif isinstance(from_value, bool):
                setattr(src_obj, src_attr, from_value)
            elif isinstance(from_value, bpy.types.Object):
                setattr(src_obj, src_attr, from_value)
        except Exception as e:
            print(e)


def gen_cam_path(self, context):
    """生成相机路径曲线

    :param self:`
    :param contexnt: m
    :return:
    """

    @meas_time
    def process():
        obj = self.id_data
        cam_list = list()
        for item in obj.motion_cam.list:
            if item.camera is not None:
                cam_list.append(item.camera)

        if len(cam_list) < 2: return

        cam_pts = [cam.matrix_world.translation for cam in cam_list]
        path = gen_bezier_curve_from_points(coords=cam_pts,
                                            type=obj.motion_cam.path_type,
                                            curve_name=obj.name + '-MotionPath',
                                            resolution_u=12)

        # 生成hook修改器(用于接受动画曲线的输入)
        path.modifiers.clear()
        for i, cam in enumerate(cam_list):
            # print(cam.name)
            hm = path.modifiers.new(
                name=f"Hook_{i}",
                type='HOOK',
            )
            if i == 0:  # bug,使用强制更新
                hm = path.modifiers.new(
                    name=f"Hook_{i}",
                    type='HOOK',
                )
            if obj.motion_cam.path_type == 'SMOOTH':
                hm.vertex_indices_set([i * 3, i * 3 + 1, i * 3 + 2])  # 跳过手柄点
            else:
                hm.vertex_indices_set([i])
            hm.object = cam

        # 生成用于采样/绘制的网格数据
        path_attr = gen_sample_attr_obj(path)
        path_mesh = gen_sample_mesh_obj(path)
        # 设置
        obj.motion_cam.path = path
        obj.motion_cam.path_attr = path_attr
        obj.motion_cam.path_mesh = path_mesh

        # 约束
        if 'Motion Camera' in obj.constraints:
            const = obj.constraints['Motion Camera']
            obj.constraints.remove(const)

        const = obj.constraints.new('FOLLOW_PATH')
        const.name = 'Motion Camera'

        const.use_fixed_location = True
        const.target = path

        try:
            const.driver_remove('offset_factor')
        except:
            pass

        d = const.driver_add('offset_factor')
        d.driver.type = 'AVERAGE'

        var1 = d.driver.variables.new()
        var1.targets[0].id = obj
        var1.targets[0].data_path = 'motion_cam.offset_factor'

        # update for driver
        path.data.update_tag()

        # hide
        coll = bpy.context.collection
        # coll.objects.unlink(path)
        # coll.objects.unlink(path_attr)
        # coll.objects.unlink(path_mesh)

    global G_STATE_UPDATE

    G_STATE_UPDATE = True
    process()
    G_STATE_UPDATE = False


# 偏移factor的get/set-------------------------------------------------------------------

def get_offset_factor(self):
    return self.get('offset_factor', 0.0)


def set_offset_factor(self, value):
    # 限制或循环val
    val = max(min(value, 1), 0)  # 循环
    self['offset_factor'] = val

    obj = self.id_data

    global G_STATE_UPDATE
    if G_STATE_UPDATE is True: return

    G_STATE_UPDATE = True

    # obj.constraints['Motion Camera'].offset_factor = value

    if 'Motion Camera' not in obj.constraints:
        return
    if obj.motion_cam.affect.enable is False:
        return

    # 防止移动帧时的无限触发更新
    if hasattr(bpy.context, 'active_operator'):
        if bpy.context.active_operator == getattr(getattr(bpy.ops, 'transform'), 'transform'): return

    path = obj.motion_cam.path
    path_attr = obj.motion_cam.path_attr
    path_mesh = obj.motion_cam.path_mesh

    if path is None or path_attr is None or path_mesh is None:
        return

    attr_values_dict = get_mesh_obj_attrs(bpy.context, path_attr)
    attr_fac = attr_values_dict.get(C_ATTR_FAC)
    attr_length = attr_values_dict.get(C_ATTR_LENGTH)

    if not attr_fac or not attr_length: return

    for i, item in enumerate(obj.motion_cam.list):
        item_next = obj.motion_cam.list[i + 1] if i < len(obj.motion_cam.list) - 1 else None
        item_pre = obj.motion_cam.list[i - 1] if i > 0 else None

        fac = attr_fac[i]

        if item_next:  # 有下一点时，用本点和下一点比较，若value存在当前区间，则在当前相机重进行转换
            from_obj = item.camera
            to_obj = item_next.camera
            next_fac = attr_fac[i + 1]

            if fac <= val < next_fac:
                true_fac = (val - fac) / (next_fac - fac)

                interpolate_cam(obj, from_obj, to_obj, true_fac)
                break
        else:  # 不存在下一点时，与上一点进行比较
            if item_pre is None: continue

            from_obj = item_pre.camera
            to_obj = item.camera
            pre_fac = attr_fac[i - 1]

            if pre_fac <= val < fac:
                true_fac = (val - pre_fac) / (fac - pre_fac)
            else:
                true_fac = 1

            interpolate_cam(obj, from_obj, to_obj, true_fac)
            break

    G_STATE_UPDATE = False


def update_driver(self, context):
    obj = self.id_data
    if 'Motion Camera' not in obj.constraints:
        return
    cons = obj.constraints['Motion Camera']
    cons.enabled = obj.motion_cam.affect.enable


#  --------------------------------------------------------------------------------

# Properties --------------------------------------------------------------
###############################################################################

class MotionCamItemProps(PropertyGroup):
    camera: PointerProperty(name='Camera', type=bpy.types.Object,
                            poll=lambda self, obj: obj.type == 'CAMERA' and obj != self,
                            update=gen_cam_path)


class MotionCamAffectCustomProp(PropertyGroup):
    data_path: StringProperty(name='Data Path', default='')


class MotionCamAffect(PropertyGroup):
    enable: BoolProperty(name='Enable', default=True, update=update_driver, options={'HIDDEN'}, )

    use_euler: BoolProperty(name='Rotation', default=True, options={'HIDDEN'})
    # search for sub camera
    use_sub_camera: BoolProperty(name='Sub Camera', default=False, options={'HIDDEN'})
    sub_camera: PointerProperty(type=bpy.types.Object)

    use_lens: BoolProperty(name='Focal Length', default=True, options={'HIDDEN'})
    use_focus_distance: BoolProperty(name='Focus Distance', default=True, options={'HIDDEN'})
    use_aperture_fstop: BoolProperty(name='F-Stop', default=True, options={'HIDDEN'})

    custom_props: CollectionProperty(type=MotionCamAffectCustomProp)


class MotionCamListProp(PropertyGroup):
    # UI
    ui: EnumProperty(items=[('CONTROL', 'Set', ''), ('AFFECT', 'Affect', '')], options={'HIDDEN'})
    # 相机列表
    list: CollectionProperty(name='List', type=MotionCamItemProps)
    list_index: IntProperty(name='List', min=0, default=0, update=gen_cam_path)

    # 路径
    path: PointerProperty(type=bpy.types.Object)
    path_attr: PointerProperty(type=bpy.types.Object)  # 用于实时采样属性
    path_mesh: PointerProperty(type=bpy.types.Object)  # 用于实时采样位置，绘制
    path_type: EnumProperty(name='Type', items=[('LINEAR', 'Linear', ''), ('SMOOTH', 'Smooth', '')],
                            default='SMOOTH',
                            options={'HIDDEN'},
                            update=gen_cam_path)

    # 偏移 用于混合相机其他参数
    offset_factor: FloatProperty(name='Offset Factor', min=0, max=1,
                                 description='Offset Factor',
                                 set=set_offset_factor,
                                 get=get_offset_factor)

    # 影响
    affect: PointerProperty(type=MotionCamAffect)


###############################################################################


# List/Operators ---------------------------------------------------------------
###############################################################################

class CAMHP_OT_affect_add_custom_prop(Operator):
    bl_idname = 'camhp.affect_add_custom_prop'
    bl_label = 'Add Custom Prop'
    bl_description = 'Add Custom Prop'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        m_cam = obj.motion_cam
        affect = m_cam.affect

        item = affect.custom_props.add()
        return {'FINISHED'}


class CAMHP_OT_affect_remove_custom_prop(Operator):
    bl_idname = 'camhp.affect_remove_custom_prop'
    bl_label = 'Remove'
    bl_description = 'Remove Custom Prop'
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    def execute(self, context):
        obj = context.object
        m_cam = obj.motion_cam
        affect = m_cam.affect

        affect.custom_props.remove(self.index)
        return {'FINISHED'}


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
                bpy.ops.camhp.motion_list_up()

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
                bpy.ops.camhp.motion_list_up()

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


class CAMHP_OT_motion_list_add(ListAction, Operator):
    """"""
    bl_idname = 'camhp.motion_list_add'
    bl_label = 'Add'

    action = 'ADD'


class CAMHP_OT_motion_list_remove(ListAction, Operator):
    """"""
    bl_idname = 'camhp.motion_list_remove'
    bl_label = 'Remove'

    action = 'REMOVE'


class CAMHP_OT_copy_motion_cam(ListAction, Operator):
    """"""
    bl_idname = 'camhp.motion_list_copy'
    bl_label = 'Copy'

    action = 'COPY'


class CAMHP_OT_move_up_motion_cam(ListMove, Operator):
    """"""
    bl_idname = 'camhp.motion_list_up'
    bl_label = 'Move Up'

    action = 'UP'


class CAMHP_OT_move_down_motion_cam(ListMove, Operator):
    """"""
    bl_idname = 'camhp.motion_list_down'
    bl_label = 'Move Down'

    action = 'DOWN'


# Operator for the list of cameras -------------------------------------------
###############################################################################

from .draw_utils.bl_ui_draw_op import BL_UI_OT_draw_operator
from .draw_utils.bl_ui_button import BL_UI_Button
from .draw_utils.bl_ui_drag_panel import BL_UI_Drag_Panel
from .draw_utils.bl_ui_label import BL_UI_Label

from bpy_extras.view3d_utils import location_3d_to_region_2d
from bpy.app.translations import pgettext_iface as tip_


def get_obj_2d_loc(obj, context):
    r3d = context.space_data.region_3d

    x, y = location_3d_to_region_2d(context.region, r3d, obj.matrix_world.translation)
    return x, y


class CAMHP_PT_add_motion_cams(BL_UI_OT_draw_operator, Operator):
    bl_idname = 'camhp.add_motion_cams'
    bl_label = 'Add Motion Camera'
    bl_options = {'UNDO_GROUPED', 'INTERNAL', 'BLOCKING', 'GRAB_CURSOR'}

    buttons = list()
    cam = None

    def __init__(self):
        super().__init__()
        self.buttons.clear()

        # 面板提示
        self.panel = BL_UI_Drag_Panel(100, 300, 300, 290)
        self.panel.bg_color = 0.2, 0.2, 0.2, 0.9

        # self.btn_close = BL_UI_Button(20, 100, 120, 30)
        # self.btn_close.bg_color = (0.2, 0.8, 0.8, 0.8)
        # self.btn_close.hover_bg_color = (0.2, 0.9, 0.9, 1.0)
        # self.btn_close.text = "Finished"
        # self.btn_close.set_mouse_down(self.finish, None)

        self.label_tip1 = BL_UI_Label(20, 120, 40, 50)
        self.label_tip1.text = tip_('Left Click->Camera Name to Add Source')
        self.label_tip1.text_size = 22

        self.label_tip2 = BL_UI_Label(20, 95, 40, 50)
        self.label_tip2.text = tip_('Right Click->End Add Mode')
        self.label_tip2.text_size = 22

        self.label_tip3 = BL_UI_Label(20, 70, 40, 50)
        self.label_tip3.text = tip_('ESC->Cancel')
        self.label_tip3.text_size = 22

        # 为每个相机添加一个按钮
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
        widgets_panel = [self.label_tip1, self.label_tip2, self.label_tip3]
        widgets = [self.panel]
        widgets += widgets_panel

        self.init_widgets(context, widgets_panel + self.buttons)

        self.panel.add_widgets(widgets_panel)

        # Open the panel at the mouse location
        self.panel.set_location(context.area.width * 0.8,
                                context.area.height * 1)

        # 创建相机
        cam_data = bpy.data.cameras.new(name='Camera')
        cam = bpy.data.objects.new('Camera', cam_data)
        empty = bpy.data.objects.new('Empty', None)

        context.collection.objects.link(cam)
        context.collection.objects.link(empty)
        # 设置
        cam.data.show_name = True
        cam.name = 'Motion Camera'
        cam.parent = empty

        empty.name = 'Motion Control'
        empty.motion_cam.affect.use_sub_camera = True
        empty.motion_cam.affect.sub_camera = cam
        # empty.empty_display_type = 'CUBE'

        self.cam = empty

    def add_motion_cam(self, obj):
        item = self.cam.motion_cam.list.add()
        item.camera = obj
        self.cam.motion_cam.offset_factor = 0.5
        self.cam.update_tag()

        bpy.context.view_layer.objects.active = self.cam
        self.cam.select_set(True)
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


# bake motion camera
class CAMHP_OT_bake_motion_cam(bpy.types.Operator):
    bl_idname = "camhp.bake_motion_cam"
    bl_label = "Bake Motion Camera"

    frame_start: IntProperty(name="Start Frame", default=1)
    frame_end: IntProperty(name="End Frame", default=100)
    frame_step: IntProperty(name="Frame Step", default=1)

    # bake
    cam = None
    ob = None

    def modal(self, context, event):
        if event.type == 'ESC':
            return {'CANCELLED'}

        frame = self.frame
        ob = self.cam_bake
        affect = self.affect
        cam = self.cam

        if frame > self.frame_end:
            return {'FINISHED'}

        context.scene.frame_set(frame)
        matrix = context.object.matrix_world.copy()

        # 位置
        loc = matrix.to_translation()
        ob.location = loc
        ob.keyframe_insert('location')

        if affect.use_euler:
            if self.euler_prev is None:
                euler = matrix.to_euler(context.object.rotation_mode)
            else:
                euler = matrix.to_euler(context.object.rotation_mode, self.euler_prev)
            self.euler_prev = euler.copy()

            ob.rotation_euler = self.euler_prev
            ob.keyframe_insert('rotation_euler')

        if not cam: return {'PASS_THROUGH'}
        # 相机数值
        if affect.use_lens:
            cam.update_tag()
            print(cam.data.lens)
            ob.data.lens = cam.data.lens
            print(ob.data.lens)

            ob.data.keyframe_insert('lens')

        if affect.use_focus_distance:
            ob.data.dof.focus_distance = cam.data.dof.focus_distance
            ob.data.dof.keyframe_insert('focus_distance')

        if affect.use_aperture_fstop:
            ob.data.dof.aperture_fstop = cam.data.dof.aperture_fstop
            ob.data.dof.keyframe_insert('aperture_fstop')

        # 自定义属性
        for item in affect.custom_props:
            if item.data_path == '': continue

            tg_obj = ob
            from_obj = context.object

            src_obj, src_attr = parse_data_path(tg_obj.data, item.data_path)
            _from_obj, from_attr = parse_data_path(from_obj.data, item.data_path)
            if from_attr is None or src_attr is None or src_obj is None: continue

            from_value = getattr(_from_obj, from_attr)

            try:
                if isinstance(from_value, float):
                    setattr(src_obj, src_attr, from_value)
                elif isinstance(from_value, mathutils.Vector):
                    setattr(src_obj, src_attr, from_value)
                elif isinstance(from_value, mathutils.Matrix):
                    setattr(src_obj, src_attr, from_value)
                elif isinstance(from_value, bool):
                    setattr(src_obj, src_attr, from_value)
                elif isinstance(from_value, bpy.types.Object):
                    setattr(src_obj, src_attr, from_value)

                if hasattr(src_obj, 'keyframe_insert'):
                    kf = getattr(src_obj, 'keyframe_insert')
                    kf(src_attr)

            except Exception as e:
                print(e)

        return {'PASS_THROUGH'}

    def execute(self, context):
        m_cam = context.object.motion_cam
        affect = m_cam.affect

        if context.object.type == 'CAMERA':
            cam = context.object
        elif (affect.use_sub_camera and
              affect.sub_camera and
              affect.sub_camera.type == 'CAMERA'):

            cam = affect.sub_camera
        else:
            cam = None

        if cam is None:
            self.report({'ERROR'}, "No camera found")
            return {'CANCELLED'}

        name = cam.name + '_bake'
        data_name = cam.data.name + '_bake'

        cam_data = bpy.data.cameras.new(name=data_name)
        ob = bpy.data.objects.new(name, cam_data)
        ob.constraints.clear()
        ob.location = 0, 0, 0

        context.collection.objects.link(ob)

        context.scene.frame_set(self.frame_start)

        self.frame = self.frame_start
        self.cam = cam
        self.cam_bake = ob
        self.affect = affect
        self.euler_prev = None

        return {"RUNNING_MODAL"}

    def invoke(self, context, event):
        wm = context.window_manager

        return self.execute(context)
        # return wm.invoke_props_dialog(self)


###############################################################################


# UI -------------------------------------------
###############################################################################

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
        elif context.object.motion_cam.ui == 'AFFECT':
            self.draw_setttings(context, layout)

    def draw_control(self, context, layout):
        layout.label(text=context.object.name, icon=context.object.type + '_DATA')

        layout.prop(context.object.motion_cam, 'path_type')
        layout.prop(context.object.motion_cam, 'offset_factor', slider=True)

        # 视口k帧
        if context.area.type == 'VIEW_3D':
            layout.operator('camhp.insert_keyframe')

        layout.label(text='Source')
        box = layout.box()
        row = box.row(align=True)

        col = row.column(align=0)

        col.template_list(
            "CAMHP_UL_CameraList", "The list",
            context.object.motion_cam, "list",
            context.object.motion_cam, "list_index", )

        col_btn = row.column(align=1)

        col_btn.operator('camhp.motion_list_add', text='', icon='ADD')

        d = col_btn.operator('camhp.motion_list_remove', text='', icon='REMOVE')
        d.index = context.object.motion_cam.list_index

        col_btn.separator()

        col_btn.operator('camhp.motion_list_up', text='', icon='TRIA_UP')
        col_btn.operator('camhp.motion_list_down', text='', icon='TRIA_DOWN')

        col_btn.separator()

        c = col_btn.operator('camhp.motion_list_copy', text='', icon='DUPLICATE')
        c.index = context.object.motion_cam.list_index

        layout.operator('camhp.bake_motion_cam')

    def draw_setttings(self, context, layout):

        col = layout.column()
        col.use_property_split = True
        col.active = context.object.motion_cam.affect.enable

        affect = context.object.motion_cam.affect

        col.prop(affect, 'enable')

        col.separator()

        col.prop(affect, 'use_euler')

        col.prop(affect, 'use_sub_camera')
        col.prop(affect, 'sub_camera', text='')

        sub = col.column()
        sub.active = False
        if context.object.type != 'CAMERA':
            if affect.sub_camera is None or affect.sub_camera.type != 'CAMERA':
                sub.active = affect.use_sub_camera
                warn = sub.column()
                warn.alert = True
                warn.label(text='There is no camera as child of this object')
        else:
            sub.active = True

        sub.prop(affect, 'use_lens')

        sub.separator()

        box = sub.box().column(align=True)
        box.label(text='Depth of Field')
        box.prop(affect, 'use_focus_distance')
        box.prop(affect, 'use_aperture_fstop')

        box = sub.box().column(align=True)
        box.label(text='Custom Properties')
        box.separator()

        for i, item in enumerate(affect.custom_props):
            if i == 0:
                box.label(text='Data Path')

            row = box.row()
            row.use_property_split = False
            # 检测是否有效
            src_obj, src_attr = parse_data_path(context.object.data, item.data_path)
            if src_attr is None:
                row.alert = True
                row.label(text='Invalid')

            row.prop(item, 'data_path', text='')

            row.operator('camhp.affect_remove_custom_prop', text='', icon='X', emboss=False).index = i
            box.separator(factor=0.5)

        box.separator(factor=0.5)
        box.operator('camhp.affect_add_custom_prop', text='Add', icon='ADD')


def draw_context(self, context):
    if context.object and context.object.type in {'CAMERA', 'EMPTY'}:
        layout = self.layout
        layout.separator()
        op = layout.operator('wm.call_panel', text='Motion Camera')
        op.name = 'CAMHP_PT_MotionCamPanel'
        op.keep_open = True
        layout.separator()


def draw_add_context(self, context):
    if context.object.type == "CAMERA":
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator('camhp.add_motion_cams')


###############################################################################

def register():
    bpy.utils.register_class(MotionCamItemProps)
    bpy.utils.register_class(MotionCamAffectCustomProp)
    bpy.utils.register_class(MotionCamAffect)
    bpy.utils.register_class(MotionCamListProp)
    bpy.types.Object.motion_cam = PointerProperty(type=MotionCamListProp)
    # list action
    bpy.utils.register_class(CAMHP_OT_affect_add_custom_prop)
    bpy.utils.register_class(CAMHP_OT_affect_remove_custom_prop)

    bpy.utils.register_class(CAMHP_OT_motion_list_add)
    bpy.utils.register_class(CAMHP_OT_motion_list_remove)
    bpy.utils.register_class(CAMHP_OT_copy_motion_cam)
    bpy.utils.register_class(CAMHP_OT_move_up_motion_cam)
    bpy.utils.register_class(CAMHP_OT_move_down_motion_cam)

    # UI
    bpy.utils.register_class(CAMHP_UL_CameraList)
    bpy.utils.register_class(CAMHP_PT_MotionCamPanel)

    bpy.utils.register_class(CAMHP_PT_add_motion_cams)
    bpy.utils.register_class(CAMHP_OT_bake_motion_cam)

    # bpy.types.VIEW3D_MT_object_context_menu.append(draw_context)
    bpy.types.VIEW3D_MT_object_context_menu.append(draw_add_context)


def unregister():
    del bpy.types.Object.motion_cam
    bpy.utils.unregister_class(MotionCamListProp)
    bpy.utils.unregister_class(MotionCamAffect)
    bpy.utils.unregister_class(MotionCamAffectCustomProp)
    bpy.utils.unregister_class(MotionCamItemProps)
    # List
    bpy.utils.unregister_class(CAMHP_OT_affect_add_custom_prop)
    bpy.utils.unregister_class(CAMHP_OT_affect_remove_custom_prop)

    bpy.utils.unregister_class(CAMHP_OT_motion_list_add)
    bpy.utils.unregister_class(CAMHP_OT_motion_list_remove)
    bpy.utils.unregister_class(CAMHP_OT_copy_motion_cam)
    bpy.utils.unregister_class(CAMHP_OT_move_up_motion_cam)
    bpy.utils.unregister_class(CAMHP_OT_move_down_motion_cam)

    # UI
    bpy.utils.unregister_class(CAMHP_UL_CameraList)
    bpy.utils.unregister_class(CAMHP_PT_MotionCamPanel)

    bpy.utils.unregister_class(CAMHP_PT_add_motion_cams)
    bpy.utils.unregister_class(CAMHP_OT_bake_motion_cam)
    # bpy.types.VIEW3D_MT_object_context_menu.remove(draw_context)
    bpy.types.VIEW3D_MT_object_context_menu.remove(draw_add_context)
