import os
import shutil
import json
from PyQt5 import QtCore, QtWidgets, QtGui

class TreeProject(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # Модель данных
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Открытые проекты"])
        self.setModel(self.model)

        # Настройка внешнего вида
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setHeaderHidden(False)
        self.setAlternatingRowColors(True)
        self.setAnimated(True)

        # Обработчики событий
        self.clicked.connect(self.on_treeview_clicked)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Корневая папка проектов и файл настроек
        self.projects_root = self.get_projects_root()
        self.settings_file = os.path.join(self.projects_root, "projects_settings.json")
        self.current_projects_state = set()

        # Загружаем сохраненные проекты
        self.saved_projects = self.load_saved_projects()

        # Таймер для отслеживания изменений
        self.file_watcher_timer = QtCore.QTimer(self)
        self.file_watcher_timer.timeout.connect(self.check_projects_changes)
        self.file_watcher_timer.start(2000)

        # Загрузка проектов при старте
        self.load_projects_list()
        self.update_projects_state()

    def get_projects_root(self):
        """Возвращает путь к корневой папке проектов"""
        projects_root = os.path.join(os.path.expanduser("~"), "SeismicProjects")
        if not os.path.exists(projects_root):
            os.makedirs(projects_root)
        return projects_root

    def load_saved_projects(self):
        """Загружает сохраненные пути проектов из файла настроек"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
        return []

    def save_projects(self):
        """Сохраняет текущие открытые проекты в файл настроек"""
        try:
            projects_to_save = []
            for i in range(self.model.rowCount()):
                item = self.model.item(i)
                project_path = item.data(QtCore.Qt.UserRole)
                if project_path and os.path.exists(project_path):
                    projects_to_save.append(project_path)

            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(projects_to_save, f, ensure_ascii=False, indent=2)

            print(f"Сохранено {len(projects_to_save)} проектов в настройки")
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def is_supported_file(self, filename):
        """Проверяет, поддерживается ли файл приложением"""
        supported_extensions = ['.dxf', '.evp', '.evg', '.csv']
        file_ext = os.path.splitext(filename)[1].lower()
        return file_ext in supported_extensions

    def add_project_to_tree(self, project_path, save_to_settings=True):
        """Добавляет проект в дерево (работает с любыми папками)"""
        # Проверяем, не добавлен ли уже этот проект
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            existing_path = item.data(QtCore.Qt.UserRole)
            if existing_path == project_path:
                print(f"Проект уже добавлен: {project_path}")
                return item

        project_name = os.path.basename(project_path)

        project_item = QtGui.QStandardItem(project_name)
        project_item.setCheckable(False)
        project_item.setData(project_path, QtCore.Qt.UserRole)
        project_item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))

        # Добавляем подсказку с путем
        project_item.setToolTip(f"Путь: {project_path}")

        self.model.appendRow(project_item)

        # Загружаем файлы проекта
        self.load_project_files(project_item, project_path)

        # Обновляем состояние watcher если это проект из корневой папки
        if os.path.dirname(project_path) == self.projects_root:
            self.update_projects_state()

        # Сохраняем в настройки
        if save_to_settings:
            self.save_projects()

        return project_item

    def add_file_to_project_tree(self, project_item, file_path):
        """Добавляет файл в дерево проекта"""
        filename = os.path.basename(file_path)

        if self.is_supported_file(filename):
            file_item = QtGui.QStandardItem(filename)
            file_item.setCheckable(True)
            file_item.setCheckState(QtCore.Qt.Unchecked)
            file_item.setData(file_path, QtCore.Qt.UserRole)
            file_item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))

            # Добавляем подсказку с полным путем
            file_item.setToolTip(f"Путь: {file_path}")

            project_item.appendRow(file_item)

    def load_project_files(self, project_item, project_path):
        """Загружает файлы проекта в дерево (работает с любыми папками)"""
        try:
            for entry in sorted(os.listdir(project_path)):
                entry_path = os.path.join(project_path, entry)

                if os.path.isfile(entry_path):
                    self.add_file_to_project_tree(project_item, entry_path)

        except PermissionError:
            print(f"Нет доступа к папке: {project_path}")
            QtWidgets.QMessageBox.warning(
                self.main_window,
                "Ошибка доступа",
                f"Нет доступа для чтения папки: {project_path}"
            )
        except Exception as e:
            print(f"Ошибка при загрузке файлов проекта: {e}")

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
                if self.main_window:
                    self.main_window.toggle_file_visibility(file_path, is_checked)

                    # ЕСЛИ ВКЛЮЧАЕМ ФАЙЛ - ПРИМЕНЯЕМ СОХРАНЕННЫЕ СВОЙСТВА
                    if is_checked and hasattr(self.main_window, 'properties_field'):
                        # Проверяем есть ли сохраненные свойства для этого файла
                        if file_path in self.main_window.properties_field.file_properties:
                            print(f"Применяем сохраненные свойства для: {os.path.basename(file_path)}")
                            self.main_window.properties_field.apply_properties(file_path)

    def show_context_menu(self, position):
        """Показывает контекстное меню для проектов"""
        index = self.indexAt(position)
        if not index.isValid():
            return

        item = self.model.itemFromIndex(index)
        if not item:
            return

        item_path = item.data(QtCore.Qt.UserRole)

        # Если это файл EVP - показываем специальное меню
        if item_path and os.path.isfile(item_path) and item_path.lower().endswith('.evp'):
            self.show_evp_context_menu(item, position)
            return

        project_path = item.data(QtCore.Qt.UserRole)

        # Проверяем что это папка проекта (любая папка)
        if not project_path or not os.path.isdir(project_path):
            return

        project_path = item.data(QtCore.Qt.UserRole)
        if not project_path or not os.path.isdir(project_path):
            return

        # Создаем контекстное меню
        context_menu = QtWidgets.QMenu(self.main_window)

        # Кнопка "Добавить в проект" - всегда доступна
        add_files_action = context_menu.addAction("Добавить в проект")

        # Проверяем права на запись
        can_write = True
        try:
            test_file = os.path.join(project_path, "test_write_permission.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except PermissionError:
            can_write = False
            add_files_action.setEnabled(False)
            add_files_action.setToolTip("Нет прав на запись в эту папку")

        context_menu.addSeparator()

        # Кнопка "Закрыть проект" - всегда доступна
        close_action = context_menu.addAction("Закрыть проект")

        # Кнопка "Удалить проект" - доступна только для проектов в корневой папке
        project_parent = os.path.dirname(project_path)
        if project_parent == self.projects_root:
            delete_action = context_menu.addAction("Удалить проект")

        # Показываем меню и обрабатываем выбор
        action = context_menu.exec_(self.viewport().mapToGlobal(position))

        if action == add_files_action:
            if self.main_window:
                self.main_window.addToProject()
        elif action == close_action:
            self.close_project(item)
        elif project_parent == self.projects_root and action == delete_action:
            self.delete_project(item)

    def show_evp_context_menu(self, item, position):
        """Показывает контекстное меню для EVP файлов"""
        context_menu = QtWidgets.QMenu(self.main_window)

        # Текущее состояние видимости
        is_visible = item.checkState() == QtCore.Qt.Checked
        visibility_action = context_menu.addAction("Скрыть" if is_visible else "Показать")

        # Кнопка для открытия свойств
        properties_action = context_menu.addAction("Свойства события")

        context_menu.addSeparator()

        # Показываем меню и обрабатываем выбор
        action = context_menu.exec_(self.viewport().mapToGlobal(position))

        file_path = item.data(QtCore.Qt.UserRole)

        if action == visibility_action:
            # Переключаем видимость
            new_state = not is_visible
            item.setCheckState(QtCore.Qt.Checked if new_state else QtCore.Qt.Unchecked)
            if self.main_window:
                self.main_window.toggle_file_visibility(file_path, new_state)

        elif action == properties_action:
            print("=== НАЖАТА КНОПКА 'СВОЙСТВА СОБЫТИЯ' ===")
            # ОПРЕДЕЛЯЕМ ТИП ВИЗУАЛИЗАЦИИ
            visualization_type = self.get_visualization_type_for_file(file_path)
            print(f"Тип визуализации: {visualization_type}")

            if self.main_window:
                print("Вызываем show_properties_field...")
                self.main_window.show_properties_field(file_path, visualization_type)
            else:
                print("main_window не найден!")

    def close_project(self, item):
        """Закрывает проект (удаляет из дерева)"""
        if item:
            project_path = item.data(QtCore.Qt.UserRole)
            # Удаляем объекты проекта из сцены
            if self.main_window:
                self.main_window.remove_project_objects(project_path)

            self.model.removeRow(item.row())

            # Обновляем настройки
            self.save_projects()

            QtWidgets.QMessageBox.information(self.main_window, "Успех", "Проект закрыт")

    def delete_project(self, item):
        """Удаляет проект полностью с диска (только для проектов в корневой папки)"""
        if not item:
            return

        project_path = item.data(QtCore.Qt.UserRole)
        project_name = item.text()

        # Дополнительная проверка - удалять можно только проекты из корневой папки
        project_parent = os.path.dirname(project_path)
        if project_parent != self.projects_root:
            QtWidgets.QMessageBox.warning(
                self.main_window,
                "Ошибка",
                "Удалять можно только проекты созданные через приложение!\n\n"
                "Внешние проекты можно только закрыть."
            )
            return

        if not project_path or not os.path.exists(project_path):
            return

        # Подтверждение удаления
        reply = QtWidgets.QMessageBox.question(
            self.main_window,
            "Подтверждение удаления",
            f"Вы уверены, что хотите УДАЛИТЬ проект '{project_name}'?\n\n"
            f"Все файлы в папке будут удалены безвозвратно!\n"
            f"Путь: {project_path}",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            try:
                # Удаляем все объекты связанные с проектом
                if self.main_window:
                    self.main_window.remove_project_objects(project_path)

                # Удаляем папку проекта
                shutil.rmtree(project_path)

                # Удаляем из дерева
                self.model.removeRow(item.row())

                # Обновляем состояние для watcher и настройки
                self.update_projects_state()
                self.save_projects()

                QtWidgets.QMessageBox.information(
                    self.main_window,
                    "Успех",
                    f"Проект '{project_name}' полностью удален"
                )

            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self.main_window,
                    "Ошибка",
                    f"Не удалось удалить проект: {str(e)}"
                )

    def update_projects_state(self):
        """Обновляет состояние проектов для сравнения"""
        self.current_projects_state = set()
        if os.path.exists(self.projects_root):
            for project_name in os.listdir(self.projects_root):
                project_path = os.path.join(self.projects_root, project_name)
                if os.path.isdir(project_path):
                    self.current_projects_state.add(project_name)

    def check_projects_changes(self):
        """Проверяет изменения в корневой папке проектов и обновляет дерево при необходимости"""
        if not os.path.exists(self.projects_root):
            return

        # Получаем текущее состояние только корневой папки
        current_state = set()
        for project_name in os.listdir(self.projects_root):
            project_path = os.path.join(self.projects_root, project_name)
            if os.path.isdir(project_path):
                current_state.add(project_name)

        # Сравниваем с предыдущим состоянием
        if current_state != self.current_projects_state:
            print("Обнаружены изменения в корневой папке проектов. Обновляю дерево...")
            self.sync_projects_tree()
            self.current_projects_state = current_state

    def sync_projects_tree(self):
        """Синхронизирует дерево проектов с состоянием корневой папки"""
        # Сохраняем информацию о текущем выделении и раскрытии
        expanded_items = self.get_expanded_items()

        # Удаляем только проекты из корневой папки
        items_to_remove = []
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            project_path = item.data(QtCore.Qt.UserRole)
            if project_path and os.path.dirname(project_path) == self.projects_root:
                # Проверяем существует ли папка
                if not os.path.exists(project_path):
                    items_to_remove.append(i)

        # Удаляем несуществующие проекты (в обратном порядке чтобы индексы не сдвигались)
        for i in sorted(items_to_remove, reverse=True):
            self.model.removeRow(i)

        # Добавляем новые проекты из корневой папки
        if os.path.exists(self.projects_root):
            for project_name in sorted(os.listdir(self.projects_root)):
                project_path = os.path.join(self.projects_root, project_name)
                if os.path.isdir(project_path):
                    # Проверяем не добавлен ли уже этот проект
                    already_exists = False
                    for i in range(self.model.rowCount()):
                        item = self.model.item(i)
                        if item and item.data(QtCore.Qt.UserRole) == project_path:
                            already_exists = True
                            break

                    if not already_exists:
                        self.add_project_to_tree(project_path, save_to_settings=False)

        # Восстанавливаем раскрытие элементов
        self.restore_expanded_items(expanded_items)

    def load_projects_list(self):
        """Загружает список проектов из корневой папки и сохраненных проектов"""
        # Сохраняем информацию о текущем выделении и раскрытии
        expanded_items = self.get_expanded_items()

        self.model.removeRows(0, self.model.rowCount())

        # Сначала загружаем проекты из корневой папки
        if os.path.exists(self.projects_root):
            projects_found = 0
            for project_name in sorted(os.listdir(self.projects_root)):
                project_path = os.path.join(self.projects_root, project_name)
                if os.path.isdir(project_path):
                    self.add_project_to_tree(project_path, save_to_settings=False)
                    projects_found += 1
            print(f"Загружено проектов из корневой папки: {projects_found}")

        # Затем загружаем сохраненные проекты (внешние)
        external_projects_found = 0
        for project_path in self.saved_projects:
            if (os.path.exists(project_path) and
                    os.path.isdir(project_path) and
                    project_path not in [self.model.item(i).data(QtCore.Qt.UserRole) for i in
                                         range(self.model.rowCount())]):
                self.add_project_to_tree(project_path, save_to_settings=False)
                external_projects_found += 1

        print(f"Загружено внешних проектов: {external_projects_found}")

        # Восстанавливаем раскрытие элементов
        self.restore_expanded_items(expanded_items)

    def refresh_projects(self):
        """Обновляет список проектов - основная функция для кнопки обновления"""
        print("Обновление списка проектов...")

        # Сохраняем текущее состояние раскрытия
        expanded_items = self.get_expanded_items()

        # Перезагружаем все проекты
        self.load_projects_list()

        # Восстанавливаем раскрытие
        self.restore_expanded_items(expanded_items)

        # Сохраняем текущее состояние
        self.save_projects()

        QtWidgets.QMessageBox.information(
            self.main_window,
            "Обновление завершено",
            "Список проектов успешно обновлен!"
        )

    def get_expanded_items(self):
        """Возвращает список раскрытых элементов"""
        expanded = []
        for i in range(self.model.rowCount()):
            index = self.model.index(i, 0)
            if self.isExpanded(index):
                item = self.model.itemFromIndex(index)
                if item:
                    expanded.append(item.data(QtCore.Qt.UserRole))
        return expanded

    def restore_expanded_items(self, expanded_paths):
        """Восстанавливает раскрытие элементов"""
        for i in range(self.model.rowCount()):
            index = self.model.index(i, 0)
            item = self.model.itemFromIndex(index)
            if item and item.data(QtCore.Qt.UserRole) in expanded_paths:
                self.expand(index)

    def create_project(self):
        """Создает новый проект"""
        project_name, ok = QtWidgets.QInputDialog.getText(
            self.main_window, 'Создать проект', 'Введите название проекта:'
        )

        if ok and project_name:
            project_path = os.path.join(self.projects_root, project_name)

            if os.path.exists(project_path):
                QtWidgets.QMessageBox.warning(self.main_window, "Ошибка", "Проект с таким именем уже существует!")
                return

            try:
                os.makedirs(project_path)
                project_item = self.add_project_to_tree(project_path)

                # Обновляем состояние для watcher
                self.update_projects_state()

                QtWidgets.QMessageBox.information(self.main_window, "Успех", f"Проект '{project_name}' создан!")

            except Exception as e:
                QtWidgets.QMessageBox.critical(self.main_window, "Ошибка", f"Не удалось создать проект: {str(e)}")

    def open_project(self):
        """Открывает папку как проект"""
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            self.main_window,
            "Выберите папку проекта",
            "",
            QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks
        )

        if not folder_path:
            return

        # Проверяем что папка существует
        if not os.path.exists(folder_path):
            QtWidgets.QMessageBox.warning(self.main_window, "Ошибка", "Выбранная папка не существует")
            return

        # Проверяем что это действительно папка
        if not os.path.isdir(folder_path):
            QtWidgets.QMessageBox.warning(self.main_window, "Ошибка", "Выбранный путь не является папкой")
            return

        # Проверяем права доступа на запись (для добавления файлов)
        try:
            # Пробуем создать тестовый файл чтобы проверить права записи
            test_file = os.path.join(folder_path, "test_write_permission.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except PermissionError:
            reply = QtWidgets.QMessageBox.question(
                self.main_window,
                "Ограниченный доступ",
                f"У вас нет прав на запись в папку:\n{folder_path}\n\n"
                f"Вы сможете просматривать файлы, но не добавлять новые.\n"
                f"Продолжить открытие проекта?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
            )
            if reply == QtWidgets.QMessageBox.No:
                return

        # Проверяем что эта папка еще не добавлена как проект
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            existing_path = item.data(QtCore.Qt.UserRole)
            if existing_path == folder_path:
                QtWidgets.QMessageBox.information(
                    self.main_window,
                    "Информация",
                    f"Проект '{os.path.basename(folder_path)}' уже открыт"
                )
                return

        # Добавляем папку как проект
        self.add_project_to_tree(folder_path)

        QtWidgets.QMessageBox.information(
            self.main_window,
            "Успех",
            f"Проект '{os.path.basename(folder_path)}' успешно открыт!\n"
            f"Путь: {folder_path}"
        )

    def get_visualization_type_for_file(self, file_path):
        """Определяет тип визуализации для файла событий"""
        # Проверяем, какой тип визуализации сейчас используется для этого файла
        if hasattr(self.main_window, 'loaded_files') and file_path in self.main_window.loaded_files:
            # Берем первый объект из файла и смотрим его тип визуализации
            obj_ids = self.main_window.loaded_files[file_path]
            if obj_ids and obj_ids[0] in self.main_window.glWidget.objects:
                obj = self.main_window.glWidget.objects[obj_ids[0]]
                if hasattr(obj, 'data') and 'visualization' in obj.data:
                    return obj.data['visualization']

        # По умолчанию возвращаем сферы
        return "spheres"