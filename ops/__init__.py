from . import op_cam, op_motion_cam, handle_draw


def register():
    op_cam.register()
    op_motion_cam.register()
    handle_draw.register()


def unregister():
    handle_draw.unregister()
    op_cam.unregister()
    op_motion_cam.unregister()
