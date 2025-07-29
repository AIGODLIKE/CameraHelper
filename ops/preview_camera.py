import bpy


# class CameraThumbHandle:
#     """Helper class for manage the handle/drawing instance"""
#     _inst: CameraThumb = None
#     _handle: int = None
#
#     # get the instance of the class
#     @property
#     def inst(self):
#         return self.__class__._inst
#
#     # set the instance of the class
#     @inst.setter
#     def inst(self, value: CameraThumb):
#         self.__class__._inst = value
#
#     @property
#     def handle(self):
#         return self.__class__._handle
#
#     @handle.setter
#     def handle(self, value: int):
#         self.__class__._handle = value
#
#     @staticmethod
#     def clear_handle():
#         if CameraThumbHandle.inst and not bpy.context.window_manager.camhp_pv.pin:
#             try:
#                 SpaceView3D.draw_handler_remove(CameraThumbHandle.handle, 'WINDOW')
#             except Exception:
#                 print("Handle C_HANDLE_CAM_PV already removed")
#
#             CameraThumbHandle.handle = None
#             CameraThumbHandle.inst = None
#
#     @staticmethod
#     def add_handle(context, depsgraph):
#         if CameraThumbHandle.handle is None:
#             CameraThumbHandle.inst = CameraThumb(context, depsgraph)
#             CameraThumbHandle.handle = SpaceView3D.draw_handler_add(CameraThumbHandle.inst, (context,), 'WINDOW',
#                                                                     'POST_PIXEL')
#
#
# def clear_wrap(self, context):
#     CameraThumbHandle.clear_handle()
#     if self.enable:
#         CameraThumbHandle.add_handle(context, context.evaluated_depsgraph_get())
#
#
# class CameraPV(PropertyGroup):
#     enable: BoolProperty(name="Enable", default=False, options={'HIDDEN'}, update=clear_wrap)
#     pin: BoolProperty(name="Pin Selected Camera", default=False, description='Pin Selected Camera',
#                       update=lambda self, context: setattr(context.window_manager.camhp_pv, 'pin_cam', context.object),
#                       options={'HIDDEN'})
#     pin_cam: PointerProperty(name="Pinned Camera", type=bpy.types.Object, description='Pinned Camera')
#
#     show_overlay: BoolProperty(name="Show Overlay", default=False,
#                                description='Show Overlay', options={'HIDDEN'})

class CAMHP_OT_campv_popup(bpy.types.Operator):
    """Camera Thumbnails\nLeft Click: Enable\nCtrl: Pin Selected Camera\nCtrl Shift Click: Send to Viewer"""
    bl_idname = "camhp.campv_popup"
    bl_label = "Preview"

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'VIEW_3D'

    def invoke(self, context, event):
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

# @persistent
# def draw_handle(scene, depsgraph):
#     context = bpy.context
#
#     if is_select_obj(context):
#         CameraThumbHandle.add_handle(context, depsgraph)
#     else:
#         CameraThumbHandle.clear_handle()
