bl_info = {
    "curve_name": "Camera Helper",
    "author": "幻之境科技 (开发:Atticus)",
    "blender": (3, 2, 0),
    "version": (0, 1),
    "category": "Camera",
    "support": "COMMUNITY",
    "doc_url": "",
    "tracker_url": "",
    "description": "",
    "location": "3D视图右侧控件栏/进入相机视图",
}

__ADDON_NAME__ = __name__

from . import ops, gz, localdb


def register():
    ops.register()
    gz.register()
    localdb.register()


def unregister():
    ops.unregister()
    gz.unregister()
    localdb.unregister()


if __name__ == '__main__':
    register()
