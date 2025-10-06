"""
Вспомогательная функция тестирования: генерация прсотого облака точек (куб 3x3x3)
"""

import pycc
import numpy as np


def create_simple_point_cloud():
    # Создаем массив точек (куб 3x3x3)
    points = []
    for x in range(3):
        for y in range(3):
            for z in range(3):
                points.append([x, y, z])

    # Преобразуем в numpy array
    points_array = np.array(points, dtype=np.float64)

    # Создаем облако точек в CloudCompare
    cloud = pycc.ccPointCloud(points_array[:, 0], points_array[:, 1], points_array[:, 2])
    cloud.setName("Simple Cube Cloud")

    # Добавляем облако в базу данных CloudCompare
    pycc.GetInstance().addToDB(cloud)

    print(f"Создано облако точек с {len(points)} точками")
    return cloud


create_simple_point_cloud()
