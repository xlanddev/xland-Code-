import sys
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel,
    QStackedWidget, QGraphicsDropShadowEffect, QHBoxLayout, QLineEdit,
    QTextEdit, QFrame, QToolBar, QMessageBox, QColorDialog, QFontDialog,
    QGraphicsScene, QGraphicsView, QGraphicsProxyWidget, QGraphicsItem,
    QGraphicsRectItem, QFileDialog
)
from PyQt6.QtGui import QColor, QFont, QAction, QIcon, QPainter, QBrush, QPen, QPixmap
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QPointF, QSize, QObject, pyqtSignal, QUrl, QSettings
import os

# --- Constants ---
GRID_SIZE = 20
DEFAULT_APP_BG = "#1e1e1e"
DEFAULT_APP_FG = "#f0f0f0"
DEFAULT_PANEL_BG = "#252526"
DEFAULT_DESIGN_BG = "#333333"
DEFAULT_BUTTON_COLOR = "#4CAF50"
DEFAULT_HIGHLIGHT_COLOR = "#4fc3f7"

# --- Helper Classes ---

class DraggableGraphicsProxyWidget(QGraphicsProxyWidget):
    clicked = pyqtSignal(QGraphicsItem)
    dragging = pyqtSignal()
    drag_finished = pyqtSignal()

    def __init__(self, widget=None, parent=None):
        super().__init__(widget, parent)
        self.widget = widget
        self._is_dragging = False
        self._drag_start_pos = QPointF()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True)
        self.widget.installEventFilter(self)

    def eventFilter(self, watched: QObject, event):
        if event.type() == 13: # QEvent.Type.MouseButtonPress
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_start_pos = event.scenePos()
                self._is_dragging = True
                self.clicked.emit(self)
                event.accept()
                return True
        elif event.type() == 15: # QEvent.Type.MouseButtonRelease
            if event.button() == Qt.MouseButton.LeftButton:
                self._is_dragging = False
                self.snap_to_grid()
                self.drag_finished.emit()
                event.accept()
                return True
        elif event.type() == 14: # QEvent.Type.MouseMove
            if self._is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
                # Calculate movement relative to scene
                current_pos = event.scenePos()
                delta = current_pos - self._drag_start_pos
                self._drag_start_pos = current_pos # Update for next move event

                # Apply movement to the proxy item
                self.setPos(self.pos() + delta)
                self.dragging.emit()
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update the underlying widget's geometry
            if self.widget:
                scene_pos = self.scenePos()
                self.widget.move(int(scene_pos.x()), int(scene_pos.y()))

        return super().itemChange(change, value)

    def snap_to_grid(self):
        new_x = round(self.scenePos().x() / GRID_SIZE) * GRID_SIZE
        new_y = round(self.scenePos().y() / GRID_SIZE) * GRID_SIZE
        self.setPos(new_x, new_y)
        if self.widget:
            self.widget.move(int(new_x), int(new_y))

    def remove(self):
        self.widget.deleteLater()
        self.scene().removeItem(self)
        self.deleteLater()


