import math

try:
    import pycc
    import cccorelib
except Exception as e:
    raise RuntimeError("Этот скрипт нужно запускать внутри CloudCompare с включённым PythonRuntime") from e

# Пытаемся подключить PyQt5 для вывода диалогов
try:
    from PyQt5 import QtWidgets
    QtAvailable = True
except Exception:
    QtAvailable = False


def ask_inputs_via_qt():
    """
    Запрашивает ввод через стандартные Qt-диалоги.
    Возвращает:
    - center (список из 3 чисел)
    - axis (список из 3 чисел)
    - angle (float)
    - clone (bool)
    """
    parent = None  # при CC.getMainWindow() будет TypeError :/
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    # Центр
    text, ok = QtWidgets.QInputDialog.getText(
        parent,
        "Центр вращения",
        "Введите координаты X Y Z (через пробел):",
        QtWidgets.QLineEdit.Normal,
        "0 0 0"
    )
    if not ok:
        raise SystemExit("Отменено пользователем")
    try:
        center = [float(v) for v in text.strip().split()]
        if len(center) != 3:
            raise ValueError()
    except Exception:
        raise RuntimeError("Неверный формат координат центра.")

    # Ось
    text, ok = QtWidgets.QInputDialog.getText(
        parent,
        "Ось вращения",
        "Введите ось вращения (X Y Z) или X/Y/Z:",
        QtWidgets.QLineEdit.Normal,
        "0 0 1"
    )
    if not ok:
        raise SystemExit("Отменено пользователем")
    s = text.strip().upper()
    if s == "X":
        axis = [1.0, 0.0, 0.0]
    elif s == "Y":
        axis = [0.0, 1.0, 0.0]
    elif s == "Z":
        axis = [0.0, 0.0, 1.0]
    else:
        try:
            axis = [float(v) for v in s.split()]
            if len(axis) != 3:
                raise ValueError()
        except Exception:
            raise RuntimeError("Неверный формат оси вращения.")

    # Угол
    angle, ok = QtWidgets.QInputDialog.getDouble(
        parent,
        "Угол вращения",
        "Введите угол (в градусах):",
        45.0,
        -360.0,
        360.0,
        4
    )
    if not ok:
        raise SystemExit("Отменено пользователем")

    # Режим применения
    res = QtWidgets.QMessageBox.question(
        parent,
        "Режим применения",
        "Применить поворот напрямую к объектам?\n"
        "Если выбрать «Нет», будут созданы копии с поворотом.",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.Yes
    )
    clone = (res == QtWidgets.QMessageBox.No)

    return center, axis, angle, clone


def ask_inputs_console():
    """
    Резервный вариант, если Qt недоступен
    """
    print("Введите координаты центра X Y Z:")
    center = list(map(float, input().strip().split()))
    print("Введите ось вращения (X Y Z) или X/Y/Z:")
    s = input().strip().upper()
    if s == "X":
        axis = [1.0, 0.0, 0.0]
    elif s == "Y":
        axis = [0.0, 1.0, 0.0]
    elif s == "Z":
        axis = [0.0, 0.0, 1.0]
    else:
        axis = list(map(float, s.split()))
    print("Введите угол вращения (в градусах):")
    angle = float(input().strip())
    print("Создать копии вместо изменения оригиналов? (y/n):")
    clone = input().strip().lower().startswith("y")
    return center, axis, angle, clone


def normalize(vec):
    l = math.sqrt(vec[0]**2 + vec[1]**2 + vec[2]**2)
    if l == 0:
        raise RuntimeError("Ось вращения не может быть нулевой.")
    return [v / l for v in vec]


def rotate_entity_around_point(entity, center, axis, angle_deg, clone=False):
    """
    Поворот выбранного объекта вокруг точки center по оси axis на угол angle_deg
    При clone=True создаётся копия объекта
    """
    CC = pycc.GetInstance()

    # Клонирование при необходимости
    if clone:
        new_entity = entity.clone()
        if new_entity is None:
            raise RuntimeError("Не удалось клонировать объект.")
        CC.addToDB(new_entity)
        target = new_entity
    else:
        target = entity

    # Перевод центра вращения в тип CCVector3
    center_vec = cccorelib.CCVector3(center[0], center[1], center[2])
    axis_vec = cccorelib.CCVector3(axis[0], axis[1], axis[2])

    # 1. Перенос объекта так, чтобы центр оказался в начале координат
    mat = target.getGLTransformation()
    translation = mat.getTranslationAsVec3D()
    translation = translation - center_vec
    mat.setTranslation(translation)
    target.setGLTransformation(mat)
    target.applyGLTransformation_recursive()

    # 2. Поворот вокруг оси
    rot = pycc.ccGLMatrix()
    rot.initFromParameters(math.radians(angle_deg), axis_vec, cccorelib.CCVector3(0.0, 0.0, 0.0))
    mat = target.getGLTransformation()
    mat = mat * rot

    # 3. Обратный перенос
    translation = mat.getTranslationAsVec3D()
    translation = translation + center_vec
    mat.setTranslation(translation)
    target.setGLTransformation(mat)
    target.applyGLTransformation_recursive()


def main():
    CC = pycc.GetInstance()

    # Получаем ввод
    if QtAvailable:
        center, axis, angle, clone = ask_inputs_via_qt()
    else:
        center, axis, angle, clone = ask_inputs_console()

    axis = normalize(axis)

    # Получаем выбранные объекты
    selected = CC.getSelectedEntities()
    if not selected:
        raise RuntimeError("Нет выбранных объектов. Выберите хотя бы один в дереве DB.")

    # Применяем к каждому объекту
    for ent in selected:
        rotate_entity_around_point(ent, center, axis, angle, clone=clone)

    CC.redrawAll()
    print(f"Поворот выполнен. Обработано объектов: {len(selected)}")


if __name__ == "__main__":
    main()
