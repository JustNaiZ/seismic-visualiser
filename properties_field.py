import json
import os
import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from OpenGL.arrays import vbo

class PropertiesField(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # Храним свойства для каждого файла
        self.file_properties = {}
        # Храним ссылки на виджеты для каждого файла
        self.widget_references = {}

        # Файл для сохранения настроек
        self.settings_file = self.get_settings_file_path()

        self.init_ui()
        self.load_properties_settings()

    def init_ui(self):
        """Инициализация интерфейса свойств"""
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок панели свойств
        header_label = QtWidgets.QLabel("Свойства")
        header_label.setStyleSheet("""
            QLabel {
                background-color: #e0e0e0;
                padding: 5px;
                font-weight: bold;
                border-bottom: 1px solid #cccccc;
            }
        """)
        main_layout.addWidget(header_label)

        # ВКЛАДКИ ФАЙЛОВ
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        # Создаем начальную вкладку с сообщением по умолчанию
        self.default_tab = QtWidgets.QWidget()
        default_layout = QtWidgets.QVBoxLayout(self.default_tab)

        default_message = QtWidgets.QLabel("Выберите файл событий для настройки свойств")
        default_message.setAlignment(QtCore.Qt.AlignCenter)
        default_message.setStyleSheet("color: gray; font-style: italic; padding: 50px;")
        default_layout.addWidget(default_message)

        self.tab_widget.addTab(self.default_tab, "Свойства")
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

    def show_event_properties(self, file_path, visualization_type):
        """Показывает свойства для выбранного файла событий"""
        try:
            # Удаляем вкладку по умолчанию если она есть
            if self.tab_widget.count() == 1 and self.tab_widget.widget(0) == self.default_tab:
                self.tab_widget.removeTab(0)

            # Проверяем, есть ли уже вкладка для этого файла
            tab_index = self.find_tab_index(file_path)

            if tab_index == -1:
                # Создаем новую вкладку
                self.create_tab(file_path, visualization_type)
            else:
                # Переключаемся на существующую вкладку
                self.tab_widget.setCurrentIndex(tab_index)
                # Обновляем содержимое вкладки
                self.update_tab_content(tab_index, file_path, visualization_type)

        except Exception as e:
            print(f"Ошибка при показе свойств: {e}")
            import traceback
            traceback.print_exc()

    def find_tab_index(self, file_path):
        """Находит индекс вкладки для файла"""
        for i in range(self.tab_widget.count()):
            tab_widget = self.tab_widget.widget(i)
            if hasattr(tab_widget, 'file_path') and tab_widget.file_path == file_path:
                return i
        return -1

    def create_tab(self, file_path, visualization_type):
        """Создает новую вкладку для файла"""
        try:
            # Создаем виджет для вкладки
            tab_content = QtWidgets.QScrollArea()
            tab_content.setWidgetResizable(True)

            content_widget = QtWidgets.QWidget()
            tab_content.setWidget(content_widget)

            # Сохраняем ссылки
            tab_content.content_widget = content_widget
            tab_content.file_path = file_path
            tab_content.visualization_type = visualization_type

            layout = QtWidgets.QVBoxLayout(content_widget)
            layout.setContentsMargins(5, 5, 5, 5)

            # Загружаем или создаем свойства
            if file_path not in self.file_properties:
                self.initialize_file_properties(file_path, visualization_type)

            # Создаем свойства для этой вкладки
            self.create_properties_widgets(layout, file_path, visualization_type)

            # Добавляем вкладку
            file_name = os.path.basename(file_path)
            self.tab_widget.addTab(tab_content, file_name)
            self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)

        except Exception as e:
            print(f"Ошибка создания вкладки: {e}")
            import traceback
            traceback.print_exc()

    def update_tab_content(self, tab_index, file_path, visualization_type):
        """Обновляет содержимое существующей вкладки"""
        try:
            tab_widget = self.tab_widget.widget(tab_index)
            if not hasattr(tab_widget, 'content_widget'):
                return

            # Очищаем старый layout
            old_layout = tab_widget.content_widget.layout()
            if old_layout:
                while old_layout.count():
                    child = old_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

            # Создаем новые виджеты
            self.create_properties_widgets(old_layout, file_path, visualization_type)

        except Exception as e:
            print(f"Ошибка обновления вкладки: {e}")

    def get_settings_file_path(self):
        """Возвращает путь к файлу настроек свойств"""
        settings_dir = os.path.join(os.path.expanduser("~"), ".seismic_visualiser")
        if not os.path.exists(settings_dir):
            os.makedirs(settings_dir)
        return os.path.join(settings_dir, "properties_settings.json")

    def load_properties_settings(self):
        """Загружает настройки свойств из файла"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)

                # Восстанавливаем настройки для каждого файла
                for file_path, settings in saved_settings.items():
                    # Проверяем существует ли файл
                    if os.path.exists(file_path):
                        # Конвертируем ключи из строк в числа для energy_ranges
                        if 'energy_ranges' in settings:
                            energy_ranges = settings['energy_ranges']
                            new_energy_ranges = {}
                            for key_str, value in energy_ranges.items():
                                try:
                                    key_int = int(key_str)
                                    new_energy_ranges[key_int] = value
                                except (ValueError, TypeError):
                                    continue
                            settings['energy_ranges'] = new_energy_ranges

                        self.file_properties[file_path] = settings
                        print(f"Загружены настройки для: {os.path.basename(file_path)}")

            else:
                print("Файл настроек свойств не найден, будут использованы настройки по умолчанию")

        except Exception as e:
            print(f"Ошибка загрузки настроек свойств: {e}")

    def save_properties_settings(self):
        """Сохраняет настройки свойств в файл"""
        try:
            # Создаем копию без ссылок на виджеты (только данные)
            settings_to_save = {}
            for file_path, properties in self.file_properties.items():
                if os.path.exists(file_path):
                    settings_to_save[file_path] = properties

            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_to_save, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"Ошибка сохранения настроек свойств: {e}")

    def initialize_file_properties(self, file_path, visualization_type):
        """Инициализирует свойства для файла"""
        if file_path in self.file_properties:
            return

        # Создаем настройки по умолчанию
        self.file_properties[file_path] = {
            'type': visualization_type,
            'energy_ranges': {
                100000000000: {
                    'color': [1.0, 0.0, 0.0],
                    'opacity': 1.0,  # Начальная прозрачность
                    'visualization': visualization_type
                },
                1000000000: {
                    'color': [1.0, 0.5, 0.0],
                    'opacity': 1.0,
                    'visualization': visualization_type
                },
                100000000: {
                    'color': [1.0, 1.0, 0.0],
                    'opacity': 1.0,
                    'visualization': visualization_type
                },
                1000000: {
                    'color': [0.0, 1.0, 0.0],
                    'opacity': 1.0,
                    'visualization': visualization_type
                },
                1000: {
                    'color': [0.0, 0.0, 1.0],
                    'opacity': 1.0,
                    'visualization': visualization_type
                },
                0: {
                    'color': [0.5, 0.5, 0.5],
                    'opacity': 1.0,
                    'visualization': visualization_type
                }
            }
        }

        self.save_properties_settings()

    def create_properties_widgets(self, layout, file_path, visualization_type):
        """Создает виджеты свойств для вкладки"""
        try:
            # Информация о файле
            file_info_label = QtWidgets.QLabel(f"Файл: {os.path.basename(file_path)}")
            file_info_label.setStyleSheet("color: gray; font-size: 12px; font-weight: bold; margin-bottom: 10px;")
            layout.addWidget(file_info_label)

            # УДАЛЕН СЛАЙДЕР ГЛОБАЛЬНОЙ ПРОЗРАЧНОСТИ

            # Добавляем разделитель
            separator = QtWidgets.QFrame()
            separator.setFrameShape(QtWidgets.QFrame.HLine)
            separator.setFrameShadow(QtWidgets.QFrame.Sunken)
            layout.addWidget(separator)

            # Заголовок для диапазонов
            ranges_label = QtWidgets.QLabel("Настройки диапазонов энергии:")
            ranges_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px; margin-bottom: 10px;")
            layout.addWidget(ranges_label)

            # ДИАПАЗОНЫ ЭНЕРГИИ - КАЖДЫЙ С СВОИМ ТИПОМ ВИЗУАЛИЗАЦИИ И ПРОЗРАЧНОСТЬЮ
            energy_ranges = [
                (100000000000, "Высокая энергия (>100 млрд)"),
                (1000000000, "Средняя энергия (1 млрд - 100 млрд)"),
                (100000000, "Низкая энергия (100 млн - 1 млрд)"),
                (1000000, "Очень низкая энергия (1 млн - 100 млн)"),
                (1000, "Минимальная энергия (1 тыс - 1 млн)"),
                (0, "Базовая энергия (<1 тыс)")
            ]

            props = self.file_properties[file_path]['energy_ranges']

            for i, (energy_threshold, label_text) in enumerate(energy_ranges):
                if energy_threshold not in props:
                    default_props = {
                        'color': [0.5, 0.5, 0.5],
                        'opacity': 1.0,
                        'visualization': visualization_type
                    }
                    self.add_energy_range_controls(layout, energy_threshold, label_text, i, default_props, file_path)
                else:
                    self.add_energy_range_controls(layout, energy_threshold, label_text, i, props[energy_threshold],
                                                   file_path)

            layout.addStretch()

        except Exception as e:
            print(f"Ошибка создания виджетов свойств: {e}")
            import traceback
            traceback.print_exc()

    def add_energy_range_controls(self, layout, energy_threshold, label_text, index, props, file_path):
        """Добавляет элементы управления для диапазона энергии"""
        # Разделитель между диапазонами
        if index > 0:
            separator = QtWidgets.QFrame()
            separator.setFrameShape(QtWidgets.QFrame.HLine)
            separator.setFrameShadow(QtWidgets.QFrame.Sunken)
            layout.addWidget(separator)

        # Метка диапазона
        range_label = QtWidgets.QLabel(label_text)
        range_label.setStyleSheet("font-weight: bold; margin-top: 3px;")
        layout.addWidget(range_label)

        # ВЫПАДАЮЩИЙ СПИСОК для выбора типа визуализации этого диапазона
        viz_layout = QtWidgets.QHBoxLayout()
        viz_label = QtWidgets.QLabel("Тип визуализации:")
        viz_layout.addWidget(viz_label)

        viz_combo = QtWidgets.QComboBox()
        viz_combo.addItem("Сферы", "spheres")
        viz_combo.addItem("Пляжные мячики", "beach_balls")
        viz_combo.addItem("Точки", "points")

        # Устанавливаем текущий тип визуализации для этого диапазона
        current_viz = props.get('visualization', 'spheres')
        idx = viz_combo.findData(current_viz)
        if idx >= 0:
            viz_combo.setCurrentIndex(idx)

        # Обработчик изменения
        viz_combo.currentIndexChanged.connect(
            lambda idx, eth=energy_threshold, fp=file_path, combo=viz_combo:
            self.on_range_visualization_changed(eth, combo.itemData(idx), fp)
        )

        viz_layout.addWidget(viz_combo)
        viz_layout.addStretch()
        layout.addLayout(viz_layout)

        # ВЫБОР ЦВЕТА для диапазона
        color_layout = QtWidgets.QHBoxLayout()
        color_label = QtWidgets.QLabel("Цвет:")
        color_layout.addWidget(color_label)

        color_picker = QtWidgets.QPushButton()
        color_picker.setFixedSize(40, 20)

        color = props['color']
        color_str = f"background-color: rgb({int(color[0] * 255)}, {int(color[1] * 255)}, {int(color[2] * 255)}); border: 1px solid black;"
        color_picker.setStyleSheet(color_str)

        color_picker.clicked.connect(
            lambda checked, eth=energy_threshold, fp=file_path, btn=color_picker:
            self.pick_color(eth, fp, btn)
        )
        color_layout.addWidget(color_picker)

        color_layout.addStretch()
        layout.addLayout(color_layout)

        # СЛАЙДЕР ПРОЗРАЧНОСТИ для диапазона (ТОЛЬКО ДЛЯ ЭТОГО ДИАПАЗОНА!)
        opacity_layout = QtWidgets.QHBoxLayout()
        opacity_label = QtWidgets.QLabel("Прозрачность:")
        opacity_layout.addWidget(opacity_label)

        opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        opacity_slider.setRange(0, 100)
        opacity_slider.setSingleStep(10)
        opacity_slider.setPageStep(10)
        opacity_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        opacity_slider.setTickInterval(10)

        # ⚠️ ИСПРАВЛЕНИЕ: правильно получаем сохраненную прозрачность
        saved_opacity = props.get('opacity', 1.0)
        opacity_percent = int(saved_opacity * 100)
        opacity_slider.setValue(opacity_percent)
        opacity_slider.setProperty("snapToTicks", True)

        opacity_label_display = QtWidgets.QLabel(f"{opacity_percent}%")
        opacity_label_display.setFixedWidth(30)

        opacity_slider.valueChanged.connect(
            lambda value, eth=energy_threshold, fp=file_path, lbl=opacity_label_display:
            self.on_range_opacity_changed(eth, value, fp, lbl)
        )
        opacity_slider.setFixedWidth(150)
        opacity_layout.addWidget(opacity_slider)
        opacity_layout.addWidget(opacity_label_display)

        opacity_layout.addStretch()
        layout.addLayout(opacity_layout)

        # Сохраняем ссылки на виджеты
        if file_path not in self.widget_references:
            self.widget_references[file_path] = {}

        if energy_threshold not in self.widget_references[file_path]:
            self.widget_references[file_path][energy_threshold] = {}

        self.widget_references[file_path][energy_threshold]['viz_combo'] = viz_combo
        self.widget_references[file_path][energy_threshold]['color_button'] = color_picker
        self.widget_references[file_path][energy_threshold]['opacity_slider'] = opacity_slider
        self.widget_references[file_path][energy_threshold]['opacity_label'] = opacity_label_display

    def change_visualization(self, file_path, new_visualization_type):
        """Меняет основной тип визуализации файла - СОХРАНЯЕТ ПРОЗРАЧНОСТЬ"""
        try:
            print(f"=== СМЕНА ОСНОВНОЙ ВИЗУАЛИЗАЦИИ ===")
            print(f"Файл: {os.path.basename(file_path)}")
            print(f"Новый тип: {new_visualization_type}")

            if file_path not in self.file_properties:
                return

            # Сохраняем текущие прозрачности всех диапазонов
            saved_opacities = {}
            if 'energy_ranges' in self.file_properties[file_path]:
                for energy_threshold, range_props in self.file_properties[file_path]['energy_ranges'].items():
                    saved_opacities[energy_threshold] = range_props.get('opacity', 1.0)

            # Обновляем основной тип визуализации файла
            self.file_properties[file_path]['type'] = new_visualization_type

            # Обновляем тип визуализации во всех диапазонах, но сохраняем их прозрачность
            if 'energy_ranges' in self.file_properties[file_path]:
                for energy_threshold in self.file_properties[file_path]['energy_ranges']:
                    self.file_properties[file_path]['energy_ranges'][energy_threshold][
                        'visualization'] = new_visualization_type
                    # Восстанавливаем сохраненную прозрачность
                    if energy_threshold in saved_opacities:
                        self.file_properties[file_path]['energy_ranges'][energy_threshold]['opacity'] = saved_opacities[
                            energy_threshold]

            self.save_properties_settings()

            # Обновляем интерфейс
            self.update_tab_for_file(file_path, new_visualization_type)

            # Применяем изменения к сцене
            if self.main_window and hasattr(self.main_window, 'reload_file_with_settings'):
                self.main_window.reload_file_with_settings(file_path)

        except Exception as e:
            print(f"Ошибка при смене визуализации: {e}")
            import traceback
            traceback.print_exc()

    def update_tab_for_file(self, file_path, visualization_type):
        """Обновляет вкладку для файла"""
        tab_index = self.find_tab_index(file_path)
        if tab_index != -1:
            self.update_tab_content(tab_index, file_path, visualization_type)

    # В классе PropertiesField добавьте:
    def apply_properties(self, file_path):
        """Применяет изменения свойств - перезагружает файл"""
        try:
            if not file_path or not self.main_window:
                return

            # Просто перезагружаем файл
            if file_path in self.main_window.loaded_files:
                print(f"🔄 Перезагрузка файла для применения свойств...")
                # Сначала выключаем
                if file_path.lower().endswith('.evp'):
                    self.main_window.toggle_evp_file(file_path, False)
                    # Затем включаем
                    self.main_window.toggle_evp_file(file_path, True)
                elif file_path.lower().endswith('.dxf'):
                    self.main_window.toggle_dxf_file(file_path, False)
                    self.main_window.toggle_dxf_file(file_path, True)
                # Добавьте обработку других типов файлов при необходимости

            print(f"✅ Свойства применены")

        except Exception as e:
            print(f"❌ Ошибка при применении свойств: {e}")

    def on_range_visualization_changed(self, energy_threshold, visualization_type, file_path):
        """Обработчик изменения типа визуализации для диапазона энергии"""
        try:
            print(f"=== ИЗМЕНЕНИЕ ВИЗУАЛИЗАЦИИ ДИАПАЗОНА ===")
            print(f"Диапазон: {energy_threshold}")
            print(f"Новый тип: {visualization_type}")
            print(f"Файл: {os.path.basename(file_path)}")

            if file_path not in self.file_properties:
                return

            # Обновляем тип визуализации для этого диапазона
            if ('energy_ranges' in self.file_properties[file_path] and
                    energy_threshold in self.file_properties[file_path]['energy_ranges']):

                # Сохраняем текущую прозрачность перед изменением типа
                current_opacity = self.file_properties[file_path]['energy_ranges'][energy_threshold].get('opacity', 1.0)

                # Обновляем тип визуализации, но сохраняем цвет и прозрачность
                self.file_properties[file_path]['energy_ranges'][energy_threshold]['visualization'] = visualization_type
                # Прозрачность остается той же!

                print(f"✅ Тип изменен на {visualization_type}, прозрачность сохранена: {current_opacity}")

                self.save_properties_settings()

                # Применяем изменения
                if self.main_window and hasattr(self.main_window, 'reload_file_with_settings'):
                    self.main_window.reload_file_with_settings(file_path)

        except Exception as e:
            print(f"Ошибка при изменении визуализации диапазона: {e}")
            import traceback
            traceback.print_exc()

    def pick_color(self, energy_threshold, file_path, color_button=None):
        """Выбор цвета для диапазона энергии с обновлением кнопки"""
        if file_path not in self.file_properties:
            return

        props = self.file_properties[file_path]['energy_ranges']
        if energy_threshold not in props:
            return

        current_color = props[energy_threshold]['color']
        current_qcolor = QtGui.QColor(
            int(current_color[0] * 255),
            int(current_color[1] * 255),
            int(current_color[2] * 255)
        )

        color = QtWidgets.QColorDialog.getColor(current_qcolor, self, f"Выберите цвет для диапазона")

        if color.isValid():
            new_color = [color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0]
            props[energy_threshold]['color'] = new_color

            # Обновляем кнопку цвета если она передана
            if color_button:
                color_str = f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); border: 1px solid black;"
                color_button.setStyleSheet(color_str)
            # Или находим кнопку в виджетах если не передана
            elif (file_path in self.widget_references and
                  energy_threshold in self.widget_references[file_path] and
                  'color_button' in self.widget_references[file_path][energy_threshold]):
                btn = self.widget_references[file_path][energy_threshold]['color_button']
                color_str = f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); border: 1px solid black;"
                btn.setStyleSheet(color_str)

            self.save_properties_settings()

            # Применяем изменения через reload_file_with_settings (как раньше)
            if self.main_window and hasattr(self.main_window, 'reload_file_with_settings'):
                self.main_window.reload_file_with_settings(file_path)

    def close_tab(self, index):
        """Закрывает вкладку"""
        self.tab_widget.removeTab(index)

        # Если вкладок не осталось, показываем вкладку по умолчанию
        if self.tab_widget.count() == 0:
            self.tab_widget.addTab(self.default_tab, "Свойства")

        # Если нет активных свойств, скрываем всю панель
        if self.is_properties_empty() and self.main_window:
            self.main_window.hide_properties_field()

    def hide_properties_field(self):
        """Скрывает всю панель свойств"""
        self.hide()

    def is_properties_empty(self):
        """Проверяет, есть ли активные вкладки свойств"""
        return self.tab_widget.count() == 0 or (
                self.tab_widget.count() == 1 and
                self.tab_widget.widget(0) == self.default_tab
        )

    def on_range_opacity_changed(self, energy_threshold, value, file_path, label):
        """Обработчик изменения прозрачности диапазона"""
        # ДИСКРЕТНЫЕ ЗНАЧЕНИЯ
        discrete_value = (value // 10) * 10
        if value != discrete_value:
            # Обновляем слайдер до дискретного значения
            if (file_path in self.widget_references and
                    energy_threshold in self.widget_references[file_path] and
                    'opacity_slider' in self.widget_references[file_path][energy_threshold]):
                self.widget_references[file_path][energy_threshold]['opacity_slider'].setValue(discrete_value)
            return

        opacity = discrete_value / 100.0

        if (file_path in self.file_properties and
                'energy_ranges' in self.file_properties[file_path] and
                energy_threshold in self.file_properties[file_path]['energy_ranges']):

            # Сохраняем прозрачность для этого диапазона
            self.file_properties[file_path]['energy_ranges'][energy_threshold]['opacity'] = opacity
            label.setText(f"{discrete_value}%")

            print(f"✅ Прозрачность диапазона {energy_threshold} сохранена: {opacity}")

            self.save_properties_settings()

            # Определяем тип визуализации для этого диапазона
            visualization_type = self.file_properties[file_path]['energy_ranges'][energy_threshold].get('visualization',
                                                                                                        'spheres')

            print(f"🎯 Тип визуализации для диапазона {energy_threshold}: {visualization_type}")

            # В зависимости от типа визуализации используем разные методы
            if visualization_type == "spheres":
                # Для сфер используем специальный метод обновления
                self.update_sphere_opacity(file_path, energy_threshold, opacity)
            else:
                # Для мячиков и точек используем перезагрузку файла
                if self.main_window and hasattr(self.main_window, 'reload_file_with_settings'):
                    self.main_window.reload_file_with_settings(file_path)

    def update_sphere_opacity(self, file_path, energy_threshold, opacity):
        """Обновляет прозрачность сфер для конкретного диапазона"""
        try:
            print(f"🔄 Обновление прозрачности сфер для диапазона {energy_threshold}: {opacity}")

            if not self.main_window or file_path not in self.main_window.loaded_files:
                return

            obj_ids = self.main_window.loaded_files[file_path]

            for obj_id in obj_ids:
                if obj_id in self.main_window.glWidget.objects:
                    obj = self.main_window.glWidget.objects[obj_id]

                    # Проверяем что это событие нужного типа
                    if obj.obj_type == "event":
                        # Получаем энергию объекта
                        energy = obj.data.get("energy", 0)
                        try:
                            energy_float = float(energy) if energy else 0.0
                        except (ValueError, TypeError):
                            energy_float = 0.0

                        # Проверяем попадает ли в наш диапазон
                        thresholds = sorted(self.file_properties[file_path]['energy_ranges'].keys(), reverse=True)
                        for thresh in thresholds:
                            if energy_float >= thresh:
                                if thresh == energy_threshold:
                                    # Это наш объект - обновляем его прозрачность
                                    self._update_single_sphere_opacity(obj, opacity)
                                break

            # Обновляем сцену
            self.main_window.glWidget.updateGL()

        except Exception as e:
            print(f"❌ Ошибка обновления прозрачности сфер: {e}")
            import traceback
            traceback.print_exc()

    def _update_single_sphere_opacity(self, obj, opacity):
        """Обновляет прозрачность одной сферы"""
        try:
            print(
                f"🎨 Обновление сферы {obj.id}: старая прозрачность={obj.current_opacity if hasattr(obj, 'current_opacity') else 'нет'}, новая={opacity}")

            # Обновляем сохраненную прозрачность
            obj.current_opacity = opacity

            # Если у объекта есть base_color, обновляем его альфа-канал
            if hasattr(obj, 'base_color'):
                if len(obj.base_color) == 4:
                    obj.base_color[3] = opacity
                elif len(obj.base_color) == 3:
                    obj.base_color.append(opacity)

            # Получаем текущие цвета VBO
            if hasattr(obj.mesh, 'colorsFacesVBO') and obj.mesh.colorsFacesVBO:
                try:
                    # Получаем данные из VBO
                    colors_data = obj.mesh.colorsFacesVBO.data

                    # Проверяем структуру данных
                    if colors_data is not None:
                        # Преобразуем в numpy массив
                        colors_array = np.array(colors_data, dtype=np.float32)

                        # Меняем альфа-канал у каждого 4-го элемента (RGBA формат)
                        colors_array[3::4] = opacity

                        # Создаем новый VBO
                        new_vbo = vbo.VBO(colors_array)

                        # Заменяем старый VBO
                        obj.mesh.colorsFacesVBO.delete()
                        obj.mesh.colorsFacesVBO = new_vbo

                        print(f"✅ VBO сферы {obj.id} обновлен с прозрачностью {opacity}")
                    else:
                        print(f"⚠️ VBO данных нет для сферы {obj.id}")

                except Exception as e:
                    print(f"⚠️ Ошибка обновления VBO: {e}")
                    # Попробуем альтернативный способ
                    self._recreate_sphere_with_opacity(obj, opacity)
            else:
                print(f"⚠️ У сферы {obj.id} нет colorsFacesVBO")
                self._recreate_sphere_with_opacity(obj, opacity)

        except Exception as e:
            print(f"❌ Ошибка обновления сферы: {e}")
            import traceback
            traceback.print_exc()

    def _recreate_sphere_with_opacity(self, obj, opacity):
        """Пересоздает сферу с новой прозрачностью"""
        try:
            print(f"🔄 Пересоздание сферы {obj.id} с прозрачностью {opacity}")

            # Получаем параметры объекта
            x, y, z = obj.location
            event_type = obj.data.get("type", "unknown")
            energy = obj.data.get("energy", 1.0)

            # Получаем базовый цвет
            if hasattr(obj, 'base_color'):
                base_color = obj.base_color[:3]  # Берем только RGB
            else:
                base_color = [1.0, 0.0, 0.0]  # По умолчанию красный

            # Формируем новый цвет с прозрачностью
            rgba_color = base_color + [opacity]

            # Очищаем старый объект
            if hasattr(obj, 'mesh'):
                self.main_window.cleanup_mesh_vbo(obj.mesh)

            # Получаем ID объекта
            obj_id = obj.id

            # Удаляем старый объект из GLWidget
            del self.main_window.glWidget.objects[obj_id]

            # Создаем новую сферу с обновленной прозрачностью
            new_obj = self.main_window.glWidget.add_object_event(x, y, z, event_type, energy, rgba_color)

            # Сохраняем тип визуализации
            new_obj.data['visualization'] = 'spheres'

            # Сохраняем тот же ID
            self.main_window.glWidget.objects[obj_id] = new_obj

            print(f"✅ Сфера {obj_id} пересоздана с прозрачностью {opacity}")

        except Exception as e:
            print(f"❌ Ошибка пересоздания сферы: {e}")