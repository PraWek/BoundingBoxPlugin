from __future__ import annotations

# Попробуем импортировать обёртки CloudCompare
RUNTIME = None
CC = None

try:
    import cloudComPy as cc  # type: ignore
    RUNTIME = 'cloudComPy'
    CC = cc
except Exception:
    try:
        import pycc  # type: ignore
        RUNTIME = 'pycc'
        CC = pycc.GetInstance()
    except Exception:
        CC = None


def friendly_name(entity) -> str:
    try:
        return entity.getName()
    except Exception:
        try:
            return str(entity)
        except Exception:
            return '<безымянный объект>'


def count_points_in_entity(entity) -> int | None:
    """Попытка разными способами получить количество точек в объекте."""
    try:
        if hasattr(entity, 'size'):
            val = entity.size()
            if isinstance(val, int):
                return val
    except Exception:
        pass

    for name in ('getNumberOfPoints', 'getNbPoints', 'n_points', 'nbPoints'):
        try:
            if hasattr(entity, name):
                fn = getattr(entity, name)
                val = fn() if callable(fn) else fn
                if isinstance(val, int):
                    return val
        except Exception:
            continue

    try:
        if hasattr(entity, 'toNpArray'):
            arr = entity.toNpArray()
            import numpy as _np
            if isinstance(arr, _np.ndarray):
                return int(arr.shape[0])
    except Exception:
        pass

    return None


def get_selected_entities() -> list:
    """Получить список выделенных объектов в CloudCompare."""
    if RUNTIME == 'cloudComPy':
        if hasattr(CC, 'getSelectedEntities'):
            return CC.getSelectedEntities()
        if hasattr(CC, 'getLoadedEntities'):
            return CC.getLoadedEntities()
        raise RuntimeError('cloudComPy найден, но API для выделения отсутствует')

    if RUNTIME == 'pycc':
        if hasattr(CC, 'getSelectedEntities'):
            return CC.getSelectedEntities()
        if hasattr(CC, 'GetSelectedEntities'):
            return CC.GetSelectedEntities()
        raise RuntimeError('pycc найден, но метод getSelectedEntities() отсутствует')

    raise RuntimeError('Не найдено поддерживаемое Python-окружение CloudCompare (cloudComPy/pycc)')


def show_message(title: str, text: str) -> None:
    """Показать сообщение через Qt (если доступно) или вывести в консоль."""
    try:
        from PySide2.QtWidgets import QMessageBox, QApplication  # type: ignore
        app = QApplication.instance() or QApplication([])
        QMessageBox.information(None, title, text)
    except Exception:
        try:
            from PyQt5.QtWidgets import QMessageBox, QApplication  # type: ignore
            app = QApplication.instance() or QApplication([])
            QMessageBox.information(None, title, text)
        except Exception:
            print(title)
            print(text)


def main():
    try:
        entities = get_selected_entities()
    except Exception as e:
        show_message('Ошибка подсчёта точек', f'Не удалось получить выделение: {e}')
        return

    if not entities:
        show_message('Подсчёт точек', 'Нет выделенных объектов. Выберите одно или несколько облаков точек и повторите.')
        return

    lines = []
    total = 0
    for ent in entities:
        try:
            n = count_points_in_entity(ent)
            name = friendly_name(ent)
            if n is None:
                lines.append(f"{name}: (не облако точек / неизвестно)")
            else:
                lines.append(f"{name}: {n} точек")
                total += n
        except Exception as exc:
            lines.append(f"{friendly_name(ent)}: ошибка ({exc})")

    if len(lines) > 1:
        lines.append(f"\nВсего: {total} точек")
    text = '\n'.join(lines)

    show_message('Подсчёт точек', text)
    print('--- Результат работы плагина ---')
    print(text)


if __name__ == '__main__':
    main()
