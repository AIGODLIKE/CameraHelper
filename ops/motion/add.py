import bpy

from ..old.draw_utils.bl_ui_draw_op import BL_UI_OT_draw_operator
from ..old.draw_utils.bl_ui_drag_panel import BL_UI_Drag_Panel
from ..old.draw_utils.bl_ui_label import BL_UI_Label
from bpy.app.translations import pgettext_iface as tip_
from ...utils.asset import AssetDir, get_asset_dir

class CAMHP_PT_add_motion_cams(BL_UI_OT_draw_operator, bpy.types.Operator):
    bl_idname = 'camhp.add_motion_cams'
    bl_label = 'Add Motion Camera'
    bl_options = {'UNDO_GROUPED', 'INTERNAL', 'BLOCKING', 'GRAB_CURSOR'}

    buttons = list()
    controller = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buttons.clear()

        # 面板提示
        self.panel = BL_UI_Drag_Panel(100, 300, 300, 290)
        self.panel.bg_color = 0.2, 0.2, 0.2, 0.9

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

            loc = get_obj_2d_loc(obj, bpy.context)
            if loc is None: continue  # 相机处于较远的位置
            x, y = loc

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

    def cancel(self, context):
        if getattr(self, 'new_cam', None) is not None:
            bpy.data.objects.remove(self.new_cam)
        if getattr(self, 'cam', None) is not None:
            bpy.data.objects.remove(self.controller)
        return {'CANCELLED'}

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
        cam_obj = bpy.data.objects.new('Camera', cam_data)

        if bpy.app.version >= (4, 3, 0):
            asset_motioncam = get_asset_dir(AssetDir.ASSET_BLEND_WITH_GIZMO.value)
        else:
            asset_motioncam = get_asset_dir(AssetDir.ASSET_BLEND.value)
        controller_obj = load_asset(name='Controller', asset_type='objects', filepath=str(asset_motioncam))
        asset_motion_src = load_asset(name='MotionCameraSource', asset_type='node_groups',
                                      filepath=str(asset_motioncam))
        asset_motion_gen = load_asset(name='MotionCamera', asset_type='node_groups',
                                      filepath=str(asset_motioncam))

        context.collection.objects.link(cam_obj)
        context.collection.objects.link(controller_obj)
        # 设置
        cam_obj.data.show_name = True
        cam_obj.name = 'Motion Camera'
        # deselect all
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = controller_obj
        controller_obj.select_set(True)
        cam_obj.select_set(True)
        # toggle edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.object.vertex_parent_set()
        bpy.ops.object.mode_set(mode='OBJECT')

        self.controller = controller_obj
        self.new_cam = cam_obj
        self.ng_motion_src = asset_motion_src
        self.ng_motion_gen = asset_motion_gen

    def add_motion_cam(self, obj):
        bpy.context.view_layer.objects.active = self.controller
        self.controller.select_set(True)

        if 'MotionCamera' not in self.controller.modifiers:
            mod_gen = self.controller.modifiers.new(type='NODES', name='MotionCamera')
            mod_gen.node_group = self.ng_motion_gen
            mod_gen.show_group_selector = False

        mod = self.controller.modifiers.new(type='NODES', name='MotionCameraSource')
        mod.node_group = self.ng_motion_src
        mod.show_group_selector = False

        # set value
        mod['Socket_2'] = obj
        mod.show_viewport = False
        mod.show_viewport = True
        # move to bottom
        for i, m in enumerate(self.controller.modifiers):
            if m.name == 'MotionCamera':
                self.controller.modifiers.move(i, len(self.controller.modifiers) - 1)
                self.controller.modifiers.active = m
                break
        bpy.context.area.tag_redraw()

    def modal(self, context, event):

        for i, btn in enumerate(self.buttons):
            if not hasattr(btn, 'bind_obj'): continue

            obj_name = getattr(btn, 'bind_obj')
            obj = bpy.data.objects.get(obj_name)

            if obj is None: continue
            x, y = get_obj_2d_loc(obj, context)
            btn.update(x, y)
            context.area.tag_redraw()

        return super().modal(context, event)
