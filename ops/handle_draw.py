import bpy
import gpu
from bpy.app.handlers import persistent
from bpy.types import SpaceView3D
from .draw_utils.shader import CameraMotionPath, CameraThumb
from bpy.types import PropertyGroup
from bpy.props import PointerProperty, BoolProperty, EnumProperty

# 全局
G_HANDLE_CURVE = None
G_HANDLE_CAM_PV = None

G_INST_CURVE = None
G_INST_CAM_PV = None


def clear_handle():
    global G_HANDLE_CURVE, G_HANDLE_CAM_PV
    global G_INST_CURVE, G_INST_CAM_PV

    if G_INST_CURVE:
        try:
            SpaceView3D.draw_handler_remove(G_HANDLE_CURVE, 'WINDOW')
        except Exception:
            print("Handle C_HANDLE_CURVE already removed")

        G_HANDLE_CURVE = None
        G_INST_CURVE = None

    if G_INST_CAM_PV and not bpy.context.window_manager.camhp_pv.pin:
        try:
            SpaceView3D.draw_handler_remove(G_HANDLE_CAM_PV, 'WINDOW')
        except Exception:
            print("Handle C_HANDLE_CAM_PV already removed")

        G_HANDLE_CAM_PV = None
        G_INST_CAM_PV = None


def add_handle(context, depsgraph):
    global G_HANDLE_CURVE, G_HANDLE_CAM_PV
    global G_INST_CURVE, G_INST_CAM_PV

    if G_HANDLE_CURVE is None:
        G_INST_CURVE = CameraMotionPath(context, depsgraph)
        G_HANDLE_CURVE = SpaceView3D.draw_handler_add(G_INST_CURVE, (context,), 'WINDOW', 'POST_VIEW')

    if G_HANDLE_CAM_PV is None:
        G_INST_CAM_PV = CameraThumb(context, depsgraph)
        G_HANDLE_CAM_PV = SpaceView3D.draw_handler_add(G_INST_CAM_PV, (context,), 'WINDOW', 'POST_PIXEL')


def clear_wrap(self, context):
    if not self.enable:
        clear_handle()


class CameraPV(PropertyGroup):
    enable: BoolProperty(name="Enable", default=False, options={'HIDDEN'}, update=clear_wrap)
    pin: BoolProperty(name="Pin Selected Camera", default=False, description='Pin Selected Camera',
                      update=lambda self, context: setattr(context.window_manager.camhp_pv, 'pin_cam', context.object),
                      options={'HIDDEN'})
    pin_cam: PointerProperty(name="Pinned Camera", type=bpy.types.Object, description='Pinned Camera')

    show_overlay: BoolProperty(name="Show Overlay", default=False,
                               description='Show Overlay', options={'HIDDEN'})


