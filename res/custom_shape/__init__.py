from pathlib import Path

import bmesh
import bpy
import numpy as np

def load_shape_geo_obj(obj_name='ROTATE'):
    """ 加载一个几何形状的模型，用于绘制几何形状的控件 """
    gz_shape_path = Path(__file__).parent.joinpath('gz_shape.blend')
    with bpy.data.libraries.load(str(gz_shape_path)) as (data_from, data_to):
        data_to.objects = [obj_name]
    return data_to.objects[0]


def create_geo_shape(obj=None, shape_type='TRIS', scale=1):
    """ 创建一个几何形状，默认创造球体
    """
    if obj:
        tmp_mesh = obj.data
    else:
        tmp_mesh = bpy.data.meshes.new('tmp')
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=scale / 5, calc_uvs=True)
        bm.to_mesh(tmp_mesh)
        bm.free()

    mesh = tmp_mesh
    vertices = np.zeros((len(mesh.vertices), 3), 'f')
    mesh.vertices.foreach_get("co", vertices.ravel())
    mesh.calc_loop_triangles()

    if shape_type == 'LINES':
        edges = np.zeros((len(mesh.edges), 2), 'i')
        mesh.edges.foreach_get("vertices", edges.ravel())
        custom_shape_verts = vertices[edges].reshape(-1, 3)
    else:
        tris = np.zeros((len(mesh.loop_triangles), 3), 'i')
        mesh.loop_triangles.foreach_get("vertices", tris.ravel())
        custom_shape_verts = vertices[tris].reshape(-1, 3)

    bpy.data.meshes.remove(mesh)

    return custom_shape_verts
