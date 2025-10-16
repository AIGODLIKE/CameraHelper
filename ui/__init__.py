from . import camera,menu

def register():
    camera.register()
    menu.register()


def unregister():
    camera.unregister()
    menu.unregister()
