from . import op_cam, op_motion_cam


def register():
    op_cam.register()
    op_motion_cam.register()


def unregister():
    op_cam.unregister()
    op_motion_cam.unregister()
