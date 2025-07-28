from . import ops, preferences, res

module_list = [
    res,
    ops,
    preferences,
]


def register():
    for mod in module_list:
        mod.register()


def unregister():
    for mod in module_list:
        mod.unregister()
