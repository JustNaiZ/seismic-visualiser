import sys
import os
import csv
from PyQt5 import QtCore, QtWidgets, QtGui
import numpy as np

from TreeProject import TreeProject
from properties_field import PropertiesField


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, glWidget):
        super().__init__()

        self.resize(800, 600)
        self.setWindowTitle('Seismic Visualiser')

        self.glWidget = glWidget
        self.loaded_files = {}

        # Создаем treeView через новый класс
        self.treeView = TreeProject(self)

        # Создаем поле свойств
        self.properties_field = PropertiesField(self)

        # Инициализируем меню и тулбар
        self.menuBar = self.menuBar()
        self.menuToolBar = QtWidgets.QToolBar()
        self.initMenu()
        self.initToolBar()

        # GUI
        self.initGUI()
        self.initTimer()

    def initMenu(self):
        fileMenu = self.menuBar.addMenu('Файл')
        viewMenu = self.menuBar.addMenu('Вид')

        # Новые действия для файлового меню
        createProjectAction = QtWidgets.QAction('Создать проект', self)
        openProjectAction = QtWidgets.QAction('Открыть проект', self)

        createProjectAction.triggered.connect(self.treeView.create_project)
        openProjectAction.triggered.connect(self.treeView.open_project)

        # Действия для управления видом
        expandAllAction = QtWidgets.QAction('Раскрыть все', self)
        collapseAllAction = QtWidgets.QAction('Свернуть все', self)
        refreshAction = QtWidgets.QAction('Обновить проекты', self)

        expandAllAction.triggered.connect(self.treeView.expandAll)
        collapseAllAction.triggered.connect(self.treeView.collapseAll)
        refreshAction.triggered.connect(self.treeView.refresh_projects)

        fileMenu.addAction(createProjectAction)
        fileMenu.addAction(openProjectAction)

        viewMenu.addSeparator()
        viewMenu.addAction(expandAllAction)
        viewMenu.addAction(collapseAllAction)
        viewMenu.addAction(refreshAction)

    def initToolBar(self):
        self.menuToolBar = QtWidgets.QToolBar('Меню с иконками')
        self.menuToolBar.setMovable(False)
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.menuToolBar)

        # Загружаем кастомные иконки для видов
        try:
            # Иконка для "Показать все" (вид спереди/изометрический)
            icon_show_all = QtGui.QIcon('icons/y.png')
            # Иконка для "Вид сверху"
            icon_top_view = QtGui.QIcon('icons/z.png')
            # Иконка для "Вид сбоку"
            icon_side_view = QtGui.QIcon('icons/x.png')
        except:
            # Если иконки не найдены, используем стандартные
            icon_show_all = self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)
            icon_top_view = self.style().standardIcon(QtWidgets.QStyle.SP_ArrowUp)
            icon_side_view = self.style().standardIcon(QtWidgets.QStyle.SP_ArrowLeft)

        # Создаем действия с кастомными иконками
        proj_yx = QtWidgets.QAction(icon_show_all, 'Показать все', self)
        proj_zx = QtWidgets.QAction(icon_top_view, 'Вид сверху', self)
        proj_yz = QtWidgets.QAction(icon_side_view, 'Вид сбоку', self)

        # Для обновления используем стандартную круговую стрелку
        refresh_action = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload),
                                           'Обновить проекты', self)

        self.menuToolBar.setIconSize(QtCore.QSize(24, 24))

        proj_yx.setToolTip('Показать все (изометрический вид)')
        proj_zx.setToolTip('Вид сверху')
        proj_yz.setToolTip('Вид сбоку')
        refresh_action.setToolTip('Обновить список проектов')

        proj_yx.triggered.connect(lambda val: self.glWidget.setArm(val))
        proj_zx.triggered.connect(lambda checked: self.glWidget.set_perspective_top())
        proj_yz.triggered.connect(lambda val: self.glWidget.set_perspective_side())
        refresh_action.triggered.connect(self.treeView.refresh_projects)

        # Добавляем все кнопки в тулбар
        self.menuToolBar.addAction(proj_yx)
        self.menuToolBar.addAction(proj_zx)
        self.menuToolBar.addAction(proj_yz)
        self.menuToolBar.addSeparator()
        self.menuToolBar.addAction(refresh_action)

    def initGUI(self):
        central_widget = QtWidgets.QWidget()
        gui_layout = QtWidgets.QHBoxLayout()
        central_widget.setLayout(gui_layout)
        self.setCentralWidget(central_widget)

        # Создаем главный горизонтальный splitter
        main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # ЛЕВАЯ ПАНЕЛЬ: вертикальный splitter для дерева и свойств
        left_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        # Верхняя часть: дерево проектов
        self.treeView.setMinimumWidth(250)
        self.treeView.setMaximumWidth(600)

        # Нижняя часть: поле свойств (изначально скрыто, но добавлено в layout)
        self.properties_field.setMinimumHeight(150)
        self.properties_field.setMaximumHeight(400)

        # Добавляем оба виджета в вертикальный splitter
        left_splitter.addWidget(self.treeView)
        left_splitter.addWidget(self.properties_field)

        # Устанавливаем начальные размеры (дерево занимает больше места)
        left_splitter.setSizes([400, 100])

        # ПРАВАЯ ПАНЕЛЬ: 3D вид
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.addWidget(self.glWidget)

        # Добавляем виджеты в главный splitter
        main_splitter.addWidget(left_splitter)  # Теперь здесь вертикальный splitter
        main_splitter.addWidget(right_widget)  # 3D вид

        # Устанавливаем начальные размеры
        main_splitter.setSizes([300, 500])

        gui_layout.addWidget(main_splitter)

        # Скрываем поле свойств по умолчанию (но оно уже в layout)
        self.properties_field.hide()

        # Сохраняем ссылки для дальнейшего использования
        self.main_splitter = main_splitter
        self.left_splitter = left_splitter

    def initTimer(self):
        timer = QtCore.QTimer(self)
        timer.setInterval(20)  # 20 мс
        timer.timeout.connect(self.glWidget.updateGL)
        timer.start()

    # Все остальные методы остаются без изменений
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

            # ДОБАВЛЯЕМ СТАТИСТИКУ ПО КООРДИНАТАМ
            all_x, all_y, all_z = [], [], []

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

                    # Сохраняем координаты для статистики
                    all_x.append(x)
                    all_y.append(y)
                    all_z.append(z)

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
            if all_x:
                print(f"=== EVP ФАЙЛ: {os.path.basename(file_path)} ===")
                print(f"Количество событий: {len(all_x)}")
                print(f"Координата X: min={min(all_x):.1f}, max={max(all_x):.1f}, avg={np.mean(all_x):.1f}")
                print(f"Координата Y: min={min(all_y):.1f}, max={max(all_y):.1f}, avg={np.mean(all_y):.1f}")
                print(f"Координата Z: min={min(all_z):.1f}, max={max(all_z):.1f}, avg={np.mean(all_z):.1f}")
                print("=" * 50)
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

    def addToProject(self):
        """Добавляет файлы в выбранный проект (работает с любыми папками)"""
        # Получаем текущий выделенный элемент
        current_index = self.treeView.currentIndex()

        # СТРОГАЯ ПРОВЕРКА: должен быть выделен конкретный элемент
        if not current_index.isValid():
            QtWidgets.QMessageBox.warning(
                self,
                "Проект не выбран",
                "Сначала ВЫДЕЛИТЕ проект в списке 'Открытые проекты'!\n\n"
                "Кликните ЛЕВОЙ кнопкой мыши на названии проекта, "
                "чтобы он был выделен синим цветом, затем ПКМ для вызова меню."
            )
            return

        item = self.treeView.model.itemFromIndex(current_index)
        if item is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось определить выбранный проект!"
            )
            return

        project_path = item.data(QtCore.Qt.UserRole)

        # Проверяем что это валидный проект (любая папка)
        if not project_path:
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Выбранный элемент не является проектом!"
            )
            return

        # Проверяем что это директория (любая папка)
        if not os.path.isdir(project_path):
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Выбранный элемент не является папкой проекта!"
            )
            return

        # ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ - можно добавлять файлы
        project_name = os.path.basename(project_path)

        # Выбираем файлы для добавления
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            f"Выберите файлы для добавления в проект '{project_name}'",
            "",
            "Поддерживаемые файлы (*.dxf *.evp *.evg *.csv);;Все файлы (*.*)"
        )

        if not file_paths:
            return

        added_count = 0
        for file_path in file_paths:
            try:
                # Копируем файл в проект (ВО ВНЕШНЮЮ ПАПКУ)
                filename = os.path.basename(file_path)
                dest_path = os.path.join(project_path, filename)

                # Если файл уже существует, добавляем суффикс
                counter = 1
                base_name, ext = os.path.splitext(filename)
                while os.path.exists(dest_path):
                    filename = f"{base_name}_{counter}{ext}"
                    dest_path = os.path.join(project_path, filename)
                    counter += 1

                import shutil
                shutil.copy2(file_path, dest_path)
                added_count += 1

                # Добавляем файл в дерево
                self.treeView.add_file_to_project_tree(item, dest_path)
                print(f"Файл добавлен в проект '{project_name}': {filename}")

            except Exception as e:
                print(f"Ошибка копирования файла {file_path}: {e}")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Ошибка",
                    f"Не удалось скопировать файл {os.path.basename(file_path)}: {str(e)}"
                )

        # Обновляем дерево (раскрываем проект чтобы показать добавленные файлы)
        self.treeView.expand(current_index)

        if added_count > 0:
            QtWidgets.QMessageBox.information(
                self,
                "Успех",
                f"Добавлено {added_count} файлов в проект '{project_name}'!\n"
                f"Файлы сохранены в: {project_path}"
            )
        else:
            QtWidgets.QMessageBox.information(
                self,
                "Информация",
                "Файлы не были добавлены в проект."
            )

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

                    # Проверяем что объект был создан
                    if len(self.glWidget.objects) == 0:
                        QtWidgets.QMessageBox.warning(self, "Предупреждение",
                                                      f"DXF файл {os.path.basename(file_path)} не содержит 3D геометрии.\n"
                                                      f"Был создан объект-заглушка.")
                    else:
                        # Находим последний добавленный объект
                        new_obj_id = list(self.glWidget.objects.keys())[-1]
                        self.loaded_files[file_path] = [new_obj_id]
                        print(f"DXF файл загружен: {file_path}, объект ID: {new_obj_id}")

                except Exception as e:
                    print(f"Ошибка загрузки DXF файла {file_path}: {e}")
                    QtWidgets.QMessageBox.warning(self, "Ошибка",
                                                  f"Не удалось загрузить DXF файл: {str(e)}\n"
                                                  f"Файл может быть пустым или использовать неподдерживаемые объекты.")
        else:
            # ВЫКЛЮЧАЕМ DXF
            if file_path in self.loaded_files:
                for obj_id in self.loaded_files[file_path]:
                    if obj_id in self.glWidget.objects:
                        self.glWidget.objects[obj_id].enabled = False
                        self.glWidget.objects[obj_id].mesh.enabled = False
                        print(f"DXF объект {obj_id} выключен")

    def toggle_evp_file(self, file_path, visible):
        """Включает/выключает EVP файл - С СОХРАНЕННОЙ ПРОЗРАЧНОСТЬЮ"""
        print(f"toggle_evp_file: {file_path}, visible: {visible}")

        if visible:
            if file_path not in self.loaded_files:
                print(f"🔄 Загрузка EVP файла: {file_path}")
                events_data = self.parse_evp_file(file_path)

                object_ids = []
                for event in events_data:
                    try:
                        x, y, z = self.transform_event_coordinates(event['x'], event['y'], event['z'])
                        energy = event['energy']

                        # Получаем настройки визуализации И ПРОЗРАЧНОСТЬ
                        visualization_type = "spheres"
                        base_color = [1.0, 0.0, 0.0]
                        opacity = 1.0  # по умолчанию

                        if hasattr(self, 'properties_field') and file_path in self.properties_field.file_properties:
                            props = self.properties_field.file_properties[file_path]

                            # Проверяем energy_ranges
                            if 'energy_ranges' in props:
                                thresholds = sorted(props['energy_ranges'].keys(), reverse=True)
                                for thresh in thresholds:
                                    if energy >= thresh:
                                        range_props = props['energy_ranges'][thresh]
                                        visualization_type = range_props.get('visualization', 'spheres')
                                        base_color = range_props.get('color', [1.0, 0.0, 0.0])
                                        # Получаем сохраненную прозрачность для этого диапазона
                                        opacity = range_props.get('opacity', 1.0)

                                        # Формируем RGBA цвет с сохраненной прозрачностью
                                        rgba_color = list(base_color[:3]) + [opacity]
                                        break

                        print(f"🎯 Создание: тип={visualization_type}, прозрачность={opacity}, цвет={rgba_color}")

                        # Создаем объект с нужным типом И ПРОЗРАЧНОСТЬЮ
                        if visualization_type == "spheres":
                            new_obj = self.glWidget.add_object_event(x, y, z, event['event_type'], energy, rgba_color)
                        elif visualization_type == "beach_balls":
                            new_obj = self.glWidget.add_object_beach_ball(x, y, z, event['event_type'], energy, rgba_color)
                        elif visualization_type == "points":
                            new_obj = self.glWidget.add_object_point(x, y, z, event['event_type'], energy, rgba_color)
                        else:
                            new_obj = self.glWidget.add_object_event(x, y, z, event['event_type'], energy, rgba_color)

                        new_obj_id = list(self.glWidget.objects.keys())[-1]
                        object_ids.append(new_obj_id)

                    except Exception as e:
                        print(f"❌ Ошибка добавления события: {e}")
                        continue

                self.loaded_files[file_path] = object_ids
                print(f"✅ Файл загружен с сохраненной прозрачностью, объектов: {len(object_ids)}")
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

    def remove_project_objects(self, project_path):
        """Удаляет все объекты, связанные с проектом"""
        print(f"Удаление объектов проекта: {project_path}")

        # Ищем все файлы, связанные с этим проектом
        files_to_remove = []
        for file_path in list(self.loaded_files.keys()):
            if file_path.startswith(project_path):
                files_to_remove.append(file_path)

        # Удаляем объекты из сцены
        for file_path in files_to_remove:
            if file_path in self.loaded_files:
                for obj_id in self.loaded_files[file_path]:
                    if obj_id in self.glWidget.objects:
                        del self.glWidget.objects[obj_id]
                        print(f"Удален объект {obj_id}")
                del self.loaded_files[file_path]
                print(f"Удалена информация о файле: {file_path}")

    def change_event_visualization(self, obj_id, visualization_type, base_color):
        """Изменяет визуализацию конкретного события - С ПЕРЕДАЧЕЙ ЦВЕТА"""
        try:
            if obj_id not in self.glWidget.objects:
                return

            obj = self.glWidget.objects[obj_id]
            if obj.obj_type != "event":
                return

            # Получаем параметры события
            x, y, z = obj.location
            event_type = obj.data.get("type", "unknown")
            energy = obj.data.get("energy", 1.0)

            if len(base_color) == 3:
                color_to_use = base_color + [1.0]  # RGB -> RGBA
            else:
                color_to_use = base_color

            print(f"🎨 Используемый цвет: {color_to_use}")

            if hasattr(obj, 'mesh'):
                self.cleanup_mesh_vbo(obj.mesh)

            # Удаляем старый объект
            del self.glWidget.objects[obj_id]

            # Создаем новый объект с выбранной визуализацией И ПЕРЕДАЕМ ЦВЕТ
            if visualization_type == "spheres":
                new_obj = self.glWidget.add_object_event(x, y, z, event_type, energy, color_to_use)
            elif visualization_type == "beach_balls":
                new_obj = self.glWidget.add_object_beach_ball(x, y, z, event_type, energy, color_to_use)
            elif visualization_type == "points":
                new_obj = self.glWidget.add_object_point(x, y, z, event_type, energy, color_to_use)
            else:
                new_obj = self.glWidget.add_object_event(x, y, z, event_type, energy, color_to_use)

            # Сохраняем тот же ID
            self.glWidget.objects[obj_id] = new_obj
            print(f"✅ Визуализация изменена для объекта {obj_id}")

        except Exception as e:
            print(f"❌ Ошибка в change_event_visualization: {e}")
            import traceback
            traceback.print_exc()

    def cleanup_mesh_vbo(self, mesh):
        """Очищает VBO меша из памяти OpenGL"""
        try:
            # Удаляем VBO если они существуют
            if hasattr(mesh, 'verticesVBO') and mesh.verticesVBO:
                mesh.verticesVBO.delete()
            if hasattr(mesh, 'colorsFacesVBO') and mesh.colorsFacesVBO:
                mesh.colorsFacesVBO.delete()
            if hasattr(mesh, 'colorsEdgesVBO') and mesh.colorsEdgesVBO:
                mesh.colorsEdgesVBO.delete()
            if hasattr(mesh, 'colorsHoveredVBO') and mesh.colorsHoveredVBO:
                mesh.colorsHoveredVBO.delete()
            if hasattr(mesh, 'colorsSelectedVBO') and mesh.colorsSelectedVBO:
                mesh.colorsSelectedVBO.delete()
            if hasattr(mesh, 'colorsEdgesActiveVBO') and mesh.colorsEdgesActiveVBO:
                mesh.colorsEdgesActiveVBO.delete()
        except Exception as e:
            print(f"⚠️ Ошибка при очистке VBO: {e}")

    # В класс MainWindow добавим метод для изменения стиля отображения EVP файлов
    def change_evp_visualization(self, file_path, visualization_type):
        """Изменяет способ визуализации для EVP файла"""
        print(f"Изменение визуализации для {file_path} на тип: {visualization_type}")

        # Сначала скрываем текущие объекты
        if file_path in self.loaded_files:
            for obj_id in self.loaded_files[file_path]:
                if obj_id in self.glWidget.objects:
                    self.glWidget.objects[obj_id].enabled = False

        # Перезагружаем файл с новым типом визуализации
        events_data = self.parse_evp_file(file_path)

        # Удаляем старые объекты
        if file_path in self.loaded_files:
            for obj_id in self.loaded_files[file_path]:
                if obj_id in self.glWidget.objects:
                    del self.glWidget.objects[obj_id]
            self.loaded_files[file_path] = []

        # Создаем новые объекты с выбранным типом визуализации
        object_ids = []
        for event in events_data:
            try:
                x, y, z = self.transform_event_coordinates(event['x'], event['y'], event['z'])

                if visualization_type == "spheres":
                    self.glWidget.add_object_event(x, y, z, event['event_type'], event['energy'])
                elif visualization_type == "beach_balls":
                    self.glWidget.add_object_beach_ball(x, y, z, event['event_type'], event['energy'])
                elif visualization_type == "points":
                    self.glWidget.add_object_point(x, y, z, event['event_type'], event['energy'])

                new_obj_id = list(self.glWidget.objects.keys())[-1]
                object_ids.append(new_obj_id)

            except Exception as e:
                print(f"Ошибка добавления события: {e}")
                continue

        self.loaded_files[file_path] = object_ids
        print(f"EVP файл перезагружен с типом визуализации: {visualization_type}, объектов: {len(object_ids)}")

    def show_properties_field(self, file_path, visualization_type):
        """Показывает поле свойств для выбранного файла"""
        try:
            print(f"=== ПОКАЗЫВАЕМ СВОЙСТВА ДЛЯ: {os.path.basename(file_path)} ===")

            # ПОКАЗЫВАЕМ поле свойств (если было скрыто)
            if self.properties_field.isHidden():
                self.properties_field.show()

                # Обновляем размеры splitter чтобы было видно свойства
                if hasattr(self, 'left_splitter'):
                    self.left_splitter.setSizes([300, 200])  # Дерево: 300, Свойства: 200

            # Показываем свойства для файла
            self.properties_field.show_event_properties(file_path, visualization_type)

            print("Поле свойств успешно показано")

        except Exception as e:
            print(f"Ошибка при показе поля свойств: {e}")
            import traceback
            traceback.print_exc()

    def hide_properties_field(self):
        """Скрывает поле свойств"""
        if hasattr(self, 'left_splitter'):
            # Скрываем свойства и отдаем все место дереву
            self.properties_field.hide()
            self.left_splitter.setSizes([500, 0])

    def closeEvent(self, event):
        """Сохраняем настройки при закрытии приложения"""
        try:
            # Сохраняем настройки свойств
            if hasattr(self, 'properties_field'):
                self.properties_field.save_properties_settings()

            # Сохраняем настройки проектов
            if hasattr(self, 'treeView'):
                self.treeView.save_projects()

            print("Все настройки сохранены")

        except Exception as e:
            print(f"Ошибка при сохранении настроек: {e}")

        event.accept()

    def reload_file_with_settings(self, file_path):
        """Перезагружает файл с применением сохраненных настроек"""
        try:
            print(f"🔄 Перезагрузка файла: {os.path.basename(file_path)}")

            # Сохраняем текущее состояние видимости
            was_visible = file_path in self.loaded_files

            # Полностью удаляем файл из загруженных
            if file_path in self.loaded_files:
                # Удаляем все объекты этого файла из сцены
                for obj_id in self.loaded_files[file_path]:
                    if obj_id in self.glWidget.objects:
                        # Очищаем VBO перед удалением
                        obj = self.glWidget.objects[obj_id]
                        if hasattr(obj, 'mesh'):
                            self.cleanup_mesh_vbo(obj.mesh)
                        del self.glWidget.objects[obj_id]
                # Удаляем запись о файле
                del self.loaded_files[file_path]
                print(f"🗑️ Удалены объекты файла {os.path.basename(file_path)}")

            # Загружаем файл заново
            if was_visible:
                print(f"🔄 Загружаем файл заново...")
                if file_path.lower().endswith('.evp'):
                    self.toggle_evp_file(file_path, True)
                elif file_path.lower().endswith('.dxf'):
                    self.toggle_dxf_file(file_path, True)
                elif file_path.lower().endswith('.csv'):
                    if os.path.basename(file_path).lower() == "detectors.csv":
                        self.toggle_detectors_file(file_path, True)
                    elif os.path.basename(file_path).lower() == "events.csv":
                        self.toggle_events_csv_file(file_path, True)
                    else:
                        self.toggle_generic_csv_file(file_path, True)

                print(f"✅ Файл {os.path.basename(file_path)} перезагружен")

        except Exception as e:
            print(f"❌ Ошибка при перезагрузке файла: {e}")
            import traceback
            traceback.print_exc()

    def reload_file_range(self, file_path, energy_threshold, visualization_type):
        """Перезагружает только объекты указанного диапазона энергии"""
        try:
            print(f"🔄 Перезагрузка диапазона {energy_threshold} файла {os.path.basename(file_path)}")

            if file_path not in self.loaded_files:
                return

            obj_ids = self.loaded_files[file_path].copy()

            for obj_id in obj_ids:
                if obj_id in self.glWidget.objects:
                    obj = self.glWidget.objects[obj_id]
                    if obj.obj_type == "event":
                        energy = obj.data.get("energy", 0)

                        try:
                            energy_float = float(energy) if energy else 0.0
                        except (ValueError, TypeError):
                            energy_float = 0.0

                        # Проверяем попадает ли объект в нужный диапазон
                        if energy_float >= energy_threshold:
                            # Получаем параметры объекта
                            x, y, z = obj.location
                            event_type = obj.data.get("type", "unknown")

                            # Очищаем старый объект
                            if hasattr(obj, 'mesh'):
                                self.cleanup_mesh_vbo(obj.mesh)

                            # Удаляем старый объект
                            del self.glWidget.objects[obj_id]

                            # Получаем сохраненные настройки для нового типа
                            if hasattr(self, 'properties_field'):
                                props = self.properties_field.file_properties.get(file_path, {})
                                color = [1.0, 0.0, 0.0]
                                opacity = 1.0

                                if 'energy_ranges' in props:
                                    range_props = props['energy_ranges'].get(energy_threshold, {})
                                    color = range_props.get('color', color)
                                    opacity = range_props.get('opacity', 1.0)

                                rgba_color = list(color[:3]) + [opacity]

                                # Создаем новый объект с нужным типом
                                if visualization_type == "spheres":
                                    new_obj = self.glWidget.add_object_event(x, y, z, event_type, energy_float,
                                                                             rgba_color)
                                elif visualization_type == "beach_balls":
                                    new_obj = self.glWidget.add_object_beach_ball(x, y, z, event_type, energy_float,
                                                                                  rgba_color)
                                elif visualization_type == "points":
                                    new_obj = self.glWidget.add_object_point(x, y, z, event_type, energy_float,
                                                                             rgba_color)
                                else:
                                    new_obj = self.glWidget.add_object_event(x, y, z, event_type, energy_float,
                                                                             rgba_color)

                                # Сохраняем тот же ID
                                self.glWidget.objects[obj_id] = new_obj

            print(f"✅ Диапазон {energy_threshold} перезагружен")

        except Exception as e:
            print(f"❌ Ошибка перезагрузки диапазона: {e}")

    def reload_file_with_updated_range(self, file_path, energy_threshold, visualization_type, rgba_color):
        """Перезагружает файл с обновленным диапазоном"""
        try:
            print(f"🔄 Перезагрузка диапазона {energy_threshold} файла {os.path.basename(file_path)}")
            print(f"📊 Тип: {visualization_type}, Цвет: {rgba_color}")

            # Сохраняем видимость
            was_visible = file_path in self.loaded_files

            # Удаляем файл если загружен
            if was_visible:
                self.toggle_evp_file(file_path, False)

            # Обновляем настройки в properties_field
            if hasattr(self, 'properties_field'):
                if file_path not in self.properties_field.file_properties:
                    self.properties_field.initialize_file_properties(file_path, visualization_type)

                # Устанавливаем правильный тип для ВСЕГО файла
                self.properties_field.file_properties[file_path]['type'] = visualization_type

                # Обновляем настройки для конкретного диапазона
                if ('energy_ranges' in self.properties_field.file_properties[file_path] and
                        energy_threshold in self.properties_field.file_properties[file_path]['energy_ranges']):
                    range_props = self.properties_field.file_properties[file_path]['energy_ranges'][energy_threshold]
                    range_props['visualization'] = visualization_type
                    range_props['opacity'] = rgba_color[3]
                    range_props['color'] = rgba_color[:3]

                # Сохраняем настройки
                self.properties_field.save_properties_settings()

            # Загружаем файл заново
            if was_visible:
                self.toggle_evp_file(file_path, True)

            print(f"✅ Файл перезагружен с обновленным диапазоном")

        except Exception as e:
            print(f"❌ Ошибка перезагрузки диапазона: {e}")
            import traceback
            traceback.print_exc()

    # В MainWindow.py добавьте:
    def reload_file_with_settings(self, file_path):
        """Перезагружает файл с применением сохраненных настроек"""
        try:
            print(f"🔄 Перезагрузка файла с настройками: {os.path.basename(file_path)}")

            # Сохраняем текущее состояние видимости
            was_visible = file_path in self.loaded_files

            # Полностью удаляем файл из загруженных
            if file_path in self.loaded_files:
                # Удаляем все объекты этого файла из сцены
                for obj_id in self.loaded_files[file_path]:
                    if obj_id in self.glWidget.objects:
                        # Очищаем VBO перед удалением
                        obj = self.glWidget.objects[obj_id]
                        if hasattr(obj, 'mesh'):
                            self.cleanup_mesh_vbo(obj.mesh)
                        del self.glWidget.objects[obj_id]
                # Удаляем запись о файле
                del self.loaded_files[file_path]
                print(f"🗑️ Удалены объекты файла {os.path.basename(file_path)}")

            # Загружаем файл заново с новыми настройками
            if was_visible:
                print(f"🔄 Загружаем файл заново с новыми настройками...")
                if file_path.lower().endswith('.evp'):
                    self.toggle_evp_file(file_path, True)
                elif file_path.lower().endswith('.dxf'):
                    self.toggle_dxf_file(file_path, True)
                elif file_path.lower().endswith('.csv'):
                    if os.path.basename(file_path).lower() == "detectors.csv":
                        self.toggle_detectors_file(file_path, True)
                    elif os.path.basename(file_path).lower() == "events.csv":
                        self.toggle_events_csv_file(file_path, True)
                    else:
                        self.toggle_generic_csv_file(file_path, True)

                print(f"✅ Файл {os.path.basename(file_path)} перезагружен с новыми настройками")

        except Exception as e:
            print(f"❌ Ошибка при перезагрузке файла: {e}")
            import traceback
            traceback.print_exc()