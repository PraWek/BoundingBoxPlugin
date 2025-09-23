import sys
import os

# Путь к модулям CloudCompare
sys.path.append(r'C:\Program Files\CloudCompare\plugins')

try:
    import pycc
    from pycc import cc, CCPlugin
except ImportError:
    print("Ошибка: Не удалось импортировать модули CloudCompare")
    print("Убедитесь, что CloudCompare установлен и пути указаны правильно")


class PointCounter(CCPlugin):
    """Плагин для подсчета количества точек в облаках"""

    def __init__(self):
        super().__init__()
        self.name = "Point Counter"
        self.description = "Подсчитывает количество точек в выбранных облаках"
        self.version = "1.0"

    def getActions(self):
        """Возвращает действия плагина"""
        action = self.createAction(
            name="Count Points",
            iconPath=os.path.join(os.path.dirname(__file__), "icon.png"),  # опционально
            tooltip="Подсчитать количество точек в выбранных облаках",
            menuName="Tools"  # Раздел меню
        )
        action.triggered.connect(self.run)
        return [action]

    def run(self):
        """Основная функция плагина"""
        try:
            # Получаем текущий активный вид
            main_window = pycc.GetMainWindow()
            if not main_window:
                self.showError("Не удалось получить главное окно")
                return

            # Получаем выбранные объекты
            selected_entities = main_window.getSelectedEntities()
            if not selected_entities:
                self.showWarning("Не выбрано ни одного облака точек")
                return

            point_counts = []

            for entity in selected_entities:
                if isinstance(entity, cc.PointCloud):
                    point_count = entity.size()
                    point_counts.append((entity.getName(), point_count))

                    # Выводим информацию в консоль
                    print(f"Облако '{entity.getName()}': {point_count:,} точек")

            if point_counts:
                # Создаем диалог с результатами
                self.showResultsDialog(point_counts)
            else:
                self.showWarning("Среди выбранных объектов нет облаков точек")

        except Exception as e:
            self.showError(f"Ошибка выполнения: {str(e)}")

    def showResultsDialog(self, point_counts):
        """Показывает диалог с результатами"""
        try:
            from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                         QLabel, QTableWidget, QTableWidgetItem,
                                         QPushButton, QHeaderView)
            from PyQt5.QtCore import Qt

            dialog = QDialog(pycc.GetMainWindow())
            dialog.setWindowTitle("Результаты подсчета точек")
            dialog.setMinimumWidth(400)

            layout = QVBoxLayout()

            # Таблица с результатами
            table = QTableWidget(len(point_counts), 2)
            table.setHorizontalHeaderLabels(["Облако точек", "Количество точек"])

            total_points = 0

            for row, (name, count) in enumerate(point_counts):
                table.setItem(row, 0, QTableWidgetItem(name))
                table.setItem(row, 1, QTableWidgetItem(f"{count:,}"))
                total_points += count

            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)

            layout.addWidget(QLabel("Результаты подсчета:"))
            layout.addWidget(table)
            layout.addWidget(QLabel(f"<b>Всего точек: {total_points:,}</b>"))

            # Кнопка закрытия
            button_layout = QHBoxLayout()
            close_button = QPushButton("Закрыть")
            close_button.clicked.connect(dialog.accept)
            button_layout.addStretch()
            button_layout.addWidget(close_button)

            layout.addLayout(button_layout)
            dialog.setLayout(layout)

            dialog.exec_()

        except Exception as e:
            print(f"Ошибка при создании диалога: {e}")

    def showWarning(self, message):
        """Показывает предупреждение"""
        try:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(pycc.GetMainWindow(), "Предупреждение", message)
        except:
            print(f"Предупреждение: {message}")

    def showError(self, message):
        """Показывает ошибку"""
        try:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(pycc.GetMainWindow(), "Ошибка", message)
        except:
            print(f"Ошибка: {message}")


# Функция для создания экземпляра плагина
def createPlugin():
    return PointCounter()