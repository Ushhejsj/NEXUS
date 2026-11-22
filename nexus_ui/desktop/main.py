
import json
import os
import sys
import math
import random
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app_scanner import find_in_cache

import psutil

from PySide6.QtCore import Qt, QTimer, Signal, QEvent, QPoint, QPointF, QRect
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QRadialGradient,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QApplication,
    QDoubleSpinBox,
    QSlider,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QProgressBar,
    QGraphicsBlurEffect,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


STYLE = """
QMainWindow {
    background-color: transparent;
    color: #eeeaf5;
    font-family: "Segoe UI";
}

QFrame#Sidebar {
    background-color: transparent;
    border-right: 1px solid #34313e;
}

QFrame#RightPanel {
    background-color: transparent;
    border-left: 1px solid #34313e;
}

QLabel#Logo {
    color: #e5d5ff;
    font-size: 27px;
    font-weight: 700;
    letter-spacing: 5px;
}

QLabel#Subtitle {
    color: #92869f;
    font-size: 9px;
    letter-spacing: 2px;
}

QLabel#PageTitle {
    color: #f4effb;
    font-size: 27px;
    font-weight: 600;
}

QLabel#Eyebrow {
    color: #b9a1dc;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
}

QLabel#Muted {
    color: #958da1;
    font-size: 11px;
}

QLabel#PanelTitle {
    color: #b9a5d5;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
}

QLabel#PanelValue {
    color: #f2eafa;
    font-size: 23px;
    font-weight: 600;
}

QLabel#Status {
    color: #d0b8ef;
    font-size: 10px;
    letter-spacing: 1px;
}

QPushButton {
    background-color: transparent;
    color: #aaa2b5;
    border: none;
    border-radius: 9px;
    padding: 12px;
    text-align: left;
    font-size: 12px;
}

QPushButton:hover {
    background-color: rgba(52, 48, 63, 105);
    color: #eee3ff;
}

QPushButton:checked {
    background-color: rgba(57, 50, 68, 125);
    color: #e5d2ff;
    border-left: 3px solid #b99ae9;
    padding-left: 9px;
}

QPushButton#QuickButton {
    background-color: rgba(48, 45, 57, 105);
    border: 1px solid #40394a;
    border-radius: 12px;
    color: #e7dff0;
    padding: 12px 6px;
    text-align: center;
    font-size: 11px;
}

QPushButton#QuickButton:hover {
    background-color: rgba(64, 54, 77, 145);
    border: 1px solid #8066a3;
}

QPushButton#UtilityButton {
    background-color: rgba(48, 45, 57, 105);
    border: 1px solid #40394a;
    border-radius: 10px;
    color: #d5c5e9;
    font-size: 17px;
    padding: 10px;
    text-align: center;
}

QPushButton#UtilityButton:hover {
    background-color: rgba(69, 57, 81, 160);
}

QFrame#Panel {
    background-color: transparent;
    border: 1px solid #393442;
    border-radius: 15px;
}

QFrame#CorePanel {
    background-color: transparent;
    border: 1px solid #3b3347;
    border-radius: 18px;
}

QFrame#MonitorCard {
    background-color: rgba(28, 30, 38, 45);
    border: 1px solid rgba(190, 185, 210, 45);
    border-radius: 12px;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QWidget#SettingsContent,
QWidget#ApplicationsContainer,
QWidget#MacrosContainer {
    background-color: transparent;
}

QLineEdit {
    background-color: rgba(48, 44, 57, 105);
    border: 1px solid #494052;
    border-radius: 13px;
    padding: 13px 16px;
    color: #f2eafa;
    font-size: 12px;
    selection-background-color: #765b99;
}

QLineEdit:focus {
    border: 1px solid #a88aca;
}

QProgressBar {
    background-color: rgba(57, 52, 65, 100);
    border: none;
    border-radius: 4px;
    height: 7px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #b49ad8;
    border-radius: 4px;
}
"""





from components.glass_frame import GlassFrame


from components.nexus_orb import NexusOrb



from components.system_graph import SystemGraph





