from . import ops, preferences, res, gizmos

module_list = [
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
