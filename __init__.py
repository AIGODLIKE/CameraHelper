bl_info = {
    "name": "Camera Helper",
    "author": "AIGODLIKE社区, Atticus, 小萌新",
    "blender": (4, 2, 0),
    "version": (1, 4, 1),
    "category": "辣椒出品",
    "support": "COMMUNITY",
    "doc_url": "",
    "tracker_url": "",
    "description": "",
    "location": "3D视图右侧控件栏/进入相机视图",
}

from . import register_module


def register():
    register_module.register()


def unregister():
    register_module.unregister()
