import json

import os

import sys

import math

import random

import subprocess

from pathlib import Path

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


class SystemGraph(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cpu_history = []
        self.ram_history = []
        self.setMinimumHeight(145)
        self.setMaximumHeight(175)

    def add_sample(self, cpu, ram):
        self.cpu_history.append(float(cpu))
        self.ram_history.append(float(ram))

        self.cpu_history = self.cpu_history[-60:]
        self.ram_history = self.ram_history[-60:]

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QPen(QColor("#393244"), 1))
        painter.setBrush(QColor(32, 29, 41, 55))
        painter.drawRoundedRect(
            0, 0, self.width() - 1, self.height() - 1, 10, 10
        )

        left = 43
        right = self.width() - 17
        top = 32
        bottom = self.height() - 24

        plot_width = max(1, right - left)
        plot_height = max(1, bottom - top)

        painter.setFont(self.font())

        # ????????? ? ???????
        painter.setPen(QColor("#b9a5d5"))
        painter.drawText(16, 20, "SYSTEM PERFORMANCE")

        painter.setPen(QPen(QColor("#b58aff"), 2.5))
        painter.drawLine(right - 205, 16, right - 185, 16)
        painter.setPen(QColor("#cbb8e0"))
        painter.drawText(right - 180, 20, "CPU")

        painter.setPen(QPen(QColor("#62c9e8"), 2.5))
        painter.drawLine(right - 105, 16, right - 85, 16)
        painter.setPen(QColor("#a9dceb"))
        painter.drawText(right - 80, 20, "RAM")

        # ?????
        painter.setFont(self.font())
        for level in range(0, 101, 25):
            y = bottom - int(plot_height * level / 100)

            painter.setPen(QPen(QColor("#393244"), 1))
            painter.drawLine(left, y, right, y)

            painter.setPen(QColor("#827990"))
            painter.drawText(9, y + 4, str(level))

        def draw_history(values, color):
            if not values:
                return

            path = QPainterPath()
            step = plot_width / max(59, len(values) - 1)

            for i, value in enumerate(values):
                x = left + i * step
                y = bottom - (max(0, min(100, value)) / 100) * plot_height

                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            painter.setPen(QPen(QColor(color), 2.5))
            painter.drawPath(path)

        draw_history(self.cpu_history, "#b58aff")
        draw_history(self.ram_history, "#62c9e8")

