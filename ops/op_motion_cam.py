import bpy
from bpy.types import PropertyGroup, Operator, Panel, UIList
from bpy.props import CollectionProperty, PointerProperty, FloatProperty, IntProperty, StringProperty, BoolProperty


def get_active_motion_item(obj):
    """

    :param obj: bpy.types.Object
    :return: bpy.types.Object.motion_cam.list.item / NONE
    """
    if len(obj.motion_cam.list) > 0:
        return obj.motion_cam.list[obj.motion_cam.active_index]


def get_edit_motion_item(obj):
    if len(obj.motion_cam.list) > 0:
        return obj.motion_cam.list[obj.motion_cam.list_index]


# 用于过滤用户选项，相机或者普通物体
def poll_camera(self, obj):
    if obj != self.id_data:
        return obj.type == 'CAMERA' if self.filter_camera else True


def interpolate_cam(self):
    tg_obj = self.id_data

    if self != get_active_motion_item(self.id_data): return
    if not self.from_obj and self.to_obj: return

    # 限定变化
    if self.use_loc:
        from_loc = self.from_obj.matrix_world.to_translation().copy()
        to_loc = self.to_obj.matrix_world.to_translation().copy()
        tg_loc = from_loc.lerp(to_loc, self.influence)
        tg_obj.location = tg_loc

    if self.use_euler:
        from_quart = self.from_obj.matrix_world.to_quaternion().copy()
        to_quart = self.to_obj.matrix_world.to_quaternion().copy()
        tg_quart = from_quart.slerp(to_quart, self.influence)
        tg_obj.rotation_euler = tg_quart.to_euler()

    if self.from_obj.type == self.to_obj.type == 'CAMERA' and self.use_lens:
        tg_lens = (1 - self.influence) * self.from_obj.data.lens + self.influence * self.to_obj.data.lens
        tg_obj.data.lens = tg_lens


def get_influence(self):
    return self.get("influence", 0.0)


def set_influence(self, value):
    self["influence"] = value
    interpolate_cam(self)


def update_src(self, context):
    interpolate_cam(self)


class MotionCamItemProps(PropertyGroup):
    name: StringProperty(name='')
    # 只选择相机
    filter_camera: BoolProperty(name='Filter Camera', default=True)
    # 来源
    from_obj: PointerProperty(name='From', type=bpy.types.Object, poll=poll_camera, update=update_src)
    to_obj: PointerProperty(name='To', type=bpy.types.Object, poll=poll_camera, update=update_src)
    # 动画
    influence: FloatProperty(name='Influence',
                             min=0,
                             max=1,
                             set=set_influence,
                             get=get_influence,
                             options={'ANIMATABLE'}, default=0.5)
    # 限定
    use_loc: BoolProperty(name='Location', default=True)
    use_euler: BoolProperty(name='Rotate', default=True)
    use_lens: BoolProperty(name='Lens', default=True)


def get_active(self):
    if self.link_selected:
        return self.get("list_index", 0)
    return self.get("active_index", 0)


def set_active(self, value):
    obj = self.id_data
    if value >= len(obj.motion_cam.list):
        self["active_index"] = len(obj.motion_cam.list) - 1
    else:
        self["active_index"] = value


class MotionCamListProp(PropertyGroup):
    # 约束列表
    list: CollectionProperty(name='List', type=MotionCamItemProps)
    list_index: IntProperty(name='List Index', default=0, min=0)

    active_index: IntProperty(name='Active', default=0, min=0, options={'ANIMATABLE'}, set=set_active, get=get_active)
    link_selected: BoolProperty(name='Link Active to Selected', default=True, options={'HIDDEN'})


class CAMHP_UL_CameraList(UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=False)
        row.use_property_decorate = False
        sub = row.row(align=True)
        sub.prop(item, 'name', emboss=False)
        sub = row.row(align=True)
        sub.prop(item, 'influence', slider=True, text='', emboss=True)


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


class CAMHP_OT_init_motion_cam(Operator):
    """Initialize"""
    bl_idname = 'camhp.init_motion_cam'
    bl_label = 'Initialize'

    @classmethod
    def poll(cls, context):
        return context.object

    def execute(self, context):
        context.object.keyframe_insert('delta_scale', frame=0)
        cam = bpy.context.object

        remain = None

        for fcurve in cam.animation_data.action.fcurves:
            if fcurve.data_path != 'delta_scale': continue

            fcurve.lock = True
            fcurve.hide = True
            fcurve.mute = True
            if remain is None:
                remain = fcurve
            else:
                cam.animation_data.action.fcurves.remove(fcurve)

        bpy.ops.camhp.add_motion_cam()

        return {'FINISHED'}


class CAMHP_PT_MotionCamPanel(Panel):
    bl_label = 'Motion Camera'
    bl_space_type = 'PROPERTIES'
    bl_idname = 'CAMHP_PT_MotionCamPanel'
    bl_context = "object"
    bl_region_type = 'WINDOW'

    @classmethod
    def poll(self, context):
        return context.object and context.object.type in {'EMPTY', 'CAMERA'}

    def is_init(self):
        """ 检查相机是否初始化

        :return:
        """
        INIT = False

        cam = bpy.context.object
        if cam.animation_data is None: return
        if cam.animation_data.action is None: return

        for fcurve in cam.animation_data.action.fcurves:
            if fcurve.data_path == 'delta_scale': INIT = True

        return INIT

    def draw(self, context):
        layout = self.layout
        if not self.is_init():
            layout.operator('CAMHP_OT_init_motion_cam')
            return

        layout.use_property_split = True
        # layout.use_property_decorate = False
        layout.label(text=context.object.name, icon=context.object.type + '_DATA')

        row = layout.row(align=True)
        row.prop(context.object.motion_cam, 'active_index')
        row.prop(context.object.motion_cam, 'link_selected', text='',
                 icon='LINKED' if context.object.motion_cam.link_selected else 'UNLINKED')

        row = layout.row(align=1)

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

        m_cam = get_edit_motion_item(context.object)

        layout.prop(m_cam, 'from_obj')
        layout.prop(m_cam, 'influence', slider=True, icon='ARROW_LEFTRIGHT')
        layout.prop(m_cam, 'to_obj')

        col = layout.column(align=True)
        col.use_property_decorate = False

        col.prop(m_cam, 'use_loc')
        col.prop(m_cam, 'use_euler')
        col.prop(m_cam, 'use_lens')


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

    bpy.utils.register_class(CAMHP_OT_init_motion_cam)

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

    bpy.utils.unregister_class(CAMHP_OT_init_motion_cam)

    # UI
    bpy.utils.unregister_class(CAMHP_UL_CameraList)
    bpy.utils.unregister_class(CAMHP_PT_MotionCamPanel)
    # bpy.types.VIEW3D_MT_object_context_menu.remove(draw_context)
