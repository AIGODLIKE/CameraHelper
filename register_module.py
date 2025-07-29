from . import ops, preferences, res, gizmos,ui

module_list = [
    ui,
    res,
    ops,
    gizmos,
    preferences,
]


def register():
    for mod in module_list:
        mod.register()


def unregister():
    for mod in module_list:
        mod.unregister()
