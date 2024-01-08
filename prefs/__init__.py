import threading
from . import data_keymap, preferences
from ..public_path_utils import get_asset_dir, AssetDir


def ensure_asset_library_exists(lock, passedSleepTime):
    import time
    import bpy

    # check if not background mode
    if bpy.app.background: return

    while not hasattr(bpy.context, 'preferences') or not hasattr(bpy.context,'view_layer'):
        time.sleep(0.5)

    libraries = bpy.context.preferences.filepaths.asset_libraries
    asset_dir = str(get_asset_dir())

    if 'CameraHelper' not in libraries:
        print('CameraHelper not in libraries')
        bpy.ops.preferences.asset_library_add()
        library = libraries[-1]
        library.name = 'CameraHelper'
        library.path = asset_dir
        bpy.ops.wm.save_userpref()

    for library in libraries:
        if library.name == "CameraHelper" and library.path != asset_dir:
            print('CameraHelper path not correct')
            library.path = asset_dir
            bpy.ops.wm.save_userpref()
            break


def register():
    preferences.register()
    data_keymap.register()

    lock = threading.Lock()
    lock_holder = threading.Thread(target=ensure_asset_library_exists, args=(lock, 5), name='Init_Preferences')
    lock_holder.daemon = True
    lock_holder.start()


def unregister():
    preferences.unregister()
    data_keymap.unregister()