class DesignView(QGraphicsView):
    item_selected = pyqtSignal(QGraphicsItem)
    item_drag_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag) # Enable rubber band selection

        self.grid_pen = QPen(QColor("#444444"), 0.5)
        self.grid_pen.setStyle(Qt.PenStyle.DotLine)

        self.selection_pen = QPen(QColor(DEFAULT_HIGHLIGHT_COLOR), 2)
        self.selection_pen.setStyle(Qt.PenStyle.DashLine)

        self.setMouseTracking(True)
        self.current_selected_item = None

    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)
        # Draw grid
        left = int(rect.left() - (rect.left() % GRID_SIZE))
        top = int(rect.top() - (rect.top() % GRID_SIZE))
        right = int(rect.right() + (GRID_SIZE - (rect.right() % GRID_SIZE)))
        bottom = int(rect.bottom() + (GRID_SIZE - (rect.bottom() % GRID_SIZE)))

        painter.setPen(self.grid_pen)
        for x in range(left, right, GRID_SIZE):
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        for y in range(top, bottom, GRID_SIZE):
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            items = self.scene.selectedItems()
            if items:
                self.current_selected_item = items[0]
                self.item_selected.emit(self.current_selected_item)
                self.update_selection_rect()
            else:
                self.current_selected_item = None
                self.item_selected.emit(None)
                self.scene.clearSelection() # Clear selection if clicking empty space

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            if self.current_selected_item:
                if isinstance(self.current_selected_item, DraggableGraphicsProxyWidget):
                    self.current_selected_item.remove()
                    self.current_selected_item = None
                    self.item_selected.emit(None)
                    self.item_drag_finished.emit() # Emit for code update
        super().keyPressEvent(event)

    def update_selection_rect(self):
        if self.current_selected_item:
            self.current_selected_item.setPen(self.selection_pen)
            self.current_selected_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True) # Ensure it's movable
        else:
            self.scene.clearSelection()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.item_drag_finished.emit() # Emit when dragging stops/selection changes


class XLandStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XLAND STUDIO")
        self.setGeometry(50, 50, 1280, 800)
        self.setStyleSheet(f"background-color: {DEFAULT_APP_BG}; color: {DEFAULT_APP_FG};")

        self.settings = QSettings("XLand", "XLandStudio")
        self.project_path = self.settings.value("project/path", "")
        self.app_elements = []
        self.generated_code = ""
        self.current_selected_proxy = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        self.create_main_menu()
        self.create_about_page()
        self.create_app_page()
        self.create_game_page() # Placeholder

        self.stacked_widget.setCurrentIndex(0)

        self.load_settings()

    def load_settings(self):
        if self.project_path and os.path.exists(self.project_path):
            self.load_project(self.project_path)
        else:
            self.clear_design_area() # Start with a clean slate

    def save_settings(self):
        self.settings.setValue("project/path", self.project_path)

    def create_main_menu(self):
        main_menu_widget = QWidget()
        main_menu_layout = QVBoxLayout(main_menu_widget)
        main_menu_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("XLAND STUDIO")
        title_label.setFont(QFont("Arial", 40, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"color: {DEFAULT_HIGHLIGHT_COLOR}; margin-bottom: 50px;")
        main_menu_layout.addWidget(title_label)

        self.btn_create_app = self.create_animated_button("ساخت برنامه", lambda: self.stacked_widget.setCurrentIndex(2))
        self.btn_create_game = self.create_animated_button("ساخت بازی", lambda: self.stacked_widget.setCurrentIndex(3))
        self.btn_about = self.create_animated_button("درباره ما", lambda: self.stacked_widget.setCurrentIndex(1))
        self.btn_exit = self.create_animated_button("خروج", self.close)

        main_menu_layout.addWidget(self.btn_create_app)
        main_menu_layout.addWidget(self.btn_create_game)
        main_menu_layout.addWidget(self.btn_about)
        main_menu_layout.addWidget(self.btn_exit)

        self.stacked_widget.addWidget(main_menu_widget)

    def create_about_page(self):
        about_widget = QWidget()
        about_layout = QVBoxLayout(about_widget)
        about_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        about_title = QLabel("درباره ما")
        about_title.setFont(QFont("Arial", 30, QFont.Weight.Bold))
        about_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_title.setStyleSheet(f"color: {DEFAULT_HIGHLIGHT_COLOR}; margin-bottom: 30px;")
        about_layout.addWidget(about_title)

        about_text = QLabel(
            "این برنامه توسط تیم xland ساخته شده است و برای اینکه شما بتوانید اولین بازی یا برنامه تون را بسازید.\n\n"
            "ما تلاش کرده‌ایم تا محیطی کاربرپسند و قدرتمند برای شروع کار شما فراهم کنیم."
        )
        about_text.setFont(QFont("Arial", 16))
        about_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_text.setWordWrap(True)
        about_text.setStyleSheet(f"color: {DEFAULT_APP_FG}; padding: 20px; max-width: 600px;")
        about_layout.addWidget(about_text)

        self.btn_back_to_menu_about = self.create_animated_button("بازگشت به منو", lambda: self.stacked_widget.setCurrentIndex(0))
        about_layout.addWidget(self.btn_back_to_menu_about)

        self.stacked_widget.addWidget(about_widget)

    def create_app_page(self):
        self.app_page_widget = QWidget()
        app_page_layout = QHBoxLayout(self.app_page_widget)
        app_page_layout.setContentsMargins(10, 10, 10, 10)
        app_page_layout.setSpacing(10)

        # --- Left Panel: Element Palette ---
        left_panel = QWidget()
        left_panel.setFixedWidth(250)
        left_panel.setStyleSheet(f"background-color: {DEFAULT_PANEL_BG}; border-radius: 8px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(15)

        palette_title = QLabel("کتابخانه المان‌ها")
        palette_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        palette_title.setStyleSheet(f"color: {DEFAULT_HIGHLIGHT_COLOR};")
        left_layout.addWidget(palette_title)

        self.btn_add_label = self.create_side_button("اضافه کردن لیبل", lambda: self.add_element("QLabel", "لیبل جدید"))
        self.btn_add_button = self.create_side_button("اضافه کردن دکمه", lambda: self.add_element("QPushButton", "دکمه جدید"))
        self.btn_add_input = self.create_side_button("اضافه کردن فیلد متن", lambda: self.add_element("QLineEdit", "فیلد متن"))
        self.btn_add_text_edit = self.create_side_button("اضافه کردن ناحیه متن", lambda: self.add_element("QTextEdit", "ناحیه متن"))

        left_layout.addWidget(self.btn_add_label)
        left_layout.addWidget(self.btn_add_button)
        left_layout.addWidget(self.btn_add_input)
        left_layout.addWidget(self.btn_add_text_edit)
        left_layout.addStretch()

        # --- Center Panel: Design Area ---
        self.design_container = QWidget()
        design_container_layout = QVBoxLayout(self.design_container)
        design_container_layout.setContentsMargins(0,0,0,0)

        self.design_view = DesignView(self.design_container)
        self.design_view.setStyleSheet(f"background-color: {DEFAULT_DESIGN_BG}; border-radius: 8px; border: 1px solid #555;")
        self.design_view.setMinimumSize(600, 500)
        self.design_view.item_selected.connect(self.on_item_selected)
        self.design_view.item_drag_finished.connect(self.update_code_and_props)

        design_container_layout.addWidget(self.design_view)

        # --- Right Panel: Properties & Code ---
        right_panel = QWidget()
        right_panel.setFixedWidth(400)
        right_panel.setStyleSheet(f"background-color: {DEFAULT_PANEL_BG}; border-radius: 8px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        # Properties Editor
        props_title = QLabel("ویژگی‌های المان")
        props_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        props_title.setStyleSheet(f"color: {DEFAULT_HIGHLIGHT_COLOR};")
        right_layout.addWidget(props_title)

        self.prop_widget = QWidget()
        self.prop_layout = QVBoxLayout(self.prop_widget)
        self.prop_layout.setContentsMargins(0, 0, 0, 0)
        self.prop_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Text Property
        self.text_prop_layout = QHBoxLayout()
        self.text_prop_layout.addWidget(QLabel("متن:"))
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text")
        self.text_input.textChanged.connect(self.update_text_property)
        self.text_prop_layout.addWidget(self.text_input)
        self.prop_layout.addLayout(self.text_prop_layout)

        # Style Properties (Color, Font)
        style_props_layout = QHBoxLayout()
        self.btn_change_color = QPushButton("رنگ")
        self.btn_change_color.setFixedWidth(80)
        self.btn_change_color.clicked.connect(self.change_element_color)
        self.btn_change_font = QPushButton("فونت")
        self.btn_change_font.setFixedWidth(80)
        self.btn_change_font.clicked.connect(self.change_element_font)
        style_props_layout.addWidget(self.btn_change_color)
        style_props_layout.addWidget(self.btn_change_font)
        style_props_layout.addStretch()
        self.prop_layout.addLayout(style_props_layout)

        self.prop_layout.addStretch()
        right_layout.addWidget(self.prop_widget)

        # Code Editor
        code_editor_title = QLabel("کد پایتون (PyQt6):")
        code_editor_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        code_editor_title.setStyleSheet(f"color: {DEFAULT_HIGHLIGHT_COLOR}; margin-top: 20px;")
        right_layout.addWidget(code_editor_title)

        self.code_editor = QTextEdit()
        self.code_editor.setFont(QFont("Consolas", 10))
        self.code_editor.setStyleSheet(f"background-color: #1f1f1f; color: #d4d4d4; border: 1px solid #555; border-radius: 4px;")
        self.code_editor.setReadOnly(True)
        right_layout.addWidget(self.code_editor)

        # Toolbar
        self.app_toolbar = QToolBar("App Actions")
        self.app_toolbar.setStyleSheet(f"QToolBar {{ background: {DEFAULT_PANEL_BG}; border-bottom: 1px solid #555; padding: 5px; }}")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.app_toolbar)

        back_action = QAction(QIcon(), "بازگشت به منو", self)
        back_action.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.app_toolbar.addAction(back_action)

        save_action = QAction(QIcon(), "ذخیره پروژه", self)
        save_action.triggered.connect(self.save_project_dialog)
        self.app_toolbar.addAction(save_action)

        load_action = QAction(QIcon(), "باز کردن پروژه", self)
        load_action.triggered.connect(self.load_project_dialog)
        self.app_toolbar.addAction(load_action)

        clear_action = QAction(QIcon(), "پاک کردن طراحی", self)
        clear_action.triggered.connect(self.clear_design_area)
        self.app_toolbar.addAction(clear_action)

        run_action = QAction(QIcon(), "اجرای برنامه", self)
        run_action.triggered.connect(self.run_generated_app)
        self.app_toolbar.addAction(run_action)

        app_page_layout.addWidget(left_panel)
        app_page_layout.addWidget(self.design_container)
        app_page_layout.addWidget(right_panel)

        self.stacked_widget.addWidget(self.app_page_widget)
        self.update_code_editor()

    def create_game_page(self):
        placeholder_game = QWidget()
        placeholder_game_layout = QVBoxLayout(placeholder_game)
        placeholder_game_layout.addWidget(QLabel("صفحه ساخت بازی (در حال توسعه...)"))
        placeholder_game_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stacked_widget.addWidget(placeholder_game)

    def add_element(self, element_type, default_name):
        widget = None
        if element_type == "QLabel":
            widget = QLabel(default_name)
            widget.setFont(QFont("Arial", 12))
            widget.setStyleSheet("color: #f0f0f0; background-color: transparent; border: none;")
            widget.adjustSize()
        elif element_type == "QPushButton":
            widget = QPushButton(default_name)
            widget.setFixedSize(120, 40)
            widget.setStyleSheet(f"background-color: {DEFAULT_BUTTON_COLOR}; color: white; border-radius: 5px;")
        elif element_type == "QLineEdit":
            widget = QLineEdit(default_name)
            widget.setFixedSize(200, 35)
            widget.setStyleSheet(f"background-color: #333; color: #f0f0f0; border: 1px solid #555; border-radius: 4px; padding: 5px;")
        elif element_type == "QTextEdit":
            widget = QTextEdit(default_name)
            widget.setFixedSize(200, 100)
            widget.setStyleSheet(f"background-color: #333; color: #f0f0f0; border: 1px solid #555; border-radius: 4px; padding: 5px;")

        if widget:
            # Add to scene and make draggable
            proxy = DraggableGraphicsProxyWidget(widget, self.design_view.scene)
            proxy.setPos(self.get_initial_position())
            proxy.clicked.connect(self.on_item_selected)
            proxy.drag_finished.connect(self.update_code_and_props)
            self.design_view.scene.addItem(proxy)

            # Store element info
            element_info = {
                "type": element_type,
                "name": default_name, # Will be made unique later
                "proxy": proxy,
                "widget": widget
            }
            self.app_elements.append(element_info)
            self.update_element_names()
            self.update_code_editor()
            self.on_item_selected(proxy) # Select the newly added item

    def get_initial_position(self):
        # Try to place items in a non-overlapping way, snapping to grid
        x, y = 20, 20
        if self.app_elements:
            last_element = self.app_elements[-1]["proxy"]
            last_rect = last_element.mapRectToScene(last_element.boundingRect())
            x = last_rect.left()
            y = last_rect.bottom() + GRID_SIZE
            # Ensure it's on grid
            x = round(x / GRID_SIZE) * GRID_SIZE
            y = round(y / GRID_SIZE) * GRID_SIZE
        return QPointF(x, y)

    def update_element_names(self):
        # Ensure unique names for code generation
        counts = {}
        for element in self.app_elements:
            base_name = element["name"].split('_')[0]
            if base_name not in counts:
                counts[base_name] = 0
            else:
                counts[base_name] += 1
            element["name"] = f"{base_name}_{counts[base_name]}"

    def update_code_and_props(self):
        self.update_element_names()
        self.update_code_editor()
        self.update_properties_panel(self.current_selected_proxy)

    def update_code_editor(self):
        code = f"""import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QLineEdit, QTextEdit
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import QRect

class GeneratedAppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("برنامه ساخته شده")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: {DEFAULT_APP_BG}; color: {DEFAULT_APP_FG};")

"""
        for i, element in enumerate(self.app_elements):
            widget = element["widget"]
            name = element["name"] # Use the unique name

            widget_code = f"        self.{name} = {element['type']}(self)\n"

            # Text
            if hasattr(widget, "text"):
                text = widget.text()
                escaped_text = text.replace('"', '\\"') # Escape double quotes
                widget_code += f'        self.{name}.setText("{escaped_text}")\n'

            # Geometry
            geom = widget.geometry()
            widget_code += f"        self.{name}.setGeometry(QRect({geom.x()}, {geom.y()}, {geom.width()}, {geom.height()}))\n"

            # Stylesheet (extracting colors and font info)
            style_sheet = widget.styleSheet()
            if style_sheet:
                # Attempt to parse color and font from stylesheet for more structured code
                color = None
                bg_color = None
                font_size = None
                font_family = widget.font().family() # Default font family

                # Simple parsing for common properties
                style_lines = style_sheet.split(';')
                for line in style_lines:
                    if ':' in line:
                        prop, val = line.split(':', 1)
                        prop = prop.strip().lower()
                        val = val.strip()

                        if prop == 'color':
                            color = val
                        elif prop == 'background-color':
                            bg_color = val
                        elif prop == 'font-size':
                            try:
                                if 'px' in val: val = val.replace('px', '')
                                font_size = int(float(val))
                            except ValueError: pass
                        elif prop == 'font-family':
                            font_family = val.replace('"', '') # Remove quotes if present

                if color:
                     widget_code += f'        self.{name}.setStyleSheet(f\'color: {color}; ...\') # Partial style\n'
                if bg_color:
                     widget_code += f'        self.{name}.setStyleSheet(f\'background-color: {bg_color}; ...\') # Partial style\n'

                # Add full stylesheet if complex, or append parsed properties
                if not (color or bg_color or font_size): # If no specific props parsed, use full sheet
                    escaped_style = style_sheet.replace('"', '\\"')
                    widget_code += f'        self.{name}.setStyleSheet("{escaped_style}")\n'
                else:
                    # Append parsed styles to the existing stylesheet, or set them directly
                    current_style = self.get_widget_style(widget)
                    if color and f'color: {color}' not in current_style:
                        current_style += f'color: {color};\n'
                    if bg_color and f'background-color: {bg_color}' not in current_style:
                        current_style += f'background-color: {bg_color};\n'
                    widget_code += f'        self.{name}.setStyleSheet("{current_style}")\n'


            # Font
            font = widget.font()
            if font.family() != "Arial" or font.pointSize() != 10: # Don't add default font
                 widget_code += f'        self.{name}.setFont(QFont("{font.family()}", {font.pointSize()}))\n'


            code += widget_code + "\n"

        code += """
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GeneratedAppWindow()
    window.show()
    sys.exit(app.exec())
"""
        self.generated_code = code
        self.code_editor.setPlainText(code)

    def get_widget_style(self, widget):
        # Helper to get combined style, prioritizing parsed properties
        base_style = widget.styleSheet()
        style_dict = {}
        if base_style:
            for rule in base_style.split(';'):
                if ':' in rule:
                    prop, val = rule.split(':', 1)
                    style_dict[prop.strip().lower()] = val.strip()

        # Add or override properties from parsed values
        if self.current_selected_proxy:
            selected_widget = self.current_selected_proxy.widget
            if selected_widget:
                color = selected_widget.palette().color(widget.foregroundRole())
                bg_color = selected_widget.palette().color(widget.backgroundRole())
                font = selected_widget.font()

                style_dict['color'] = color.name() if color.isValid() else DEFAULT_APP_FG
                style_dict['background-color'] = bg_color.name() if bg_color.isValid() else DEFAULT_DESIGN_BG
                style_dict['font-family'] = f'"{font.family()}"'
                style_dict['font-size'] = f'{font.pointSize()}pt' # PyQt uses pt

        # Reconstruct stylesheet string
        new_style_list = [f"{prop}: {val}" for prop, val in style_dict.items()]
        return "; ".join(new_style_list) + ";"


    def on_item_selected(self, item):
        self.current_selected_proxy = item
        self.update_properties_panel(item)
        self.design_view.update_selection_rect() # Update visual selection

    def update_properties_panel(self, item):
        if isinstance(item, DraggableGraphicsProxyWidget):
            widget = item.widget
            # Text Property
            if hasattr(widget, "text"):
                self.text_input.setText(widget.text())
                self.text_input.setEnabled(True)
            else:
                self.text_input.setText("")
                self.text_input.setEnabled(False)

            # Enable style buttons
            self.btn_change_color.setEnabled(True)
            self.btn_change_font.setEnabled(True)

        else: # No item selected or invalid item
            self.text_input.setText("")
            self.text_input.setEnabled(False)
            self.btn_change_color.setEnabled(False)
            self.btn_change_font.setEnabled(False)

    def update_text_property(self, text):
        if self.current_selected_proxy and hasattr(self.current_selected_proxy.widget, "setText"):
            self.current_selected_proxy.widget.setText(text)
            self.current_selected_proxy.widget.adjustSize() # Adjust size if text changes
            self.update_code_editor()

    def change_element_color(self):
        if self.current_selected_proxy:
            widget = self.current_selected_proxy.widget
            current_color = widget.palette().color(widget.foregroundRole()) # Text color
            if current_color.isValid():
                 color = QColorDialog.getColor(current_color, self, "انتخاب رنگ متن")
            else:
                 color = QColorDialog.getColor(QColor(DEFAULT_APP_FG), self, "انتخاب رنگ متن")

            if color.isValid():
                widget.setTextColor(color) # For QLabel, QPushButton, etc.
                widget.setPalette(widget.palette()) # Update palette
                widget.setStyleSheet(f"color: {color.name()};")
                self.update_code_editor()

    def change_element_font(self):
         if self.current_selected_proxy:
            widget = self.current_selected_proxy.widget
            font = widget.font()
            font, valid = QFontDialog.getFont(font, self, "انتخاب فونت")
            if valid:
                widget.setFont(font)
                widget.update() # Force repaint
                self.update_code_editor()

    def clear_design_area(self):
        if self.current_selected_proxy:
            self.current_selected_proxy.setSelected(False)
            self.current_selected_proxy = None
            self.update_properties_panel(None)

        # Remove all items from the scene
        for item in self.design_view.scene.items():
            if isinstance(item, DraggableGraphicsProxyWidget):
                item.remove()
            else:
                self.design_view.scene.removeItem(item)

        self.app_elements = []
        self.update_code_editor()

    def save_project_dialog(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره پروژه",
            self.project_path if self.project_path else ".",
            "JSON Files (*.json);;All Files (*)"
        )
        if path:
            if not path.endswith(".json"):
                path += ".json"
            self.project_path = path
            self.save_project(path)
            self.save_settings() # Save the last used path

    def save_project(self, path):
        project_data = {
            "elements": [],
            "window_geometry": {
                "x": self.geometry().x(),
                "y": self.geometry().y(),
                "width": self.width(),
                "height": self.height()
            },
            "design_view_rect": {
                "x": self.design_view.rect().x(),
                "y": self.design_view.rect().y(),
                "width": self.design_view.rect().width(),
                "height": self.design_view.rect().height()
            }
        }

        for element in self.app_elements:
            widget = element["widget"]
            proxy = element["proxy"]
            geom = widget.geometry()
            style = widget.styleSheet()
            font = widget.font()

            element_data = {
                "type": element["type"],
                "name": element["name"],
                "text": widget.text() if hasattr(widget, "text") else "",
                "geometry": {"x": geom.x(), "y": geom.y(), "width": geom.width(), "height": geom.height()},
                "style_sheet": style,
                "font": {"family": font.family(), "point_size": font.pointSize()}
            }
            project_data["elements"].append(element_data)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "ذخیره موفق", f"پروژه با موفقیت در {path} ذخیره شد.")
        except Exception as e:
            QMessageBox.critical(self, "خطای ذخیره", f"خطا در ذخیره پروژه:\n{e}")

    def load_project_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "باز کردن پروژه",
            self.project_path if self.project_path else ".",
            "JSON Files (*.json);;All Files (*)"
        )
        if path:
            self.project_path = path
            self.load_project(path)
            self.save_settings() # Save the last opened path

    def load_project(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            self.clear_design_area() # Clear current design

            # Load elements
            for elem_data in project_data.get("elements", []):
                widget = None
                element_type = elem_data["type"]
                default_name = elem_data["name"] # Use saved name

                if element_type == "QLabel":
                    widget = QLabel()
                    widget.setFont(QFont(elem_data["font"]["family"], elem_data["font"]["point_size"]))
                    widget.setStyleSheet(elem_data["style_sheet"])
                    widget.setText(elem_data["text"])
                    widget.adjustSize()
                elif element_type == "QPushButton":
                    widget = QPushButton()
                    widget.setFixedSize(elem_data["geometry"]["width"], elem_data["geometry"]["height"])
                    widget.setStyleSheet(elem_data["style_sheet"])
                    widget.setText(elem_data["text"])
                elif element_type == "QLineEdit":
                    widget = QLineEdit()
                    widget.setFixedSize(elem_data["geometry"]["width"], elem_data["geometry"]["height"])
                    widget.setStyleSheet(elem_data["style_sheet"])
                    widget.setText(elem_data["text"])
                elif element_type == "QTextEdit":
                    widget = QTextEdit()
                    widget.setFixedSize(elem_data["geometry"]["width"], elem_data["geometry"]["height"])
                    widget.setStyleSheet(elem_data["style_sheet"])
                    widget.setText(elem_data["text"])

                if widget:
                    proxy = DraggableGraphicsProxyWidget(widget, self.design_view.scene)
                    geom = elem_data["geometry"]
                    proxy.setPos(geom["x"], geom["y"])
                    proxy.widget.setGeometry(geom["x"], geom["y"], geom["width"], geom["height"])
                    proxy.clicked.connect(self.on_item_selected)
                    proxy.drag_finished.connect(self.update_code_and_props)
                    self.design_view.scene.addItem(proxy)

                    element_info = {
                        "type": element_type,
                        "name": default_name,
                        "proxy": proxy,
                        "widget": widget
                    }
                    self.app_elements.append(element_info)

            # Update unique names after loading
            self.update_element_names()
            self.update_code_editor()
            QMessageBox.information(self, "باز کردن موفق", f"پروژه با موفقیت از {path} بارگذاری شد.")

        except Exception as e:
            QMessageBox.critical(self, "خطای باز کردن", f"خطا در بارگذاری پروژه:\n{e}")


    def run_generated_app(self):
        if not self.generated_code:
            QMessageBox.warning(self, "کد خالی", "هیچ کدی برای اجرا وجود ندارد. لطفا ابتدا المان‌هایی را طراحی کنید.")
            return

        # Save the current project state to a temporary file to ensure the generated code uses the latest state
        temp_project_file = "temp_project_state.json"
        self.save_project(temp_project_file)

        # Create a temporary Python file
        temp_script_file = "generated_app_run.py"
        try:
            with open(temp_script_file, "w", encoding="utf-8") as f:
                f.write(self.generated_code)

            # Execute the temporary Python script
            import subprocess
            # Use sys.executable to ensure the same Python interpreter is used
            process = subprocess.Popen([sys.executable, temp_script_file], creationflags=subprocess.CREATE_NEW_CONSOLE)
            # We don't wait for the process to finish, as the generated app runs independently.

            QMessageBox.information(self, "اجرای برنامه", "برنامه شما در یک پنجره جدید در حال اجراست.")

        except Exception as e:
            QMessageBox.critical(self, "خطا در اجرا", f"خطا در اجرای برنامه:\n{e}")
        finally:
            # Clean up temporary files if they exist
            if os.path.exists(temp_script_file):
                os.remove(temp_script_file)
            if os.path.exists(temp_project_file):
                # Decide whether to keep or remove temp project state
                # os.remove(temp_project_file)
                pass # Keep it for debugging maybe


    def create_animated_button(self, text, action=None):
        button = QPushButton(text)
        button.setFixedSize(220, 55)
        button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 15px;
                padding: 12px 25px;
                border: none;
                transition: background-color 0.3s ease;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        if action:
            button.clicked.connect(action)

        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(15)
        shadow_effect.setXOffset(3)
        shadow_effect.setYOffset(3)
        shadow_effect.setColor(QColor(0, 0, 0, 150))
        button.setGraphicsEffect(shadow_effect)

        return button

    def create_side_button(self, text, action):
        button = QPushButton(text)
        button.setFont(QFont("Arial", 12))
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {DEFAULT_PANEL_BG};
                color: #f0f0f0;
                border-radius: 5px;
                padding: 8px 15px;
                border: 1px solid #666;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: #6a6a6a;
                border: 1px solid #888;
            }}
            QPushButton:pressed {{
                background-color: #7a7a7a;
            }}
        """)
        button.clicked.connect(action)
        return button


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Set application-wide settings for style and behavior
    app.setStyleSheet(f"""
        QWidget {{
            font-family: Arial;
            font-size: 10pt;
        }}
        QLabel {{
            color: {DEFAULT_APP_FG};
        }}
        QPushButton {{
            background-color: #505050;
            color: {DEFAULT_APP_FG};
            border-radius: 4px;
            padding: 5px;
        }}
        QLineEdit, QTextEdit {{
            background-color: #333;
            color: {DEFAULT_APP_FG};
            border: 1px solid #555;
            border-radius: 4px;
            padding: 5px;
        }}
        QTextEdit {{
            background-color: #282828; /* Slightly darker for code editor */
        }}
        QToolBar {{
            background: {DEFAULT_PANEL_BG};
            border-bottom: 1px solid #555;
            padding: 5px;
        }}
        QToolBar QAction {{
            padding: 5px;
            border: none;
            background: transparent;
        }}
        QToolBar QAction:hover {{
            background: #555;
        }}
    """)
    window = XLandStudio()
    window.show()
    sys.exit(app.exec())
