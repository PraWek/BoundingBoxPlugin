# Bounding Box - CloudCompare Python plugin

Этот скрипт предназначен для использования внутри CloudCompare как Python-плагин

Он автоматически вычисляет:
- AABB - Axis-Aligned Bounding Box
- OBB (PCA) - Oriented Bounding Box на основе PCA
- Minimal OBB - минимальный по объёму ориентированный бокс

... и строит их в виде цветных ccMesh объектов в дереве CloudCompare.

Скрипт полезен для анализа форм облаков точек, сравнения объёмов и визуализации ориентированных параллелепипедов

## Возможности

Извлечение точек из любых ccPointCloud объектов CloudCompare.  
Построение трёх типов bounding box:
- AABB
- OBB (PCA)
- Minimal OBB  

Упорядочивание вершин OBB в корректную структуру (8 углов параллелепипеда).  
Создание параллелепипедов в виде ccMesh (12 треугольников).  
Автоматическое добавление мешей в дерево объектов CC.  
Вывод объёмов всех типов коробок.

## Структура проекта
BoundingBoxPlugin/  
│  
├── [AABB_OBB.py](AABB_OBB.py)  
├── [README.md](README.md)  

## Требования
### Среда
- CloudCompare 2.13+
- Python 3.10
- Open3d 0.19.0
- Включённый Python плагин (PythonPlugin)

### Python-модули
CloudCompare поставляет:
- pycc
- numpy

Необходимо установить вручную:
```commandline
pip install open3d
```
https://www.open3d.org/docs/release/introduction.html#python-quick-start

## Как запустить
### 1. Откройте CloudCompare  
Запустите CloudCompare с поддержкой Python.

### 2. Загрузите облако точек  
Поддерживается любой формат: .las, .laz, .ply, .bin, .xyz, .pcd и т. д.

### 3. Выделите один объект
Скрипт работает только с одним выделенным облаком.

### 4. Запустите Python Script
Modules -> Python Plugin -> Script Register

### 5. Выберите AABB_OBB.py
После запуска в:
- лог выведутся объёмы коробок;
- в дереве объектов появятся три новых ccMesh:
  - AABB_box
  - OBB_PCA_box
  - OBB_Min_box
