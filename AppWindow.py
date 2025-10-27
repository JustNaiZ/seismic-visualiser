import sys
import os
import csv
from PyQt5 import QtCore, QtWidgets, QtGui
import numpy as np


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, glWidget):
        super().__init__()

        self.resize(800, 600)
        self.setWindowTitle('Seismic Visualiser')

        self.glWidget = glWidget
        self.project_data = {}  # Хранит информацию о загруженных файлах
        self.loaded_files = {}  # Хранит информацию о загруженных файлах и их объектах

        # Создаем treeView
        self.treeView = QtWidgets.QTreeView()
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Открытые проекты"])
        self.treeView.setModel(self.model)

        # Настраиваем treeView
        self.treeView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.treeView.setHeaderHidden(False)
        self.treeView.setAlternatingRowColors(True)
        self.treeView.setAnimated(True)

        # Подключаем обработчики событий
        self.treeView.clicked.connect(self.on_treeview_clicked)

        # Инициализируем меню и тулбар
        self.menuBar = self.menuBar()
        self.menuToolBar = QtWidgets.QToolBar()
        self.initMenu()
        self.initToolBar()

        # GUI
        self.initGUI()
        self.initTimer()

    def parse_evp_file(self, file_path):
        """Парсинг .evp файла с сейсмическими событиями"""
        try:
            # Пробуем разные кодировки
            encodings = ['windows-1251', 'cp1251', 'iso-8859-1', 'utf-8']
            file_content = None

            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        file_content = f.readlines()
                    break
                except UnicodeDecodeError:
                    continue

            if file_content is None:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Не удалось определить кодировку файла")
                return []

            events_data = []
            events_count = 0
            for line_num, line in enumerate(file_content, 1):
                line = line.strip()

                # Пропускаем пустые строки и комментарии
                if not line or line.startswith('#'):
                    continue

                # Разбиваем строку по пробелам (убираем множественные пробелы)
                parts = line.split()

                # В вашем файле минимум нужно: дата, время, магнитуда, X, Y, Z
                if len(parts) < 6:
                    print(f"Пропущена строка {line_num}: недостаточно данных ({len(parts)} колонок)")
                    continue

                try:
                    # Парсим основные параметры события из .evp файла
                    date_str = parts[0]  # Дата (например: 20160411)
                    time_str = parts[1]  # Время (например: 081902)
                    magnitude = float(parts[2]) if parts[2] != 'NaN' else 0.0
                    x = float(parts[3])  # Координата X
                    y = float(parts[4])  # Координата Y
                    z = float(parts[5])  # Координата Z (глубина)

                    # Ищем энергию в следующих колонках (может быть в разных позициях)
                    energy = 0.0
                    energy_found = False

                    # Пробуем найти числовые значения энергии в колонках 6-20
                    for i in range(6, min(20, len(parts))):
                        try:
                            part = parts[i]
                            # Пропускаем нулевые значения и NaN
                            if part in ['0.000000e+00', 'NaN', '0.0', '0']:
                                continue

                            # Пробуем преобразовать в float
                            energy_val = float(part)
                            if energy_val > 0:
                                energy = energy_val
                                energy_found = True
                                break
                        except (ValueError, IndexError):
                            continue

                    # Если не нашли энергию, используем магнитуду как приближение
                    if not energy_found and magnitude > 0:
                        energy = 10 ** (1.5 * magnitude + 4.8)  # Примерная формула
                    elif not energy_found:
                        energy = 1.0  # Значение по умолчанию

                    # Определяем тип события по магнитуде
                    if magnitude > 2.0:
                        event_type = "explosion"
                    elif magnitude > 0.5:
                        event_type = "earthquake"
                    else:
                        event_type = "microseismic"

                    events_data.append({
                        'x': x, 'y': y, 'z': z,
                        'event_type': event_type,
                        'energy': energy,
                        'magnitude': magnitude
                    })
                    events_count += 1

                except (ValueError, IndexError) as e:
                    print(f"Ошибка в строке {line_num}: {e}")
                    continue

            print(f"Загружено {events_count} событий из {file_path}")
            return events_data

        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить .evp файл: {str(e)}")
            return []

    def transform_event_coordinates(self, x, y, z):
        """ПРОСТОЕ преобразование координат событий: меняем Y и Z местами"""
        # Просто меняем Y и Z местами
        new_x = x
        new_y = z  # Берем Z как Y (высота)
        new_z = y  # Берем Y как Z (глубина)

        print(f"Преобразование: ({x:.1f}, {y:.1f}, {z:.1f}) -> ({new_x:.1f}, {new_y:.1f}, {new_z:.1f})")

        return new_x, new_y, new_z

    def is_supported_file(self, filename):
        """Проверяет, поддерживается ли файл приложением"""
        supported_extensions = ['.dxf', '.evp', '.evg', '.csv']
        file_ext = os.path.splitext(filename)[1].lower()
        return file_ext in supported_extensions

    def openProject(self):
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите папку")
        if not folder_path:
            return

        # Проверяем что папка существует и доступна
        if not os.path.exists(folder_path):
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выбранная папка не существует")
            return

        # Сохраняем информацию о проекте
        self.project_data[folder_path] = {
            'dxf_files': [],
            'evp_files': [],
            'csv_files': []
        }

        # Добавляем проект в дерево с чекбоксами (изначально выключены)
        self.add_project_to_tree(folder_path)

        QtWidgets.QMessageBox.information(self, "Успех", "Проект успешно загружен в дерево! Включите файлы галочками.")

    def add_project_to_tree(self, folder_path):
        """Добавляет проект в дерево с возможностью включения/выключения"""
        rootNode = self.model.invisibleRootItem()
        project_name = os.path.basename(folder_path)

        # Создаем элемент проекта БЕЗ чекбокса (только для корневой папки)
        project_item = QtGui.QStandardItem(project_name)
        project_item.setCheckable(False)  # Убираем чекбокс у корневой папки
        project_item.setData(folder_path, QtCore.Qt.UserRole)
        project_item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))

        rootNode.appendRow(project_item)

        # РЕКУРСИВНО добавляем всё содержимое папки (файлы и подпапки)
        self.add_folder_contents_recursive(project_item, folder_path)

        # Раскрываем проект по умолчанию
        self.treeView.expand(project_item.index())

    def add_folder_contents_recursive(self, parent_item, folder_path):
        """РЕКУРСИВНО добавляет всё содержимое папки в дерево"""
        try:
            for entry in sorted(os.listdir(folder_path)):
                entry_path = os.path.join(folder_path, entry)

                # Пропускаем системные файлы и папки
                if entry.startswith('.') or entry in ['__pycache__', 'venv', '.venv']:
                    continue

                if os.path.isdir(entry_path):
                    # Для папок - создаем элемент и РЕКУРСИВНО добавляем содержимое
                    folder_item = QtGui.QStandardItem(entry)
                    folder_item.setData(entry_path, QtCore.Qt.UserRole)
                    folder_item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))

                    parent_item.appendRow(folder_item)

                    # РЕКУРСИВНЫЙ вызов для подпапок
                    self.add_folder_contents_recursive(folder_item, entry_path)

                else:
                    # Для файлов - проверяем поддерживается ли формат
                    if self.is_supported_file(entry):
                        # Поддерживаемые файлы - с чекбоксом
                        file_item = QtGui.QStandardItem(entry)
                        file_item.setCheckable(True)
                        file_item.setCheckState(QtCore.Qt.Unchecked)
                        file_item.setData(entry_path, QtCore.Qt.UserRole)
                        file_item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))

                        # Сохраняем информацию о файле
                        file_ext = os.path.splitext(entry)[1].lower()
                        project_path = self.find_project_root(parent_item)

                        if project_path and project_path in self.project_data:
                            if file_ext == '.dxf':
                                self.project_data[project_path]['dxf_files'].append(entry_path)
                            elif file_ext in ['.evp', '.evg']:
                                self.project_data[project_path]['evp_files'].append(entry_path)
                            elif file_ext == '.csv':
                                self.project_data[project_path]['csv_files'].append(entry_path)

                        parent_item.appendRow(file_item)
                    else:
                        # Неподдерживаемые файлы - без чекбокса и серым цветом
                        file_item = QtGui.QStandardItem(entry)
                        file_item.setEnabled(False)
                        file_item.setForeground(QtGui.QColor(128, 128, 128))
                        file_item.setData(entry_path, QtCore.Qt.UserRole)
                        file_item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))
                        parent_item.appendRow(file_item)

        except PermissionError:
            print(f"Нет доступа к папке: {folder_path}")
        except Exception as e:
            print(f"Ошибка при добавлении файлов в дерево: {e}")

    def find_project_root(self, item):
        """Находит корневую папку проекта для элемента"""
        # Поднимаемся вверх по дереву до корневой папки проекта
        current = item
        while current:
            project_path = current.data(QtCore.Qt.UserRole)
            if project_path and project_path in self.project_data:
                return project_path
            current = current.parent()
        return None

    def on_treeview_clicked(self, index):
        """Обработчик клика по дереву - ТОЛЬКО для чекбоксов"""
        item = self.model.itemFromIndex(index)
        if item is None:
            return

        # Обрабатываем ТОЛЬКО если элемент имеет чекбокс (файлы)
        if item.isCheckable():
            file_path = item.data(QtCore.Qt.UserRole)
            if file_path and os.path.isfile(file_path):
                is_checked = item.checkState() == QtCore.Qt.Checked
                self.toggle_file_visibility(file_path, is_checked)

    def toggle_file_visibility(self, file_path, visible):
        """Включает/выключает отображение объектов из файла"""
        file_name = os.path.basename(file_path).lower()
        print(f"Переключение файла {file_name}: {'включен' if visible else 'выключен'}")

        if file_name.endswith('.dxf'):
            self.toggle_dxf_file(file_path, visible)
        elif file_name.endswith(('.evp', '.evg')):
            self.toggle_evp_file(file_path, visible)
        elif file_name == "detectors.csv":
            self.toggle_detectors_file(file_path, visible)
        elif file_name == "events.csv":
            self.toggle_events_csv_file(file_path, visible)
        else:
            # Для других CSV файлов
            self.toggle_generic_csv_file(file_path, visible)

    def toggle_dxf_file(self, file_path, visible):
        """Включает/выключает DXF файл"""
        print(f"toggle_dxf_file: {file_path}, visible: {visible}")

        if visible:
            # Если файл уже загружен, просто включаем его
            if file_path in self.loaded_files:
                for obj_id in self.loaded_files[file_path]:
                    if obj_id in self.glWidget.objects:
                        self.glWidget.objects[obj_id].enabled = True
                        self.glWidget.objects[obj_id].mesh.enabled = True
                        print(f"DXF объект {obj_id} включен")
            else:
                # Загружаем новый DXF файл
                try:
                    print(f"Загрузка нового DXF файла: {file_path}")
                    self.glWidget.add_object_dxf(file_path)

                    # Находим последний добавленный объект (предполагаем, что это наш DXF)
                    new_obj_id = list(self.glWidget.objects.keys())[-1]
                    self.loaded_files[file_path] = [new_obj_id]

                    print(f"DXF файл загружен: {file_path}, объект ID: {new_obj_id}")

                except Exception as e:
                    print(f"Ошибка загрузки DXF файла {file_path}: {e}")
                    QtWidgets.QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить DXF файл: {str(e)}")
        else:
            # Выключаем DXF - отключаем объекты, но не удаляем их
            if file_path in self.loaded_files:
                print(f"Выключение объектов DXF: {self.loaded_files[file_path]}")
                for obj_id in self.loaded_files[file_path]:
                    if obj_id in self.glWidget.objects:
                        self.glWidget.objects[obj_id].enabled = False
                        self.glWidget.objects[obj_id].mesh.enabled = False
                        print(f"DXF объект {obj_id} выключен")

    def toggle_evp_file(self, file_path, visible):
        """Включает/выключает EVP файл"""
        if visible:
            # Загружаем EVP если еще не загружен
            if file_path not in self.loaded_files:
                events_data = self.parse_evp_file(file_path)
                object_ids = []
                for event in events_data:
                    try:
                        # Простое преобразование: меняем Y и Z местами
                        x, y, z = self.transform_event_coordinates(event['x'], event['y'], event['z'])
                        self.glWidget.add_object_event(x, y, z, event['event_type'], event['energy'])
                        object_ids.append(list(self.glWidget.objects.keys())[-1])
                    except Exception as e:
                        print(f"Ошибка добавления события: {e}")
                        continue

                self.loaded_files[file_path] = object_ids
                print(f"EVP файл загружен: {file_path}, объектов: {len(object_ids)}")
            else:
                # Включаем уже загруженные события
                for obj_id in self.loaded_files[file_path]:
                    if obj_id in self.glWidget.objects:
                        self.glWidget.objects[obj_id].enabled = True
                        self.glWidget.objects[obj_id].mesh.enabled = True
        else:
            # Выключаем события из EVP
            if file_path in self.loaded_files:
                for obj_id in self.loaded_files[file_path]:
                    if obj_id in self.glWidget.objects:
                        self.glWidget.objects[obj_id].enabled = False
                        self.glWidget.objects[obj_id].mesh.enabled = False

    def toggle_detectors_file(self, file_path, visible):
        """Включает/выключает detectors.csv"""
        if visible:
            # Загружаем detectors.csv если еще не загружен
            if file_path not in self.loaded_files:
                fx = lambda x: float(x.replace(',', '.'))
                object_ids = []
                try:
                    with open(file_path, newline='', encoding='utf-8') as f:
                        reader = csv.reader(f, delimiter=';', quotechar='|')
                        for row in reader:
                            if len(row) >= 4:
                                try:
                                    det_id = int(row[0])
                                    x = fx(row[2])
                                    y = fx(row[3])
                                    z = fx(row[1])
                                    self.glWidget.add_object_detector(det_id, x, y, z)
                                    object_ids.append(list(self.glWidget.objects.keys())[-1])
                                except (ValueError, IndexError) as e:
                                    print(f"Ошибка загрузки детектора: {e}")
                                    continue

                    self.loaded_files[file_path] = object_ids
                    print(f"Detectors CSV загружен: {file_path}")
                except Exception as e:
                    print(f"Ошибка загрузки detectors.csv: {e}")
            else:
                # Включаем уже загруженные детекторы
                for obj_id in self.loaded_files[file_path]:
                    if obj_id in self.glWidget.objects:
                        self.glWidget.objects[obj_id].enabled = True
                        self.glWidget.objects[obj_id].mesh.enabled = True
        else:
            # Выключаем детекторы
            if file_path in self.loaded_files:
                for obj_id in self.loaded_files[file_path]:
                    if obj_id in self.glWidget.objects:
                        self.glWidget.objects[obj_id].enabled = False
                        self.glWidget.objects[obj_id].mesh.enabled = False

    def toggle_events_csv_file(self, file_path, visible):
        """Включает/выключает events.csv"""
        if visible:
            # Загружаем events.csv если еще не загружен
            if file_path not in self.loaded_files:
                fx = lambda x: float(x.replace(',', '.'))
                object_ids = []
                try:
                    with open(file_path, newline='', encoding='utf-8') as f:
                        reader = csv.reader(f, delimiter=';', quotechar='|')
                        for row in reader:
                            if len(row) >= 6:
                                try:
                                    x = fx(row[1])
                                    y = fx(row[3])
                                    z = fx(row[2])
                                    event_type = row[-1] if row[-1] else "unknown"
                                    energy = fx(row[5]) if len(row) > 5 else 1.0
                                    self.glWidget.add_object_event(x, y, z, event_type, energy)
                                    object_ids.append(list(self.glWidget.objects.keys())[-1])
                                except (ValueError, IndexError) as e:
                                    print(f"Ошибка загрузки события: {e}")
                                    continue

                    self.loaded_files[file_path] = object_ids
                    print(f"Events CSV загружен: {file_path}")
                except Exception as e:
                    print(f"Ошибка загрузки events.csv: {e}")
            else:
                # Включаем уже загруженные события
                for obj_id in self.loaded_files[file_path]:
                    if obj_id in self.glWidget.objects:
                        self.glWidget.objects[obj_id].enabled = True
                        self.glWidget.objects[obj_id].mesh.enabled = True
        else:
            # Выключаем события
            if file_path in self.loaded_files:
                for obj_id in self.loaded_files[file_path]:
                    if obj_id in self.glWidget.objects:
                        self.glWidget.objects[obj_id].enabled = False
                        self.glWidget.objects[obj_id].mesh.enabled = False

    def toggle_generic_csv_file(self, file_path, visible):
        """Включает/выключает другие CSV файлы"""
        print(f"Обработка CSV файла: {file_path}, visible: {visible}")
        # Здесь можно добавить логику для других CSV файлов

    def closeSelectedProject(self):
        index = self.treeView.currentIndex()
        if not index.isValid():
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Проект не выбран")
            return

        item = self.model.itemFromIndex(index)
        parent = item.parent()
        if parent is None:
            # Удаляем проект и все его объекты
            project_path = item.data(QtCore.Qt.UserRole)
            self.remove_project_objects(project_path)
            self.model.removeRow(item.row())
        else:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выделена не корневая папка")

    def remove_project_objects(self, project_path):
        """Удаляет все объекты, связанные с проектом"""
        if project_path in self.project_data:
            # Удаляем все файлы проекта из loaded_files
            for file_list in self.project_data[project_path].values():
                for file_path in file_list:
                    if file_path in self.loaded_files:
                        # Удаляем объекты из сцены
                        for obj_id in self.loaded_files[file_path]:
                            if obj_id in self.glWidget.objects:
                                del self.glWidget.objects[obj_id]
                        del self.loaded_files[file_path]

            del self.project_data[project_path]

    def initMenu(self):
        fileMenu = self.menuBar.addMenu('Файл')
        viewMenu = self.menuBar.addMenu('Вид')

        exitAction = QtWidgets.QAction('Закрыть проект', self)
        openFileAction = QtWidgets.QAction('Открыть проект', self)
        openFileAction.triggered.connect(self.openProject)

        # Действия для управления видом
        expandAllAction = QtWidgets.QAction('Раскрыть всё', self)
        collapseAllAction = QtWidgets.QAction('Свернуть всё', self)

        expandAllAction.triggered.connect(self.treeView.expandAll)
        collapseAllAction.triggered.connect(self.treeView.collapseAll)

        exitAction.triggered.connect(self.closeSelectedProject)
        fileMenu.addAction(openFileAction)
        fileMenu.addAction(exitAction)

        # Кастомный заголовок без лишних отступов
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(12, 2, 12, 2)
        header_label = QtWidgets.QLabel("Открытые проекты")
        header_label.setStyleSheet("color: gray; font-size: 9pt; padding: 0px;")
        header_layout.addWidget(header_label)

        header_action = QtWidgets.QWidgetAction(viewMenu)
        header_action.setDefaultWidget(header_widget)
        viewMenu.addAction(header_action)

        # Кастомный разделитель с отступами по бокам
        separator_widget = QtWidgets.QWidget()
        separator_layout = QtWidgets.QHBoxLayout(separator_widget)
        separator_layout.setContentsMargins(8, 0, 8, 4)  # Отступы слева и справа

        separator_line = QtWidgets.QWidget()
        separator_line.setFixedHeight(1)
        separator_line.setStyleSheet("background-color: #c0c0c0;")
        separator_layout.addWidget(separator_line)

        separator_action = QtWidgets.QWidgetAction(viewMenu)
        separator_action.setDefaultWidget(separator_widget)
        viewMenu.addAction(separator_action)

        viewMenu.addAction(expandAllAction)
        viewMenu.addAction(collapseAllAction)

    def initToolBar(self):
        self.menuToolBar = QtWidgets.QToolBar('Меню с иконками')
        self.menuToolBar.setMovable(False)
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.menuToolBar)

        icon1 = QtGui.QIcon('icons/x.png')
        icon3 = QtGui.QIcon('icons/y.png')
        icon2 = QtGui.QIcon('icons/z.png')

        proj_yz = QtWidgets.QAction(icon1, '', self)
        proj_yx = QtWidgets.QAction(icon2, '', self)
        proj_zx = QtWidgets.QAction(icon3, '', self)

        self.menuToolBar.setIconSize(QtCore.QSize(24, 24))
        self.menuToolBar.addSeparator()

        proj_yz.setToolTip('Вид сбоку')
        proj_yx.setToolTip('Показать все')
        proj_zx.setToolTip('Вид сверху')

        proj_yx.triggered.connect(lambda val: self.glWidget.setArm(val))
        proj_zx.triggered.connect(lambda checked: self.glWidget.set_perspective_top())
        proj_yz.triggered.connect(lambda val: self.glWidget.set_perspective_side())

        self.menuToolBar.addAction(proj_yx)
        self.menuToolBar.addAction(proj_zx)
        self.menuToolBar.addAction(proj_yz)

    def initGUI(self):
        central_widget = QtWidgets.QWidget()
        gui_layout = QtWidgets.QHBoxLayout()

        central_widget.setLayout(gui_layout)
        self.setCentralWidget(central_widget)

        # Создаем splitter для возможности изменения размеров
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # Добавляем treeView с минимальным и максимальным размером
        self.treeView.setMinimumWidth(200)
        self.treeView.setMaximumWidth(600)

        # Создаем правую панель
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.addWidget(self.glWidget)

        # Добавляем виджеты в splitter
        splitter.addWidget(self.treeView)
        splitter.addWidget(right_widget)

        # Устанавливаем начальные размеры (treeView - 300px, GLWidget - остальное)
        splitter.setSizes([300, 500])

        gui_layout.addWidget(splitter)

    def initTimer(self):
        timer = QtCore.QTimer(self)
        timer.setInterval(20)  # 20 мс
        timer.timeout.connect(self.glWidget.updateGL)
        timer.start()