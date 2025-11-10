from __future__ import annotations
from typing import List, Tuple, Optional, Any

import numpy as np

try:
    import pycc
except Exception as e:
    print("ОШИБКА: не найден модуль pycc:", e)
    raise

try:
    import open3d as o3d
except Exception:
    print("ОШИБКА: не найден модуль open3d")
    raise


# Глобальный экземпляр CloudCompare API
CC = pycc.GetInstance()


def get_selected_entity() -> List[Any]:
    """Возвращает список выделенных объектов в CloudCompare"""
    try:
        return CC.getSelectedEntities()
    except Exception:
        return []


def extract_numpy_points(entity: Any) -> np.ndarray:
    """
    Извлекает массив координат точек CloudCompare (Nx3, float64)

    Поддерживает разные структуры CC:
    - e.points()
    - e.toNpArrayCopy()
    - e.toNpArray()
    - e.getCoords()
    - e.asArray()
    """
    candidates = [
        ("points()", lambda e: e.points()),
        ("toNpArrayCopy()", lambda e: e.toNpArrayCopy()),
        ("toNpArray()", lambda e: e.toNpArray()),
        ("getCoords()", lambda e: e.getCoords()),
        ("asArray()", lambda e: getattr(e, "asArray", lambda: None)()),
    ]

    last_err: Optional[Exception] = None

    for name, fn in candidates:
        try:
            pts = fn(entity)
            if pts is None:
                continue

            arr = np.asarray(pts)

            # Возможная форма (N*3,) → (N,3)
            if arr.ndim == 1 and arr.size % 3 == 0:
                arr = arr.reshape((-1, 3))

            if arr.ndim == 2 and arr.shape[1] == 3:
                return arr.astype(np.float64)
        except Exception as ex:
            last_err = ex
            continue

    # Пробуем через associated cloud
    try:
        assoc = entity.getAssociatedCloud()
        arr = np.asarray(assoc.points())
        if arr.ndim == 2 and arr.shape[1] == 3:
            return arr.astype(np.float64)
    except Exception:
        pass

    raise RuntimeError(
        f"Невозможно извлечь координаты точек. Последняя ошибка: {last_err}"
    )


def o3d_from_numpy(pts: np.ndarray) -> o3d.geometry.PointCloud:
    """Создаёт PointCloud Open3D из numpy-матрицы Nx3"""
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts)
    return pcd


def reorder_obb_corners(corners: np.ndarray) -> np.ndarray:
    """
    Приводит 8 вершин OBB к согласованному порядку

    Алгоритм:
    - выбираем первую вершину p0
    - находим две ближайшие (основание)
    - находим третью ось через максимальную проекцию на нормаль
    - формируем локальную систему координат
    - переносим точки в структуру {min,max} по каждой оси
    """
    corners = np.asarray(corners, dtype=np.float64)
    p0 = corners[0]

    d2 = np.sum((corners - p0) ** 2, axis=1)
    nearest = np.argsort(d2)[1:3]

    p1, p2 = corners[nearest]
    v1, v2 = p1 - p0, p2 - p0

    # Нормаль
    normal = np.cross(v1, v2)
    n_norm = np.linalg.norm(normal)
    normal = normal / n_norm if n_norm > 0 else np.array([0.0, 0.0, 1.0])

    # Ищем вершину, максимально коллинеарную нормали
    best_i = max(
        range(1, 8),
        key=lambda i: abs(np.dot(corners[i] - p0, normal)),
    )
    v3 = corners[best_i] - p0

    e1 = v1 / np.linalg.norm(v1)
    e2 = v2 / np.linalg.norm(v2)
    e3 = v3 / np.linalg.norm(v3)

    M = np.column_stack((e1, e2, e3))
    local = (corners - p0) @ np.linalg.inv(M)

    mins = np.min(local, axis=0)
    maxs = np.max(local, axis=0)

    ordered_local = np.array([
        [mins[0], mins[1], mins[2]],
        [maxs[0], mins[1], mins[2]],
        [mins[0], maxs[1], mins[2]],
        [maxs[0], maxs[1], mins[2]],
        [mins[0], mins[1], maxs[2]],
        [maxs[0], mins[1], maxs[2]],
        [mins[0], maxs[1], maxs[2]],
        [maxs[0], maxs[1], maxs[2]],
    ])

    return ordered_local @ M + p0


