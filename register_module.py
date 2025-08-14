from . import ops, preferences, res, gizmos, ui, update

module_list = [
    ui,
    res,
    ops,
    update,
    gizmos,
    preferences,
]


def register():
    for mod in module_list:
        mod.register()


def unregister():
    for mod in module_list:
        mod.unregister()
