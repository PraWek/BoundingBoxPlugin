import numpy as np

try:
    import pycc
except Exception as e:
    print("ERROR: не найден модуль pycc", e)
    raise

try:
    import open3d as o3d
except Exception as e:
    print("ERROR: не найден модуль open3d")
    raise

CC = pycc.GetInstance()


def get_selected_entity():
    """
    Возвращает список выбранных сущностей (или [] если нет)
    """
    try:
        sel = CC.getSelectedEntities()
        return sel
    except Exception:
        try:
            sel = CC.getSelection()
            return sel
        except Exception:
            return []

def extract_numpy_points(cc_entity):
    """
    Попытки получить numpy array Nx3 координат из объекта CloudCompare.
    Поддерживаем несколько возможных имён/методов:
      - entity.points()
      - entity.toNpArrayCopy()
      - entity.toNpArray()
      - entity.getCoords()
    Возвращает numpy array float64 shape (N,3)
    """
    candidates = [
        ("points()", lambda e: e.points()),
        ("toNpArrayCopy()", lambda e: e.toNpArrayCopy()),
        ("toNpArray()", lambda e: e.toNpArray()),
        ("getCoords()", lambda e: e.getCoords()),
        ("asArray()", lambda e: getattr(e, "asArray", lambda: None)()),
    ]

    last_err = None
    for name, fn in candidates:
        try:
            pts = fn(cc_entity)
            if pts is None:
                continue
            pts = np.asarray(pts)
            if pts.ndim == 1 and pts.size % 3 == 0:
                pts = pts.reshape((-1, 3))
            if pts.ndim == 2 and pts.shape[1] == 3:
                return pts.astype(np.float64)
        except Exception as ex:
            last_err = ex
            # пробуем следующий метод
            continue

    # если ничего не сработало, попробуем получить associated cloud
    try:
        assoc = cc_entity.getAssociatedCloud()
        pts = np.asarray(assoc.points())
        if pts.ndim == 2 and pts.shape[1] == 3:
            return pts.astype(np.float64)
    except Exception:
        pass

    raise RuntimeError("Не удалось извлечь координаты из объекта CloudCompare. Последняя ошибка: {}".format(last_err))


def o3d_from_numpy(pts_np):
    """Создает Open3D PointCloud из numpy Nx3"""
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts_np)
    return pcd


def add_box_mesh_to_cc(name, vertices_np, color_rgb):
    """
    Создает ccPointCloud + ccMesh из переданных вершин (8x3) и индексов куба,
    добавляет mesh в CloudCompare DB
    vertices_np: (8,3) numpy
    color_rgb: (r,g,b) 0..255
    """
    # Индексы треугольников куба (12 треугольников)
    TRIANGLES = np.array([
        [0,1,2],[1,3,2],  # -X face
        [4,6,5],[5,6,7],  # +X face
        [0,4,1],[1,4,5],  # -Y face
        [2,3,6],[3,7,6],  # +Y face
        [0,2,4],[2,6,4],  # -Z face
        [1,5,3],[3,5,7],  # +Z face
    ], dtype=np.int32)

    xs = vertices_np[:,0].astype(pycc.PointCoordinateType)
    ys = vertices_np[:,1].astype(pycc.PointCoordinateType)
    zs = vertices_np[:,2].astype(pycc.PointCoordinateType)

    verts = pycc.ccPointCloud(xs, ys, zs)
    verts.setName(f"{name}_verts")

    mesh = pycc.ccMesh(verts)
    for tri in TRIANGLES:
        mesh.addTriangle(int(tri[0]), int(tri[1]), int(tri[2]))

    mesh.setName(name)

    try:
        rgb_arr = np.tile(np.array(color_rgb, dtype=np.uint8)[None, :], (vertices_np.shape[0], 1))
        verts.setColors(rgb_arr)
        verts.showColors(True)
    except Exception:
        pass

    CC.addToDB(mesh)
    CC.updateUI()
    return mesh


def compute_and_add_bboxes(cc_entity):
    pts = extract_numpy_points(cc_entity)
    if pts.shape[0] < 3:
        print("Недостаточно точек (<3) для вычислений")
        return

    pcd = o3d_from_numpy(pts)

    # AABB
    aabb = pcd.get_axis_aligned_bounding_box()

    # OBB PCA
    obb_pca = o3d.geometry.OrientedBoundingBox.create_from_points(pcd.points)

    # Min OBB (точный)
    try:
        obb_min = o3d.geometry.OrientedBoundingBox.create_from_points_minimal(pcd.points)
    except Exception:
        obb_min = obb_pca

    print("Bounding boxes volumes")
    try:
        print("AABB volume:        {:.6f}".format(aabb.volume()))
    except Exception:
        print("AABB volume: (н/д)")
    try:
        print("OBB (PCA) volume:   {:.6f}".format(obb_pca.volume()))
    except Exception:
        print("OBB (PCA) volume: (н/д)")
    try:
        print("OBB (minimal) vol.: {:.6f}".format(obb_min.volume()))
    except Exception:
        print("OBB (minimal) vol: (н/д)")


    # Получим 8 вершин каждого бокса (Open3D -> numpy)
    def obb_corners(obb):
        # open3d.geometry.OrientedBoundingBox.get_box_points()
        pts8 = np.asarray(obb.get_box_points())  # shape (8,3)
        return pts8


    aabb_obb = o3d.geometry.OrientedBoundingBox.create_from_axis_aligned_bounding_box(aabb)

    aabb_pts = obb_corners(aabb_obb)
    obb_pca_pts = obb_corners(obb_pca)
    obb_min_pts = obb_corners(obb_min)

    mesh_aabb = add_box_mesh_to_cc("AABB_box", aabb_pts, (255, 0, 0))
    mesh_obb_pca = add_box_mesh_to_cc("OBB_PCA_box", obb_pca_pts, (0, 255, 0))
    mesh_obb_min = add_box_mesh_to_cc("OBB_Min_box", obb_min_pts, (0, 0, 255))

    print("Добавлены меши: AABB_box, OBB_PCA_box, OBB_Min_box")


def main():
    sel = get_selected_entity()
    if not sel:
        print("Не выбрано ни одной сущности в CloudCompare. Выдели облако и запусти скрипт снова")
        return

    entity = sel[0]
    print("Выбрана сущность:", getattr(entity, "getName", lambda: str(entity))())
    try:
        compute_and_add_bboxes(entity)
    except Exception as e:
        print("Ошибка при вычислениях или добавлении боксов", e)
        raise


if __name__ == "__main__":
    main()