def add_box_mesh_to_cc(
    name: str,
    vertices_np: np.ndarray,
    rgb: Tuple[int, int, int],
) -> pycc.ccMesh:
    """
    Создаёт параллелепипед в CloudCompare по 8 упорядоченным вершинам
    Цвет задаётся в виде (R,G,B)
    """
    TRI = np.array([
        [0, 1, 2], [1, 3, 2],
        [4, 6, 5], [5, 6, 7],
        [0, 4, 1], [1, 4, 5],
        [2, 3, 6], [3, 7, 6],
        [0, 2, 4], [2, 6, 4],
        [1, 5, 3], [3, 5, 7],
    ], dtype=np.int32)

    xs = vertices_np[:, 0].astype(pycc.PointCoordinateType)
    ys = vertices_np[:, 1].astype(pycc.PointCoordinateType)
    zs = vertices_np[:, 2].astype(pycc.PointCoordinateType)

    verts = pycc.ccPointCloud(xs, ys, zs)
    verts.setName(f"{name}_verts")

    mesh = pycc.ccMesh(verts)
    mesh.setName(name)

    for t in TRI:
        mesh.addTriangle(int(t[0]), int(t[1]), int(t[2]))

    # Цвет вершин
    try:
        color_arr = np.tile(
            np.array(rgb, dtype=np.uint8)[None, :],
            (8, 1)
        )
        verts.setColors(color_arr)
        verts.showColors(True)
    except Exception:
        pass

    CC.addToDB(mesh)
    CC.updateUI()
    return mesh


def compute_bboxes(entity: Any) -> None:
    """Вычисляет AABB, OBB(PCA), OBB(min) и добавляет их в CloudCompare"""
    pts = extract_numpy_points(entity)
    if pts.shape[0] < 3:
        print("Слишком мало точек для вычисления")
        return

    pcd = o3d_from_numpy(pts)

    aabb = pcd.get_axis_aligned_bounding_box()
    obb_pca = o3d.geometry.OrientedBoundingBox.create_from_points(pcd.points)

    try:
        obb_min = o3d.geometry.OrientedBoundingBox.create_from_points_minimal(
            pcd.points
        )
    except Exception:
        obb_min = obb_pca

    # Вывод объёмов
    print("\nОбъёмы параллелепипедов:")
    print("AABB:        ", aabb.volume())
    print("OBB (PCA):   ", obb_pca.volume())
    print("OBB (min):   ", obb_min.volume(), "\n")

    def ordered(obb: o3d.geometry.OrientedBoundingBox) -> np.ndarray:
        return reorder_obb_corners(np.asarray(obb.get_box_points()))

    aabb_conv = o3d.geometry.OrientedBoundingBox.create_from_axis_aligned_bounding_box(aabb)

    add_box_mesh_to_cc("AABB_box", ordered(aabb_conv), (255, 0, 0))
    add_box_mesh_to_cc("OBB_PCA_box", ordered(obb_pca), (0, 255, 0))
    add_box_mesh_to_cc("OBB_Min_box", ordered(obb_min), (0, 0, 255))

    print("Боксы добавлены в дерево объектов CloudCompare")


def main() -> None:
    """Точка входа - обработка выделенного облака"""
    sel = get_selected_entity()
    if not sel:
        print("Нет выделенных объектов. Выделите облако точек")
        return

    ent = sel[0]
    name = ent.getName() if hasattr(ent, "getName") else "<без имени>"
    print(f"Выбрана сущность: {name}")

    compute_bboxes(ent)


if __name__ == "__main__":
    main()
