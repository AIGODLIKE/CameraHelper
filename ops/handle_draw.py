import bpy
from bpy.app.handlers import persistent
from bpy.props import PointerProperty, BoolProperty
from bpy.types import PropertyGroup
from bpy.types import SpaceView3D

from .draw_utils.shader import CameraThumb


# 全局


class CameraThumbHandle:
    """Helper class for manage the handle/drawing instance"""
    _inst: CameraThumb = None
    _handle: int = None

    # get the instance of the class
    @property
    def inst(self):
        return self.__class__._inst

    # set the instance of the class
    @inst.setter
    def inst(self, value: CameraThumb):
        self.__class__._inst = value

    @property
    def handle(self):
        return self.__class__._handle

    @handle.setter
    def handle(self, value: int):
        self.__class__._handle = value

    @staticmethod
    def clear_handle():
        if CameraThumbHandle.inst and not bpy.context.window_manager.camhp_pv.pin:
            try:
                SpaceView3D.draw_handler_remove(CameraThumbHandle.handle, 'WINDOW')
            except Exception:
                print("Handle C_HANDLE_CAM_PV already removed")

            CameraThumbHandle.handle = None
            CameraThumbHandle.inst = None

    @staticmethod
    def add_handle(context, depsgraph):
        if CameraThumbHandle.handle is None:
            CameraThumbHandle.inst = CameraThumb(context, depsgraph)
            CameraThumbHandle.handle = SpaceView3D.draw_handler_add(CameraThumbHandle.inst, (context,), 'WINDOW',
                                                                    'POST_PIXEL')


def clear_wrap(self, context):
    CameraThumbHandle.clear_handle()
    if self.enable:
        CameraThumbHandle.add_handle(context, context.evaluated_depsgraph_get())


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
                context.window_manager.camhp_pv.enable = not context.window_manager.camhp_pv.enable

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
        CameraThumbHandle.add_handle(context, depsgraph)
    else:
        CameraThumbHandle.clear_handle()


@persistent
def load_file_clear_handle(noob):
    print('Camera Helper Clear Handle')
    CameraThumbHandle.clear_handle()
    bpy.context.window_manager.camhp_pv.enable = False


class CAMHP_OT_pv_snap_shot(bpy.types.Operator):
    """Snap Shot"""
    bl_idname = "camhp.pv_snap_shot"
    bl_label = "Snap Shot"

    @classmethod
    def poll(cls, context):
        return CameraThumbHandle.inst

    def invoke(self, context, event):
        context.window_manager.camhp_snap_shot_image = True
        return self.execute(context)

    def execute(self, context):
        self.width = CameraThumbHandle.inst.width
        self.height = CameraThumbHandle.inst.height

        cam = CameraThumbHandle.inst.cam
        buffer = CameraThumbHandle.inst.buffer

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
    bpy.app.handlers.load_pre.append(load_file_clear_handle)


def unregister():
    # bpy.app.handlers.depsgraph_update_post.remove(draw_handle)
    bpy.app.handlers.load_pre.remove(load_file_clear_handle)

    # del bpy.types.Scene.camhp_pv
    del bpy.types.WindowManager.camhp_pv
    del bpy.types.WindowManager.camhp_snap_shot_image
    # del bpy.types.window_manager.camhp_snap_shot_image

    bpy.utils.unregister_class(CAMHP_PT_pop_cam_pv_panel)
    bpy.utils.unregister_class(CAMHP_OT_pv_snap_shot)
    bpy.utils.unregister_class(CAMHP_OT_campv_popup)
    bpy.utils.unregister_class(CameraPV)