from panels.sidebar import SidebarMixin
class NexusWindow(SidebarMixin, QMainWindow):


    def __init__(self):
        super().__init__()

        self.setWindowTitle("NEXUS Desktop")
        self.resize(1500, 900)
        self.setMinimumSize(1100, 700)

        self.setStyleSheet(STYLE)

        self.settings_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "nexus_settings.json"
        )

        self.saved_settings = self.load_settings()

        self.nav_buttons = []
        self.style_buttons = {}

        root = QWidget()
        self.setCentralWidget(root)

        self.background_label = QLabel(root)
        self.background_label.setObjectName("AppBackground")
        self.background_blur_effect = QGraphicsBlurEffect(self.background_label)
        self.background_label.setGraphicsEffect(self.background_blur_effect)
        self.background_label.setGeometry(root.rect())
        self.background_label.lower()

        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.create_sidebar(layout)
        self.create_workspace(layout)
        app = QApplication.instance()
        app.installEventFilter(self)
        self.apply_saved_background()


        # РћСЃС‚Р°Р»СЊРЅРѕР№ РєРѕРґ __init__

    def set_background_blur(self, value):
        self.background_blur_label.setText(f"Размытие фона: {value}")
        self.background_blur_effect.setBlurRadius(value)
        self.saved_settings["background_blur"] = value
        self.save_settings()

    def set_background_dim(self, value):
        self.background_dim_label.setText(f"Затемнение фона: {value}%")
        self.saved_settings["background_dim"] = value
        self.update_background()
        self.save_settings()
    def update_background(self):
        if not hasattr(self, "background_label"):
            return

        root = self.centralWidget()
        if root is None:
            return

        self.background_label.setGeometry(root.rect())

        pixmap = getattr(self, "background_source_pixmap", QPixmap())
        if pixmap.isNull():
            return

        size = root.size()
        scaled = pixmap.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )

        x = max(0, (scaled.width() - size.width()) // 2)
        y = max(0, (scaled.height() - size.height()) // 2)

        rendered = scaled.copy(x, y, size.width(), size.height())
        painter = QPainter(rendered)
        dim = int(self.saved_settings.get("background_dim", 0))
        if dim > 0:
            painter.fillRect(rendered.rect(), QColor(0, 0, 0, int(dim * 255 / 100)))
        painter.end()
        self.background_label.setPixmap(rendered)

    def set_background_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose background image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )

        if not path:
            return

        pixmap = QPixmap(path)
        if pixmap.isNull():
            return

        self.background_source_pixmap = pixmap
        self.saved_settings["background_path"] = path
        self.update_background()
        self.save_settings()

    def apply_saved_background(self):
        path = self.saved_settings.get("background_path", "")
        if path and os.path.isfile(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.background_source_pixmap = pixmap
                self.update_background()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_background()
    def load_settings(self):
        if not os.path.exists(self.settings_path):
            return {}
        try:
            with open(self.settings_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                print("[NEXUS] Settings loaded.")
                return data
        except (OSError, json.JSONDecodeError) as error:
            print(f"[NEXUS] Settings load error: {error}")
        return {}


    def save_settings(self):
        if not hasattr(self, "orb"):
            return

        settings = dict(getattr(self, "saved_settings", {}))
        settings.update({
            "primary_color": self.orb.primary_color.name(),
            "secondary_color": self.orb.secondary_color.name(),
            "glow_intensity": self.orb.glow_intensity,
            "animation_speed": self.orb.animation_speed,
            "particle_count": self.orb.particle_count,
            "orb_scale": self.orb.orb_scale,
            "style": self.orb.style,
        })

        self.saved_settings = settings

        try:
            with open(self.settings_path, "w", encoding="utf-8") as file:
                json.dump(settings, file, indent=4, ensure_ascii=False)
        except OSError as error:
            print(f"[NEXUS] Settings save error: {error}")

    def apply_saved_settings(self):
        """РџСЂРёРјРµРЅРµРЅРёРµ СЃРѕС…СЂР°РЅС‘РЅРЅС‹С… РЅР°СЃС‚СЂРѕРµРє Рє AI Core."""

        settings = self.saved_settings

        primary = QColor(settings.get("primary_color", "#B995E8"))
        secondary = QColor(settings.get("secondary_color", "#F1C2A9"))

        if primary.isValid() and secondary.isValid():
            self.orb.set_colors(primary, secondary)

        try:
            self.orb.set_glow(
                float(settings.get("glow_intensity", 1.0))
            )
            self.orb.set_animation_speed(
                float(settings.get("animation_speed", 1.0))
            )
            self.orb.set_particle_count(
                int(settings.get("particle_count", 180))
            )
            self.orb.set_orb_scale(
                float(settings.get("orb_scale", 1.0))
            )
            self.orb.set_style(
                str(settings.get("style", "ENERGY"))
            )
        except (ValueError, TypeError):
            print("[NEXUS] Invalid settings values.")

        print("[NEXUS] AI Core settings applied.")




    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        collapsed = self.sidebar_collapsed
        self.sidebar.setFixedWidth(64 if collapsed else 190)

        self.sidebar_layout.setContentsMargins(
            6 if collapsed else 12, 14, 6 if collapsed else 12, 14
        )
        self.sidebar_toggle.setText("\u203a" if collapsed else "\u2039   \u0421\u0412\u0415\u0420\u041d\u0423\u0422\u042c")

        for widget in self.sidebar_text_widgets:
            widget.setVisible(not collapsed)

        for icon_label, name_label in zip(
            self.nav_icon_labels, self.nav_name_labels
        ):
            icon_label.setVisible(True)
            name_label.setVisible(not collapsed)

        self.sidebar_premium_label.setVisible(not collapsed)
        self.sidebar_settings_icon.setVisible(True)
        self.sidebar_settings_label.setVisible(not collapsed)

    def create_workspace(self, parent):
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(27, 24, 27, 20)
        layout.setSpacing(15)

        header = QHBoxLayout()

        self.page_title = QLabel("\u0414\u043e\u0431\u0440\u044b\u0439 \u0434\u0435\u043d\u044c")
        self.page_title.setObjectName("PageTitle")

        self.status_label = QLabel("NEXUS ONLINE")
        self.status_label.setObjectName("Status")

        header.addWidget(self.page_title)
        header.addStretch()
        header.addWidget(self.status_label)

        layout.addLayout(header)

        self.page_stack = QStackedWidget()
        layout.addWidget(self.page_stack, 1)

        home_page = QWidget()
        home_layout = QVBoxLayout(home_page)
        home_layout.setContentsMargins(0, 0, 0, 0)
        home_layout.setSpacing(15)

        greeting = QLabel("\u0412\u0430\u0448 \u043f\u0435\u0440\u0441\u043e\u043d\u0430\u043b\u044c\u043d\u044b\u0439 AI-\u0446\u0435\u043d\u0442\u0440")
        greeting.setObjectName("Eyebrow")
        home_layout.addWidget(greeting)

        description = QLabel("\u0412\u0441\u0451 \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043a\u043e\u043c\u043f\u044c\u044e\u0442\u0435\u0440\u043e\u043c \u2014 \u0432 \u043e\u0434\u043d\u043e\u043c \u043c\u0435\u0441\u0442\u0435.")
        description.setObjectName("Muted")
        home_layout.addWidget(description)

        # Р¦РµРЅС‚СЂР°Р»СЊРЅР°СЏ РїР°РЅРµР»СЊ AI Core
        core_panel = GlassFrame()
        core_panel.setObjectName("CorePanel")

        core_layout = QVBoxLayout(core_panel)
        core_layout.setContentsMargins(15, 5, 15, 10)
        core_layout.setSpacing(0)

        self.orb = NexusOrb()

        # Р’РѕСЃСЃС‚Р°РЅР°РІР»РёРІР°РµРј РЅР°СЃС‚СЂРѕР№РєРё РґРѕ РѕС‚РѕР±СЂР°Р¶РµРЅРёСЏ СЃС„РµСЂС‹
        self.apply_saved_settings()

        core_layout.addWidget(self.orb, 1)

        core_name = QLabel("N E X U S   C O R E")
        core_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        core_name.setStyleSheet("""
            color: #d6c0ed;
            font-size: 11px;
            font-weight: 600;
        """)

        self.core_status = QLabel("SLEEP  В·  AWAITING COMMAND")
        self.core_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.core_status.setStyleSheet("""
            color: #9586a8;
            font-size: 9px;
            letter-spacing: 2px;
        """)

        self.orb.stateChanged.connect(self.update_core_status)

        core_layout.addWidget(core_name)
        core_layout.addSpacing(5)
        core_layout.addWidget(self.core_status)

        # РљРЅРѕРїРєРё СЃРѕСЃС‚РѕСЏРЅРёР№ AI Core
        preview_row = QHBoxLayout()
        preview_row.setSpacing(6)

        preview_states = [
            ("SLEEP", "SLEEP"),
            ("WAKE UP", "WAKE_UP"),
            ("LISTEN", "LISTENING"),
            ("THINK", "THINKING"),
            ("EXECUTE", "EXECUTING"),
        ]

        for label, state in preview_states:
            button = QPushButton(label)
            button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(48, 44, 57, 105);
                    color: #cbb8e0;
                    border: 1px solid #494052;
                    border-radius: 7px;
                    padding: 6px 8px;
                    font-size: 9px;
                }
                QPushButton:hover {
                    background-color: rgba(73, 59, 89, 155);
                    border: 1px solid #a88aca;
                }
            """)

            button.clicked.connect(
                lambda checked=False, s=state: self.preview_core_state(s)
            )

            preview_row.addWidget(button)

        core_layout.addLayout(preview_row)

        # Р“Р°Р»РµСЂРµСЏ СЃС‚РёР»РµР№ NEXUS CORE

        home_layout.addWidget(core_panel, 4)

        # РњРѕРЅРёС‚РѕСЂРёРЅРі СЃРёСЃС‚РµРјС‹
        system_page = QWidget()
        system_layout = QVBoxLayout(system_page)
        system_layout.setContentsMargins(0, 0, 0, 0)
        system_layout.setSpacing(15)

        self.monitor_labels = {}
        cards = QHBoxLayout()
        cards.setSpacing(12)

        cpu_card = self.create_monitor_card(
            "CPU / RAM UTILIZATION",
            "вЂ”",
            "РћР¶РёРґР°РЅРёРµ РїРѕРґРєР»СЋС‡РµРЅРёСЏ РјРѕРЅРёС‚РѕСЂРёРЅРіР°",
        )

        disk_card = self.create_monitor_card(
            "DISK / NETWORK",
            "вЂ”",
            "РћР¶РёРґР°РЅРёРµ РїРѕРґРєР»СЋС‡РµРЅРёСЏ РјРѕРЅРёС‚РѕСЂРёРЅРіР°",
        )

        gpu_card = self.create_monitor_card(
            "NVIDIA GPU",
            "GPU  ?",
            "???????? ?????? NVIDIA",
        )

        cards.addWidget(cpu_card)
        cards.addWidget(disk_card)
        cards.addWidget(gpu_card)

        system_layout.addLayout(cards)

        self.system_graph = SystemGraph()
        system_layout.addWidget(self.system_graph)

        # APPLICATIONS PAGE
        applications_page = QWidget()
        applications_layout = QVBoxLayout(applications_page)
        applications_layout.setContentsMargins(0, 0, 0, 0)
        applications_layout.setSpacing(14)

        apps_heading = QLabel("APPLICATION LIBRARY")
        apps_heading.setObjectName("Eyebrow")
        applications_layout.addWidget(apps_heading)

        apps_description = QLabel(
            "????????????? ?????????? Windows ? ????? ? ??????? ??????."
        )
        apps_description.setObjectName("Muted")
        applications_layout.addWidget(apps_description)

        self.app_search = QLineEdit()
        self.app_search.setPlaceholderText("????? ??????????...")
        self.app_search.setMinimumHeight(40)
        self.app_search.textChanged.connect(self.filter_applications)
        applications_layout.addWidget(self.app_search)

        self.apps_scroll = QScrollArea()
        self.apps_scroll.setWidgetResizable(True)
        self.apps_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.apps_scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.apps_scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.apps_container = QWidget()
        self.apps_container.setObjectName("ApplicationsContainer")
        self.apps_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.apps_list_layout = QVBoxLayout(self.apps_container)
        self.apps_list_layout.setSpacing(8)
        self.apps_list_layout.setContentsMargins(2, 2, 8, 2)

        self.apps_scroll.setWidget(self.apps_container)
        applications_layout.addWidget(self.apps_scroll, 1)

        self.application_entries = {}
        self.app_catalog = {}

        # MACROS PAGE
        macros_page = QWidget()
        macros_layout = QVBoxLayout(macros_page)
        macros_layout.setContentsMargins(0, 0, 0, 0)
        macros_layout.setSpacing(14)

        macros_heading = QLabel("AUTOMATION CENTER")
        macros_heading.setObjectName("Eyebrow")
        macros_layout.addWidget(macros_heading)

        macros_description = QLabel(
            "???????? ???????? ? ???????? ????????? ?????????? ????? ?????????."
        )
        macros_description.setObjectName("Muted")
        macros_layout.addWidget(macros_description)

        self.macro_name_input = QLineEdit()
        self.macro_name_input.setPlaceholderText("???????? ????????")
        self.macro_name_input.setMinimumHeight(40)
        macros_layout.addWidget(self.macro_name_input)

        self.macro_apps_expanded = False

        self.macro_apps_toggle = QPushButton("?  APPLICATIONS")
        self.macro_apps_toggle.setMinimumHeight(40)
        self.macro_apps_toggle.setCheckable(True)
        self.macro_apps_toggle.clicked.connect(
            self.toggle_macro_app_picker
        )
        macros_layout.addWidget(self.macro_apps_toggle)

        self.macro_app_picker = QWidget()
        macro_picker_layout = QVBoxLayout(self.macro_app_picker)
        macro_picker_layout.setContentsMargins(0, 0, 0, 0)
        macro_picker_layout.setSpacing(8)

        self.macro_app_search = QLineEdit()
        self.macro_app_search.setPlaceholderText("Search applications...")
        self.macro_app_search.setMinimumHeight(38)
        self.macro_app_search.textChanged.connect(
            self.filter_macro_app_list
        )
        macro_picker_layout.addWidget(self.macro_app_search)

        self.macro_app_list = QListWidget()
        self.macro_app_list.setMinimumHeight(150)
        self.macro_app_list.setMaximumHeight(230)
        macro_picker_layout.addWidget(self.macro_app_list)

        self.macro_app_list.itemChanged.connect(
            self.sync_macro_selection
        )

        self.macro_app_picker.setVisible(False)
        macros_layout.addWidget(self.macro_app_picker)

        order_heading = QLabel("LAUNCH ORDER")
        order_heading.setObjectName("Eyebrow")
        macros_layout.addWidget(order_heading)

        self.macro_selected_list = QListWidget()
        self.macro_selected_list.setMinimumHeight(75)
        self.macro_selected_list.setMaximumHeight(125)
        macros_layout.addWidget(self.macro_selected_list)

        order_buttons = QHBoxLayout()

        move_up_button = QPushButton("?")
        move_up_button.clicked.connect(
            lambda: self.move_macro_app(-1)
        )
        order_buttons.addWidget(move_up_button)

        move_down_button = QPushButton("?")
        move_down_button.clicked.connect(
            lambda: self.move_macro_app(1)
        )
        order_buttons.addWidget(move_down_button)

        macros_layout.addLayout(order_buttons)

        delay_row = QHBoxLayout()
        delay_label = QLabel("DELAY BETWEEN APPS")
        delay_label.setObjectName("Muted")
        delay_row.addWidget(delay_label)

        self.macro_delay_input = QDoubleSpinBox()
        self.macro_delay_input.setRange(0, 60)
        self.macro_delay_input.setDecimals(1)
        self.macro_delay_input.setSingleStep(0.5)
        self.macro_delay_input.setSuffix(" s")
        self.macro_delay_input.setValue(1.0)
        delay_row.addWidget(self.macro_delay_input)

        macros_layout.addLayout(delay_row)

        create_macro_button = QPushButton("?  CREATE MACRO")
        create_macro_button.setMinimumHeight(42)
        create_macro_button.clicked.connect(self.create_macro)
        macros_layout.addWidget(create_macro_button)

        macros_list_heading = QLabel("YOUR AUTOMATIONS")
        macros_list_heading.setObjectName("Eyebrow")
        macros_layout.addWidget(macros_list_heading)

        self.macros_scroll = QScrollArea()
        self.macros_scroll.setWidgetResizable(True)
        self.macros_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.macros_scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.macros_scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.macros_container = QWidget()
        self.macros_container.setObjectName("MacrosContainer")
        self.macros_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.macros_list_layout = QVBoxLayout(self.macros_container)
        self.macros_list_layout.setSpacing(8)
        self.macros_list_layout.setContentsMargins(2, 2, 8, 2)

        self.macros_scroll.setWidget(self.macros_container)
        macros_layout.addWidget(self.macros_scroll, 1)

        self.page_stack.addWidget(home_page)
        self.page_stack.addWidget(system_page)
        self.page_stack.addWidget(applications_page)
        self.page_stack.addWidget(macros_page)
        self.page_stack.setCurrentIndex(0)

        self.refresh_macros()

        self._net_previous = psutil.net_io_counters()

        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(
            self.update_system_monitor
        )
        self.monitor_timer.start(1000)

        self.update_system_monitor()

        # РќРёР¶РЅСЏСЏ РєРѕРЅСЃРѕР»СЊ
        self.console_input = QLineEdit()
        self.console_input.setPlaceholderText(
            ">_  NEXUS CONSOLE вЂ” Enter command..."
        )
        self.console_input.returnPressed.connect(
            self.submit_console
        )
        home_layout.addWidget(self.console_input)

        parent.addWidget(workspace, 1)

        
    def create_monitor_card(self, title, value, description):
        card = GlassFrame()
        card.setObjectName("MonitorCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(7)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #b9a5d5;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
        """)

        value_label = QLabel(value)
        value_label.setStyleSheet("""
            color: #e5d5ff;
            font-size: 25px;
            font-weight: 700;
        """)

        description_label = QLabel(description)
        description_label.setStyleSheet("""
            color: #958da1;
            font-size: 10px;
        """)

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(description_label)

        if not hasattr(self, "monitor_labels"):
            self.monitor_labels = {}

        self.monitor_labels[title] = (
            value_label,
            description_label
        )

        return card


    def update_system_monitor(self):
        try:
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory()

            self.system_graph.add_sample(cpu, memory.percent)

            drive = os.path.splitdrive(
                os.path.abspath(__file__)
            )[0] + os.sep

            disk = psutil.disk_usage(drive)

            current_net = psutil.net_io_counters()
            elapsed = 1.0

            if hasattr(self, "_net_previous"):
                received = (
                    current_net.bytes_recv -
                    self._net_previous.bytes_recv
                ) / elapsed

                sent = (
                    current_net.bytes_sent -
                    self._net_previous.bytes_sent
                ) / elapsed
            else:
                received = 0
                sent = 0

            self._net_previous = current_net

            def format_rate(value):
                if value >= 1024 * 1024:
                    return f"{value / (1024 * 1024):.1f} MB/s"
                if value >= 1024:
                    return f"{value / 1024:.1f} KB/s"
                return f"{value:.0f} B/s"

            cpu_value, cpu_description = self.monitor_labels[
                "CPU / RAM UTILIZATION"
            ]

            cpu_value.setText(f"CPU  {cpu:.0f}%")
            cpu_description.setText(
                f"RAM  {memory.percent:.0f}%  В·  "
                f"{memory.used / (1024 ** 3):.1f} / "
                f"{memory.total / (1024 ** 3):.1f} GB"
            )

            disk_value, disk_description = self.monitor_labels[
                "DISK / NETWORK"
            ]

            disk_value.setText(f"DISK  {disk.percent:.0f}%")
            disk_description.setText(
                f"FREE  {disk.free / (1024 ** 3):.1f} GB"
                f"   В·   в†“ {format_rate(received)}"
                f"   в†‘ {format_rate(sent)}"
            )

            gpu_value, gpu_description = self.monitor_labels["NVIDIA GPU"]
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=2, check=True
                )
                values = [float(x.strip()) for x in result.stdout.strip().splitlines()[0].split(",")]
                load, temp, used, total = values
                gpu_value.setText(f"GPU  {load:.0f}%")
                gpu_description.setText(
                    f"TEMP  {temp:.0f} ?C  ?  VRAM  {used:.0f} / {total:.0f} MiB"
                )
            except Exception:
                gpu_value.setText("GPU  N/A")
                gpu_description.setText("NVIDIA telemetry unavailable")

        except Exception as error:
            print(f"[NEXUS MONITOR] {error}")

    def create_right_panel(self, parent):
        panel = GlassFrame()
        panel.setObjectName("RightPanel")
        panel.setFixedWidth(235)

        panel.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-left: 1px solid #292333;
            }
            QLabel {
                color: #d8c9e8;
            }
            QPushButton {
                background-color: rgba(28, 24, 37, 105);
                color: #cbb9df;
                border: 1px solid #332a40;
                border-radius: 8px;
                padding: 12px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(48, 36, 61, 150);
                border-color: #8d65b5;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 24, 16, 20)
        layout.setSpacing(12)

        title = QLabel("CONTROL PANEL")
        title.setStyleSheet("""
            color: #c6a3e8;
            font-size: 12px;
            font-weight: 700;
        """)

        subtitle = QLabel("NEXUS UTILITIES")
        subtitle.setStyleSheet("""
            color: #82758f;
            font-size: 9px;
        """)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        background_title = QLabel("ФОН ПРИЛОЖЕНИЯ")
        background_title.setStyleSheet(
            "color: #b9a5d5; font-size: 12px; font-weight: 700; padding-top: 12px;"
        )
        layout.addWidget(background_title)

        background_button = QPushButton("ВЫБРАТЬ ИЗОБРАЖЕНИЕ")
        background_button.clicked.connect(self.set_background_image)
        layout.addWidget(background_button)

        self.background_blur_label = QLabel("Размытие фона: 0")
        layout.addWidget(self.background_blur_label)

        self.background_blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.background_blur_slider.setRange(0, 30)
        self.background_blur_slider.setValue(
            int(self.saved_settings.get("background_blur", 0))
        )
        self.background_blur_slider.valueChanged.connect(self.set_background_blur)
        layout.addWidget(self.background_blur_slider)

        self.background_dim_label = QLabel("Затемнение фона: 0%")
        layout.addWidget(self.background_dim_label)

        self.background_dim_slider = QSlider(Qt.Orientation.Horizontal)
        self.background_dim_slider.setRange(0, 80)
        self.background_dim_slider.setValue(
            int(self.saved_settings.get("background_dim", 0))
        )
        self.background_dim_slider.valueChanged.connect(self.set_background_dim)
        layout.addWidget(self.background_dim_slider)
        layout.addSpacing(20)

        for name in [
            "Settings",
            "Notifications",
            "Power",
        ]:
            button = QPushButton(name)
            button.clicked.connect(
                lambda checked=False, item=name: self.show_message(item)
            )
            layout.addWidget(button)

        layout.addStretch()

        status = QLabel("NEXUS CORE  В·  ONLINE")
        status.setStyleSheet("""
            color: #9b83b5;
            font-size: 9px;
        """)
        layout.addWidget(status)

        parent.addWidget(panel)


    def change_orb_style(self, style):
        self.orb.set_style(style)

        for name, button in self.style_buttons.items():
            button.setChecked(name == style)

        self.status_label.setText(
            f"в—Џ  CORE STYLE: {style}"
        )

        self.save_settings()


    def eventFilter(self, obj, event):
        if event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel,
        ):
            if hasattr(self, "orb"):
                self.orb.reset_idle_timer()

        return super().eventFilter(obj, event)

   
    def open_customization(self):
        if hasattr(self, "customization_page"):
            self.page_title.setText("\u041d\u0410\u0421\u0422\u0420\u041e\u0419\u041a\u0418")
            self.page_stack.setCurrentWidget(self.customization_page)
            for button in self.nav_buttons:
                button.setChecked(False)
            return

        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.Shape.NoFrame)
        page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        page.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        content = QWidget()
        content.setObjectName("SettingsContent")
        content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        page.setWidget(content)

        self.customization_page = page

        layout = QVBoxLayout(content)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        title = QLabel("CORE CUSTOMIZATION")
        title.setStyleSheet("""
            font-size: 19px;
            font-weight: 700;
            letter-spacing: 2px;
        """)
        layout.addWidget(title)

        subtitle = QLabel(
            "РќР°СЃС‚СЂРѕР№ РІРЅРµС€РЅРёР№ РІРёРґ СЃРІРѕРµРіРѕ NEXUS CORE"
        )
        subtitle.setStyleSheet(
            "color: #958da1; font-size: 11px;"
        )
        layout.addWidget(subtitle)

        background_title = QLabel("ФОН ПРИЛОЖЕНИЯ")
        background_title.setStyleSheet(
            "color: #b9a5d5; font-size: 12px; font-weight: 700; padding-top: 12px;"
        )
        layout.addWidget(background_title)

        background_button = QPushButton("ВЫБРАТЬ ИЗОБРАЖЕНИЕ")
        background_button.clicked.connect(self.set_background_image)
        layout.addWidget(background_button)

        self.background_blur_label = QLabel("Размытие фона: 0")
        layout.addWidget(self.background_blur_label)

        self.background_blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.background_blur_slider.setRange(0, 30)
        self.background_blur_slider.setValue(
            int(self.saved_settings.get("background_blur", 0))
        )
        self.background_blur_slider.valueChanged.connect(self.set_background_blur)
        layout.addWidget(self.background_blur_slider)

        self.background_dim_label = QLabel("Затемнение фона: 0%")
        layout.addWidget(self.background_dim_label)

        self.background_dim_slider = QSlider(Qt.Orientation.Horizontal)
        self.background_dim_slider.setRange(0, 80)
        self.background_dim_slider.setValue(
            int(self.saved_settings.get("background_dim", 0))
        )
        self.background_dim_slider.valueChanged.connect(self.set_background_dim)
        layout.addWidget(self.background_dim_slider)

        # Р’Р«Р‘РћР  Р¦Р’Р•РўРћР’
        layout.addSpacing(10)

        style_title = QLabel("CORE VISUAL STYLE")
        style_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        style_title.setStyleSheet("""
            color: #b9a5d5;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2px;
            padding-top: 8px;
        """)
        layout.addWidget(style_title)

        style_row = QHBoxLayout()
        style_row.setSpacing(8)

        self.style_buttons = {}

        styles = [
            "ENERGY",
            "PARTICLES",
            "HOLOGRAM",
            "FLUID",
            "AURA",
            "VERITY",
        ]

        for style_name in styles:
            button = QPushButton(style_name)
            button.setCheckable(True)
            button.setChecked(style_name == self.orb.style)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(48, 44, 57, 105);
                    color: #aaa0b8;
                    border: 1px solid #494052;
                    border-radius: 8px;
                    padding: 9px 5px;
                    font-size: 9px;
                    font-weight: 600;
                    text-align: center;
                }

                QPushButton:hover {
                    background-color: rgba(73, 59, 89, 155);
                    border: 1px solid #a88aca;
                    color: #eee3ff;
                }

                QPushButton:checked {
                    background-color: rgba(73, 59, 89, 155);
                    border: 1px solid #b995e8;
                    color: #e8d6ff;
                }
            """)

            button.clicked.connect(
                lambda checked=False, s=style_name:
                    self.change_orb_style(s)
            )

            self.style_buttons[style_name] = button
            style_row.addWidget(button)

        layout.addLayout(style_row)

        colors_title = QLabel("COLOR PALETTE")
        colors_title.setStyleSheet(
            "color: #b9a5d5; font-weight: 700;"
        )
        layout.addWidget(colors_title)

        self.primary_color_button = QPushButton(
            "PRIMARY COLOR"
        )
        self.primary_color_button.clicked.connect(
            self.choose_primary_color
        )
        layout.addWidget(self.primary_color_button)

        self.secondary_color_button = QPushButton(
            "SECONDARY COLOR"
        )
        self.secondary_color_button.clicked.connect(
            self.choose_secondary_color
        )
        layout.addWidget(self.secondary_color_button)

        self.refresh_color_buttons()

        # Р СџР С›Р вЂєР вЂ”Р Р€Р СњР С™Р В
        layout.addSpacing(10)

        sliders_title = QLabel(
            "ANIMATION & APPEARANCE"
        )
        sliders_title.setStyleSheet(
            "color: #b9a5d5; font-weight: 700;"
        )
        layout.addWidget(sliders_title)

        def add_slider(
            name, minimum, maximum, value,
            callback, suffix="%"
        ):
            row = QVBoxLayout()

            header = QHBoxLayout()

            label = QLabel(name)
            value_label = QLabel(f"{value}{suffix}")
            value_label.setStyleSheet(
                "color: #b995e8;"
            )

            header.addWidget(label)
            header.addStretch()
            header.addWidget(value_label)

            slider = QSlider(
                Qt.Orientation.Horizontal
            )
            slider.setRange(minimum, maximum)
            slider.setValue(value)

            slider.valueChanged.connect(callback)
            slider.valueChanged.connect(
                lambda v, target=value_label, unit=suffix:
                    target.setText(f"{v}{unit}")
            )

            row.addLayout(header)
            row.addWidget(slider)
            layout.addLayout(row)

               # Р ВР СњР СћР вЂўР СњР РЋР ВР вЂ™Р СњР С›Р РЋР СћР В¬ Р РЋР вЂ™Р вЂўР В§Р вЂўР СњР ВРЇ
        add_slider(
            "GLOW INTENSITY",
            0, 200,
            int(self.orb.glow_intensity * 100),
            lambda v: (
                self.orb.set_glow(v / 100),
                self.save_settings()
            )
        )

        # Р РЋР С™Р С›Р В Р С›Р РЋР СћР В¬ Р С’Р СњР ВР СљР С’Р В¦Р ВР В
        add_slider(
            "ANIMATION SPEED",
            10, 300,
            int(self.orb.animation_speed * 100),
            lambda v: (
                self.orb.set_animation_speed(v / 100),
                self.save_settings()
            )
        )

        # Р РђР—РњР•Р  РЎР¤Р•Р Р«
        add_slider(
            "ORB SIZE",
            50, 150,
            int(self.orb.orb_scale * 100),
            lambda v: (
                self.orb.set_orb_scale(v / 100),
                self.save_settings()
            )
        )

        # Р С™Р С›Р вЂєР ВР В§Р вЂўР РЋР СћР вЂ™Р С› Р В§Р С’Р РЋР СћР ВР¦
        add_slider(
            "PARTICLE COUNT",
            10, 260,
            self.orb.particle_count,
            lambda v: (
                self.orb.set_particle_count(v),
                self.save_settings()
            ),
            suffix=""
        )

        layout.addStretch()

        close_button = QPushButton("\u2190 \u041d\u0410 \u0413\u041b\u0410\u0412\u041d\u0423\u042e")
        close_button.clicked.connect(lambda: self.change_page(0))
        layout.addWidget(close_button)

        self.page_stack.addWidget(page)
        self.page_title.setText("\u041d\u0410\u0421\u0422\u0420\u041e\u0419\u041a\u0418")
        self.page_stack.setCurrentWidget(page)

        for button in self.nav_buttons:
            button.setChecked(False)


    def refresh_color_buttons(self):
        if hasattr(self, "primary_color_button"):
            self.primary_color_button.setStyleSheet(
                f"background-color: {self.orb.primary_color.name()};"
                "color: #191820; font-weight: 700;"
            )

        if hasattr(self, "secondary_color_button"):
            self.secondary_color_button.setStyleSheet(
                f"background-color: {self.orb.secondary_color.name()};"
                "color: #191820; font-weight: 700;"
            )

    def choose_primary_color(self):
        color = QColorDialog.getColor(
            self.orb.primary_color,
            self,
            "Choose Primary Color"
        )

        if color.isValid():
            self.orb.set_colors(
                color,
                self.orb.secondary_color
            )
            self.refresh_color_buttons()
            self.save_settings()

    def choose_secondary_color(self):
        color = QColorDialog.getColor(
            self.orb.secondary_color,
            self,
            "Choose Secondary Color"
        )

        if color.isValid():
            self.orb.set_colors(
                self.orb.primary_color,
                color
            )
            self.refresh_color_buttons()
            self.save_settings()


    def preview_core_state(self, state):
        if state == "WAKE_UP":
            self.orb.wake_up()
        else:
            self.orb.set_state(state)

    def update_core_status(self, state):
        labels = {
            "SLEEP": "SLEEP  Р’В·  AWAITING COMMAND",
            "WAKE_UP": "WAKE UP  Р’В·  ACTIVATING",
            "LISTENING": "LISTENING  Р’В·  SPEAK NOW",
            "THINKING": "THINKING  Р’В·  PROCESSING",
            "EXECUTING": "EXECUTING  Р’В·  RUNNING ACTION",
        }

        self.core_status.setText(labels.get(state, state))

    def refresh_applications(self):
        cache_file = PROJECT_ROOT / "app_cache.json"

        # ?????? ??????? ???????????? ?????????? ??????? ? MACROS.
        self.app_catalog = {}

        try:
            if cache_file.exists():
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                apps = data.get("apps", {})

                if not isinstance(apps, dict):
                    raise ValueError("Invalid app cache format")

                self.app_catalog = {
                    str(name): str(app_path)
                    for name, app_path in apps.items()
                    if isinstance(name, str) and isinstance(app_path, str)
                }

            # ??? ?????????? ?????????? ?????? ?????? ???? ??????.
            start_menu_roots = []

            appdata = os.environ.get("APPDATA")
            programdata = os.environ.get("PROGRAMDATA")

            if appdata:
                start_menu_roots.append(
                    Path(appdata) / "Microsoft/Windows/Start Menu/Programs"
                )

            if programdata:
                start_menu_roots.append(
                    Path(programdata) / "Microsoft/Windows/Start Menu/Programs"
                )

            visible = {}

            for root in start_menu_roots:
                if not root.exists():
                    continue

                try:
                    shortcuts = list(root.rglob("*.lnk"))
                    shortcuts += list(root.rglob("*.url"))

                    for shortcut in shortcuts:
                        if not shortcut.is_file():
                            continue

                        name = shortcut.stem.strip()
                        if name:
                            visible.setdefault(name, str(shortcut))
                except (OSError, PermissionError) as scan_error:
                    print(f"[NEXUS APPLICATIONS] Cannot scan {root}: {scan_error}")

            self.application_entries = dict(sorted(
                visible.items(),
                key=lambda item: item[0].casefold()
            ))

            self.filter_applications(self.app_search.text())
            self.status_label.setText(
                f"APPLICATIONS: {len(self.application_entries)} SHORTCUTS | "
                f"CATALOG: {len(self.app_catalog)}"
            )

        except Exception as error:
            self.application_entries = {}
            self.filter_applications(self.app_search.text())
            self.status_label.setText("APPLICATION LIST LOAD FAILED")
            print(f"[NEXUS APPLICATIONS] {error}")

    def filter_applications(self, query=""):
        while self.apps_list_layout.count():
            item = self.apps_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        query = query.casefold().strip()
        matches = [
            (name, path)
            for name, path in self.application_entries.items()
            if query in name.casefold() or query in Path(path).stem.casefold()
        ]

        if not matches:
            empty = QLabel("NO MATCHING APPLICATIONS IN CATALOG")
            empty.setObjectName("Muted")
            self.apps_list_layout.addWidget(empty)
        else:
            for app_name, app_path in matches:
                row = QFrame()
                row.setObjectName("MonitorCard")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(14, 10, 14, 10)

                name = QLabel(app_name.replace("_", " ").title())
                name.setObjectName("PanelValue")
                name.setStyleSheet("font-size: 14px;")

                open_button = QPushButton("OPEN")
                open_button.setMinimumWidth(90)
                open_button.clicked.connect(
                    lambda checked=False, target=app_path:
                    self.launch_application(target)
                )

                row_layout.addWidget(name, 1)
                row_layout.addWidget(open_button)
                self.apps_list_layout.addWidget(row)

        self.apps_list_layout.addStretch()

    def launch_application(self, target):
        try:
            os.startfile(target)
            self.status_label.setText("APPLICATION LAUNCHED")
        except Exception as error:
            self.status_label.setText("LAUNCH FAILED")
            print(f"[NEXUS APPLICATIONS] {error}")

    def get_macros(self):
        path = Path("nexus_macros.json")
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def save_macros(self, macros):
        Path("nexus_macros.json").write_text(
            json.dumps(macros, ensure_ascii=False, indent=4),
            encoding="utf-8"
        )

    def refresh_macros(self):
        while self.macros_list_layout.count():
            item = self.macros_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        macros = self.get_macros()

        if not macros:
            empty = QLabel("???? ??? ?????????. ?????? ???? ?????? ?????? ????.")
            empty.setObjectName("Muted")
            self.macros_list_layout.addWidget(empty)

        for macro in macros:
            row = QFrame()
            row.setObjectName("MonitorCard")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)

            info = QVBoxLayout()
            name = QLabel(macro.get("name", "Unnamed macro"))
            name.setObjectName("PanelValue")

            details = QLabel(
                f"{len(macro.get('apps', []))} application(s)"
            )
            details.setObjectName("Muted")

            info.addWidget(name)
            info.addWidget(details)

            run_button = QPushButton("RUN")
            run_button.clicked.connect(
                lambda checked=False, item=macro: self.run_macro(item)
            )

            delete_button = QPushButton("DELETE")
            delete_button.clicked.connect(
                lambda checked=False, item=macro: self.delete_macro(item)
            )

            row_layout.addLayout(info, 1)
            row_layout.addWidget(run_button)
            row_layout.addWidget(delete_button)
            self.macros_list_layout.addWidget(row)

        self.macros_list_layout.addStretch()

    def toggle_macro_app_picker(self, checked):
        self.macro_apps_expanded = checked
        self.macro_app_picker.setVisible(checked)
        self.macro_apps_toggle.setText(
            "?  APPLICATIONS" if checked else "?  APPLICATIONS"
        )

    def refresh_macro_app_list(self):
        if not self.application_entries:
            self.refresh_applications()

        self.macro_app_list.clear()

        for app_name, app_path in sorted(
            self.application_entries.items(),
            key=lambda item: item[0].casefold()
        ):
            item = QListWidgetItem(app_name)
            item.setData(Qt.ItemDataRole.UserRole, app_path)
            item.setFlags(
                item.flags() | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(Qt.CheckState.Unchecked)
            self.macro_app_list.addItem(item)

        self.filter_macro_app_list(self.macro_app_search.text())

    def filter_macro_app_list(self, query):
        query = query.strip().casefold()

        for index in range(self.macro_app_list.count()):
            item = self.macro_app_list.item(index)
            item.setHidden(
                query not in item.text().casefold()
            )

    def sync_macro_selection(self, item):
        app_path = item.data(Qt.ItemDataRole.UserRole)
        if not app_path:
            return

        existing_row = -1
        for index in range(self.macro_selected_list.count()):
            selected = self.macro_selected_list.item(index)
            if selected.data(Qt.ItemDataRole.UserRole) == app_path:
                existing_row = index
                break

        if item.checkState() == Qt.CheckState.Checked:
            if existing_row < 0:
                selected = QListWidgetItem(item.text())
                selected.setData(Qt.ItemDataRole.UserRole, app_path)
                self.macro_selected_list.addItem(selected)
        elif existing_row >= 0:
            self.macro_selected_list.takeItem(existing_row)

    def move_macro_app(self, direction):
        row = self.macro_selected_list.currentRow()
        target = row + direction

        if row < 0 or target < 0:
            return
        if target >= self.macro_selected_list.count():
            return

        item = self.macro_selected_list.takeItem(row)
        self.macro_selected_list.insertItem(target, item)
        self.macro_selected_list.setCurrentRow(target)

    def create_macro(self):
        name = self.macro_name_input.text().strip()

        selected_apps = []
        for index in range(self.macro_selected_list.count()):
            item = self.macro_selected_list.item(index)
            app_path = item.data(Qt.ItemDataRole.UserRole)
            if app_path:
                selected_apps.append(str(app_path))

        if not name or not selected_apps:
            self.status_label.setText(
                "ENTER A NAME AND SELECT AT LEAST ONE APP"
            )
            return

        macro = {
            "name": name,
            "apps": selected_apps,
            "delay": float(self.macro_delay_input.value())
        }

        macros = self.get_macros()
        macros.append(macro)
        self.save_macros(macros)

        self.macro_name_input.clear()
        self.macro_selected_list.clear()
        self.macro_delay_input.setValue(1.0)

        for index in range(self.macro_app_list.count()):
            self.macro_app_list.item(index).setCheckState(
                Qt.CheckState.Unchecked
            )

        self.refresh_macros()
        self.status_label.setText("MACRO CREATED")

    def run_macro(self, macro):
        apps = list(macro.get("apps", []))
        if not apps:
            self.status_label.setText("MACRO HAS NO APPLICATIONS")
            return

        try:
            delay_seconds = max(0.0, float(macro.get("delay", 0)))
        except (TypeError, ValueError):
            delay_seconds = 0.0

        delay_ms = int(delay_seconds * 1000)
        self.status_label.setText(
            "MACRO STARTED: " + macro.get("name", "")
        )
        self._launch_macro_step(
            apps, 0, delay_ms, macro.get("name", "")
        )

    def _launch_macro_step(self, apps, index, delay_ms, macro_name):
        if index >= len(apps):
            self.status_label.setText(
                "MACRO COMPLETED: " + macro_name
            )
            return

        app_path = str(apps[index])

        try:
            if app_path.casefold() in ("notepad.exe", "calc.exe"):
                subprocess.Popen([app_path], shell=False)
            elif Path(app_path).exists():
                os.startfile(app_path)
            else:
                print(f"[NEXUS MACROS] Application not found: {app_path}")
        except Exception as error:
            print(f"[NEXUS MACROS] Launch failed: {app_path}: {error}")

        if index + 1 < len(apps):
            QTimer.singleShot(
                delay_ms,
                lambda: self._launch_macro_step(
                    apps, index + 1, delay_ms, macro_name
                )
            )
        else:
            self.status_label.setText(
                "MACRO COMPLETED: " + macro_name
            )

    def delete_macro(self, macro):
        macros = self.get_macros()
        macros = [
            item for item in macros
            if item != macro
        ]
        self.save_macros(macros)
        self.refresh_macros()
        self.status_label.setText("MACRO DELETED")

    def change_page(self, index):
        pages = [
            "Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ",
            "Applications",
            "Macros",
            "System",
            "Lighting",
            "Clipboard",
        ]

        self.page_title.setText(pages[index])
        self.page_stack.setCurrentIndex(
            3 if index == 2 else 2 if index == 1 else 1 if index == 3 else 0
        )

        if index == 1:
            self.refresh_applications()
        elif index == 2:
            self.refresh_macro_app_list()
            self.refresh_macros()

        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

        if index == 0:
            self.status_label.setText("NEXUS ONLINE")
        else:
            self.status_label.setText(
                "MODULE PREVIEW"
            )

    def show_message(self, name):
        self.status_label.setText(
            f"{{name.upper()}} вЂ” COMING SOON"
        )

    def submit_command(self):
        command = self.ask_input.text().strip()

        if not command:
            return

        self.status_label.setText(
            "BACKEND NOT CONNECTED"
        )
        self.ask_input.clear()

    def submit_console(self):
        command = self.console_input.text().strip()

        if not command:
            return

        self.status_label.setText(
            "CONSOLE BACKEND NOT CONNECTED"
        )
        self.console_input.clear()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)

    window = NexusWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

