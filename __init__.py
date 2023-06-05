bl_info = {
    "name": "Camera Helper",
    "author": "AIGODLIKE社区,Atticus",
    "blender": (3, 4, 0),
    "version": (1, 1, 4),
    "category": "辣椒出品",
    "support": "COMMUNITY",
    "doc_url": "",
    "tracker_url": "",
    "description": "",
    "location": "3D视图右侧控件栏/进入相机视图",
}

__ADDON_NAME__ = __name__

from . import prefs, ops, gz, localdb


def register():
    ops.register()
    prefs.register()
    gz.register()
    localdb.register()


def unregister():
    ops.unregister()
    prefs.unregister()
    gz.unregister()
    localdb.unregister()


if __name__ == '__main__':
    register()