class pop_cam_panel(bpy.types.Panel):
    """Properties"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'


class CAMHP_PT_pop_cam_pv_panel(pop_cam_panel):
    bl_label = "Preview"
    bl_idname = 'CAMHP_PT_pop_cam_pv_panel'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.active = context.window_manager.camhp_pv.enable
        layout.prop(context.window_manager.camhp_pv, 'enable')
        layout.prop(context.window_manager.camhp_pv, 'pin')
        layout.operator('camhp.pv_snap_shot')
        # layout.prop(context.window_manager.camhp_pv, 'show_overlay')


class CAMHP_OT_campv_popup(bpy.types.Operator):
    """Camera Thumbnails\nLeft Click: Enable\nCtrl: Pin Selected Camera\nCtrl Shift Click: Send to Viewer"""
    bl_idname = "camhp.campv_popup"
    bl_label = "Preview"

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'VIEW_3D'

    def invoke(self, context, event):
        # print(event.type, event.value)
        #
        # def pop_up(cls, context):
        #     layout = cls.layout
        #     layout.popover("CAMHP_PT_pop_cam_pv_panel")

        if event.type == 'LEFTMOUSE':
            if event.ctrl and not event.shift:
                context.window_manager.camhp_pv.pin = False if context.window_manager.camhp_pv.pin else True
            elif event.shift and event.ctrl:
                bpy.ops.camhp.pv_snap_shot()
            else:
                context.window_manager.camhp_pv.enable = False if context.window_manager.camhp_pv.enable else True

        context.area.tag_redraw()

        return {'INTERFACE'}


def is_select_obj(context):
    return (
            context and
            hasattr(context, 'object') and
            context.object and
            context.object.type in {'CAMERA', 'EMPTY'}
    )


@persistent
def draw_handle(scene, depsgraph):
    context = bpy.context

    if is_select_obj(context):
        add_handle(context, depsgraph)
    else:
        clear_handle()


@persistent
def load_file_clear_handle(noob):
    print('Camera Helper Clear Handle')
    clear_handle()
    bpy.context.window_manager.camhp_pv.enable = False


class CAMHP_OT_pv_snap_shot(bpy.types.Operator):
    """Snap Shot"""
    bl_idname = "camhp.pv_snap_shot"
    bl_label = "Snap Shot"

    @classmethod
    def poll(cls, context):
        return G_INST_CAM_PV

    def invoke(self, context, event):
        context.window_manager.camhp_snap_shot_image = True
        return self.execute(context)

    def execute(self, context):
        self.width = G_INST_CAM_PV.width
        self.height = G_INST_CAM_PV.height

        cam = G_INST_CAM_PV.cam
        buffer = G_INST_CAM_PV.buffer

        if f'_SnapShot_{cam.name}' in bpy.data.images:
            img = bpy.data.images[f'_SnapShot_{cam.name}']
        else:
            img = bpy.data.images.new(name=f'_SnapShot_{cam.name}',
                                      width=self.width,
                                      height=self.height)

        img.scale(self.width, self.height)
        try:
            img.pixels.foreach_set(buffer)
        except TypeError as e:
            print(e)
            return {'CANCELLED'}
        # set resolution
        ori_width = context.scene.render.resolution_x
        ori_height = context.scene.render.resolution_y
        context.scene.render.resolution_x = self.width
        context.scene.render.resolution_y = self.height

        bpy.ops.render.view_show('INVOKE_DEFAULT')
        if context.window.screen.areas[0].type == 'IMAGE_EDITOR':
            # set img as area active image
            context.window.screen.areas[0].spaces[0].image = img

        # restore
        context.scene.render.resolution_x = ori_width
        context.scene.render.resolution_y = ori_height

        context.window_manager.camhp_snap_shot_image = False
        self.report({'INFO'}, f'Snap Shot')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(CameraPV)
    bpy.utils.register_class(CAMHP_PT_pop_cam_pv_panel)
    bpy.utils.register_class(CAMHP_OT_campv_popup)
    bpy.utils.register_class(CAMHP_OT_pv_snap_shot)

    bpy.types.WindowManager.camhp_pv = PointerProperty(type=CameraPV)
    # bpy.types.Scene.camhp_pv = PointerProperty(type=CameraPV)
    # bpy.types.window_manager.camhp_snap_shot_image = BoolProperty(name='Snap Shot', default=False)
    bpy.types.WindowManager.camhp_snap_shot_image = BoolProperty(name='Snap Shot', default=False)

    # bpy.app.handlers.depsgraph_update_post.append(draw_handle)
    # bpy.app.handlers.load_pre.append(load_file_clear_handle)


def unregister():
    # clear_handle()
    # bpy.app.handlers.depsgraph_update_post.remove(draw_handle)
    # bpy.app.handlers.load_pre.remove(load_file_clear_handle)

    # del bpy.types.Scene.camhp_pv
    del bpy.types.WindowManager.camhp_pv
    del bpy.types.WindowManager.camhp_snap_shot_image
    # del bpy.types.window_manager.camhp_snap_shot_image

    bpy.utils.unregister_class(CAMHP_PT_pop_cam_pv_panel)
    bpy.utils.unregister_class(CAMHP_OT_pv_snap_shot)
    bpy.utils.unregister_class(CAMHP_OT_campv_popup)
    bpy.utils.unregister_class(CameraPV)
