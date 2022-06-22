from . import data_keymap,preferences


def register():
    preferences.register()
    data_keymap.register()


def unregister():
    preferences.unregister()
    data_keymap.unregister()
