import json
import os
import sys
import math
import random
import subprocess
from pathlib import Path
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
from components.glass_frame import GlassFrame
from components.nexus_orb import NexusOrb
from components.system_graph import SystemGraph


class SidebarMixin:
    def create_sidebar(self, parent):
        sidebar = GlassFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(190)

        self.sidebar = sidebar
        self.sidebar_collapsed = False
        self.sidebar_text_widgets = []
        self.nav_buttons = []
        self.nav_symbols = []
        self.nav_icon_labels = []
        self.nav_name_labels = []

        layout = QVBoxLayout(sidebar)
        self.sidebar_layout = layout
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(5)

        self.sidebar_toggle = QPushButton("\u2039   \u0421\u0412\u0415\u0420\u041d\u0423\u0422\u042c")
        self.sidebar_toggle.setFixedHeight(30)
        self.sidebar_toggle.setStyleSheet("padding: 0px 6px; text-align: left; font-size: 11px; background: transparent; border: none;")
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.sidebar_toggle)

        menu_label = QLabel("\u0420\u0410\u0411\u041e\u0427\u0415\u0415 \u041f\u0420\u041e\u0421\u0422\u0420\u0410\u041d\u0421\u0422\u0412\u041e")
        menu_label.setObjectName("PanelTitle")
        layout.addWidget(menu_label)
        self.sidebar_text_widgets.append(menu_label)

        pages = [
            ("⌂", "ГЛАВНАЯ"),
            ("▦", "ПРИЛОЖЕНИЯ"),
            ("≡", "МАКРОСЫ"),
            ("▤", "СИСТЕМА"),
            ("◉", "ОСВЕЩЕНИЕ"),
            ("▣", "БУФЕР ОБМЕНА"),
        ]

        for index, (symbol, name) in enumerate(pages):
            button = QPushButton()
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setFixedHeight(36)
            button.setToolTip(name)
            button.setStyleSheet("text-align: left; padding: 0px;")

            row = QHBoxLayout(button)
            row.setContentsMargins(7, 0, 6, 0)
            row.setSpacing(7)

            icon_label = QLabel(symbol)
            icon_label.setFixedWidth(25)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("background: transparent; border: none;")

            name_label = QLabel(name)
            name_label.setStyleSheet("font-size: 11px; background: transparent;")

            row.addWidget(icon_label)
            row.addWidget(name_label)
            row.addStretch()

            button.clicked.connect(
                lambda checked=False, i=index: self.change_page(i)
            )

            self.nav_buttons.append(button)
            self.nav_symbols.append((symbol, name))
            self.nav_icon_labels.append(icon_label)
            self.nav_name_labels.append(name_label)
            layout.addWidget(button)

        premium_button = QPushButton()
        premium_button.setFixedHeight(36)
        premium_button.setToolTip("\u041f\u043e\u0434\u043f\u0438\u0441\u043a\u0430 \u0432 \u0431\u0443\u0434\u0443\u0449\u0435\u043c")
        premium_row = QHBoxLayout(premium_button)
        premium_row.setContentsMargins(7, 0, 6, 0)
        premium_row.setSpacing(7)

        premium_icon = QLabel("\u2605")
        premium_icon.setFixedWidth(25)
        premium_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        premium_icon.setStyleSheet("background: transparent; border: none;")

        self.sidebar_premium_label = QLabel("\u041f\u041e\u0414\u041f\u0418\u0421\u041a\u0410")
        self.sidebar_premium_label.setStyleSheet("font-size: 11px; background: transparent;")

        premium_row.addWidget(premium_icon)
        premium_row.addWidget(self.sidebar_premium_label)
        premium_row.addStretch()
        premium_button.clicked.connect(
            lambda checked=False: self.show_message("\u041f\u041e\u0414\u041f\u0418\u0421\u041a\u0410")
        )
        layout.addWidget(premium_button)

        self.sidebar_premium_button = premium_button
        layout.addStretch()

        settings_button = QPushButton()
        settings_button.setFixedHeight(36)
        settings_row = QHBoxLayout(settings_button)
        settings_row.setContentsMargins(7, 0, 6, 0)
        settings_row.setSpacing(7)

        self.sidebar_settings_icon = QLabel("\u2699")
        self.sidebar_settings_icon.setFixedWidth(25)
        self.sidebar_settings_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_settings_icon.setStyleSheet("background: transparent; border: none;")

        self.sidebar_settings_label = QLabel("\u041d\u0410\u0421\u0422\u0420\u041e\u0419\u041a\u0418")
        self.sidebar_settings_label.setStyleSheet("font-size: 11px; background: transparent;")

        settings_row.addWidget(self.sidebar_settings_icon)
        settings_row.addWidget(self.sidebar_settings_label)
        settings_row.addStretch()

        settings_button.clicked.connect(self.open_customization)
        self.sidebar_settings_button = settings_button
        layout.addWidget(settings_button)

        parent.addWidget(sidebar)
