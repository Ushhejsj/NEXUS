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

from components.glass_frame import GlassFrame


class NexusOrb(QWidget):
    """РњРЅРѕРіРѕСЃС‚РёР»РµРІР°СЏ Р°РЅРёРјРёСЂРѕРІР°РЅРЅР°СЏ СЃРёСЃС‚РµРјР° NEXUS CORE."""

    stateChanged = Signal(str)

    def __init__(self):
        super().__init__()

        self.setMinimumHeight(215)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.phase = 0.0
        self.state = "SLEEP"
        self.style = "ENERGY"
        # VERITY Creepy Idle Animation
        self.idle_active = False
        self.idle_stage = 0
        self.idle_stage_time = 0

        self.eye_offset = 0.0
        self.creepy_smile = 0.0
        self.idle_elapsed = 0

        self.primary_color = QColor("#B995E8")
        self.secondary_color = QColor("#F1C2A9")

        # РџРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёРµ РїР°СЂР°РјРµС‚СЂС‹
        self.glow_intensity = 1.0
        self.animation_speed = 1.0
        self.particle_count = 180
        self.orb_scale = 1.0

        rng = random.Random(42)


        self.particles = [
            (
                rng.uniform(0, math.pi * 2),
                rng.uniform(0, math.pi),
                rng.uniform(1.0, 3.0),
                rng.uniform(0, math.pi * 2),
            )
            for _ in range(260)
        ]

        self.states = {


    


            "SLEEP": {
                "speed": 0.035,
                "pulse": 5,
                "glow": 42,
                "movement": 3,
            },
            "WAKE_UP": {
                "speed": 0.17,
                "pulse": 19,
                "glow": 115,
                "movement": 13,
            },
            "LISTENING": {
                "speed": 0.085,
                "pulse": 10,
                "glow": 75,
                "movement": 7,
            },
            "THINKING": {
                "speed": 0.23,
                "pulse": 13,
                "glow": 95,
                "movement": 12,
            },
            "EXECUTING": {
                "speed": 0.29,
                "pulse": 17,
                "glow": 120,
                "movement": 16,
            },
        }

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)

    # -----------------------------
    # Р Р€Р СџР В Р С’Р вЂ™Р вЂєР вЂўР СњР ВР вЂў Р РЋР С›Р РЋР СћР С›Р Р‡Р СњР ВР Р‡Р СљР В
    # -----------------------------


    def reset_idle_timer(self):
        self.idle_elapsed = 0

        if self.idle_active:
            self.stop_idle_animation()


    def set_state(self, state):
        state = state.upper().replace(" ", "_")

        if state not in self.states:
            return

        self.state = state
        self.stateChanged.emit(state)
        self.update()

    def wake_up(self):
        self.set_state("WAKE_UP")
        QTimer.singleShot(1100, self.finish_wake_up)

    def finish_wake_up(self):
        if self.state == "WAKE_UP":
            self.set_state("LISTENING")

    # -----------------------------
    # Р Р€Р СџР В Р С’Р вЂ™Р вЂєР вЂўР СњР ВР вЂў Р РЋР СћР ВР вЂєР Р‡Р СљР В
    # -----------------------------


    def set_style(self, style):
        style = style.upper()

        available_styles = [
            "ENERGY",
            "PARTICLES",
            "HOLOGRAM",
            "FLUID",
            "AURA",
            "VERITY",
        ]

        if style not in available_styles:
            return

        self.style = style
        self.update()

    def set_colors(self, primary, secondary):
        self.primary_color = QColor(primary)
        self.secondary_color = QColor(secondary)
        self.update()

    def set_glow(self, value):
        self.glow_intensity = max(0.0, min(2.0, value))
        self.update()

    def set_animation_speed(self, value):
        self.animation_speed = max(0.1, min(3.0, value))

    def set_particle_count(self, value):
        self.particle_count = max(10, min(260, int(value)))
        self.update()

    def set_orb_scale(self, value):
        self.orb_scale = max(0.5, min(1.5, value))
        self.update()

    # -----------------------------
    # Р С’Р СњР ВР СљР С’Р В¦Р ВРЇ
    # -----------------------------

    def animate(self):
        settings = self.states[self.state]

        style_speed = {
            "ENERGY": 1.0,
            "PARTICLES": 0.8,
            "HOLOGRAM": 0.65,
            "FLUID": 0.55,
            "AURA": 0.4,
            "VERITY": 0.5,
        }

        self.phase += (
            settings["speed"]
            * self.animation_speed
            * style_speed[self.style]
        )
        # РђРІС‚РѕРјР°С‚РёС‡РµСЃРєРёР№ Р·Р°РїСѓСЃРє VERITY Idle С‡РµСЂРµР· 15 СЃРµРєСѓРЅРґ
        if self.style == "VERITY" and self.state == "SLEEP":
            if not self.idle_active:
                self.idle_elapsed += 30

                if self.idle_elapsed >= 15000:
                    self.start_idle_animation()
        else:
            self.idle_elapsed = 0

            if self.idle_active:
                self.stop_idle_animation()

        self.update_idle_animation()
        self.update()

    # -----------------------------
    # Р вЂ™Р РЋР СџР С›Р СљР С›Р вЂњР С’Р СћР вЂўР вЂєР В¬Р СњР В«Р вЂў Р В¤Р Р€Р СњР С™Р В¦Р ВР В
    # -----------------------------

    def start_idle_animation(self):
        if self.style != "VERITY" or self.state != "SLEEP":
            return

        self.idle_active = True
        self.idle_stage = 0
        self.idle_stage_time = 0
        self.eye_offset = 0.0
        self.creepy_smile = 0.0
        self.update()

    def stop_idle_animation(self):
        self.idle_active = False
        self.idle_elapsed = 0
        self.idle_stage = 0
        self.idle_stage_time = 0
        self.eye_offset = 0.0
        self.creepy_smile = 0.0
        self.update()

    def update_idle_animation(self):
        if not self.idle_active:
            return

        self.idle_stage_time += 30
        t = self.idle_stage_time

        if self.idle_stage == 0:
            self.eye_offset = min(1.0, t / 900) * 0.15
            if t >= 900:
                self.idle_stage = 1
                self.idle_stage_time = 0

        elif self.idle_stage == 1:
            if t >= 500:
                self.idle_stage = 2
                self.idle_stage_time = 0

        elif self.idle_stage == 2:
            progress = min(1.0, t / 1100)
            self.eye_offset = 0.15 - progress * 0.30
            if t >= 1100:
                self.idle_stage = 3
                self.idle_stage_time = 0

        elif self.idle_stage == 3:
            if t >= 500:
                self.idle_stage = 4
                self.idle_stage_time = 0

        elif self.idle_stage == 4:
            self.creepy_smile = min(1.0, t / 500)
            if t >= 500:
                self.idle_stage = 5
                self.idle_stage_time = 0

        elif self.idle_stage == 5:
            self.creepy_smile = 1.0
            if t >= 2500:
                self.idle_stage = 6
                self.idle_stage_time = 0

        elif self.idle_stage == 6:
            progress = min(1.0, t / 700)
            self.creepy_smile = 1.0 - progress
            self.eye_offset *= 0.94

            if t >= 700:
                self.stop_idle_animation()

        self.update()


    def color_alpha(self, color, alpha):
        result = QColor(color)
        result.setAlpha(max(0, min(255, int(alpha))))
        return result

    def draw_glow(self, painter, cx, cy, radius, intensity):
        glow = QRadialGradient(cx, cy, radius)

        glow.setColorAt(
            0.0,
            self.color_alpha(
                self.secondary_color,
                65 * intensity,
            ),
        )

        glow.setColorAt(
            0.35,
            self.color_alpha(
                self.primary_color,
                45 * intensity,
            ),
        )

        glow.setColorAt(
            1.0,
            QColor(20, 18, 30, 0),
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)

        painter.drawEllipse(
            int(cx - radius),
            int(cy - radius),
            int(radius * 2),
            int(radius * 2),
        )

    # -----------------------------
    # ENERGY
    # -----------------------------

    def draw_energy(self, painter, cx, cy, radius, movement):
        pulse = math.sin(self.phase * 1.5) * movement

        # Р’РЅРµС€РЅРµРµ СЌРЅРµСЂРіРµС‚РёС‡РµСЃРєРѕРµ РїРѕР»Рµ
        self.draw_glow(
            painter,
            cx,
            cy,
            radius * 2.1,
            self.glow_intensity,
        )

        # Р­РЅРµСЂРіРµС‚РёС‡РµСЃРєРёРµ РѕР±РѕР»РѕС‡РєРё
        for i in range(4):
            r = radius * (1.0 + i * 0.13) + pulse

            color = self.color_alpha(
                self.primary_color,
                65 - i * 13,
            )

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(color, 1.4))

            painter.drawEllipse(
                int(cx - r),
                int(cy - r),
                int(r * 2),
                int(r * 2),
            )

        # РћСЃРЅРѕРІРЅР°СЏ СЌРЅРµСЂРіРµС‚РёС‡РµСЃРєР°СЏ СЃС„РµСЂР°
        gradient = QRadialGradient(
            cx - radius * 0.3,
            cy - radius * 0.35,
            radius * 1.7,
        )

        gradient.setColorAt(0.0, self.secondary_color)
        gradient.setColorAt(0.3, self.primary_color)
        gradient.setColorAt(0.72, QColor("#765B9E"))
        gradient.setColorAt(1.0, QColor("#30213F"))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)

        painter.drawEllipse(
            int(cx - radius),
            int(cy - radius),
            int(radius * 2),
            int(radius * 2),
        )

        # Р­РЅРµСЂРіРµС‚РёС‡РµСЃРєРёРµ СЂР°Р·СЂСЏРґС‹
        for i in range(14):
            angle = (
                self.phase * 0.7
                + i * math.pi * 2 / 14
            )

            inner_r = radius * 0.8
            outer_r = radius + 18 + math.sin(
                self.phase * 2 + i
            ) * 12

            x1 = cx + math.cos(angle) * inner_r
            y1 = cy + math.sin(angle) * inner_r

            x2 = cx + math.cos(angle + 0.08) * outer_r
            y2 = cy + math.sin(angle + 0.08) * outer_r

            color = self.color_alpha(
                self.secondary_color,
                110,
            )

            painter.setPen(QPen(color, 1.5))

            painter.drawLine(
                int(x1),
                int(y1),
                int(x2),
                int(y2),
            )

    # -----------------------------
    # PARTICLES
    # -----------------------------

    def draw_particles(self, painter, cx, cy, radius):
        self.draw_glow(
            painter,
            cx,
            cy,
            radius * 1.7,
            self.glow_intensity * 0.7,
        )

        # РўРѕРЅРєРёР№ РІРЅРµС€РЅРёР№ РєРѕРЅС‚СѓСЂ
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(
            QPen(
                self.color_alpha(self.primary_color, 35),
                1,
            )
        )

        painter.drawEllipse(
            int(cx - radius),
            int(cy - radius),
            int(radius * 2),
            int(radius * 2),
        )

        # РЎС„РµСЂР° РёР· РѕС‚РґРµР»СЊРЅС‹С… С‚РѕС‡РµРє
        for index, particle in enumerate(
            self.particles[:self.particle_count]
        ):
            theta, phi, size, offset = particle

            angle = theta + self.phase * 0.16

            depth = math.cos(phi)

            x = (
                cx
                + math.sin(phi)
                * math.cos(angle)
                * radius
            )

            y = (
                cy
                + math.sin(phi)
                * math.sin(angle)
                * radius
                * 0.78
            )

            # Р§Р°СЃС‚РёС†С‹ РЅР° РїРµСЂРµРґРЅРµРј РїР»Р°РЅРµ СЏСЂС‡Рµ
            alpha = 75 + int((depth + 1) * 80)

            alpha += int(
                35 * math.sin(self.phase + offset)
            )

            color = self.color_alpha(
                self.primary_color,
                alpha,
            )

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)

            particle_size = size * (
                0.7 + (depth + 1) * 0.35
            )

            painter.drawEllipse(
                int(x),
                int(y),
                int(particle_size),
                int(particle_size),
            )

    # -----------------------------
    # HOLOGRAM
    # -----------------------------

    def draw_hologram(self, painter, cx, cy, radius):
        self.draw_glow(
            painter,
            cx,
            cy,
            radius * 1.8,
            self.glow_intensity,
        )

        color = self.color_alpha(
            self.primary_color,
            125,
        )

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, 1.3))

        # Р’РЅРµС€РЅСЏСЏ РіРѕР»РѕРіСЂР°С„РёС‡РµСЃРєР°СЏ РѕР±РѕР»РѕС‡РєР°
        painter.drawEllipse(
            int(cx - radius),
            int(cy - radius),
            int(radius * 2),
            int(radius * 2),
        )

        # Р’СЂР°С‰Р°СЋС‰РёРµСЃСЏ РІРµСЂС‚РёРєР°Р»СЊРЅС‹Рµ СЌР»Р»РёРїСЃС‹
        for i in range(5):
            factor = abs(
                math.sin(self.phase * 0.6 + i * 0.6)
            )

            width = max(4, radius * factor)

            painter.setPen(
                QPen(
                    self.color_alpha(
                        self.secondary_color,
                        110,
                    ),
                    1,
                )
            )

            painter.drawEllipse(
                int(cx - width),
                int(cy - radius),
                int(width * 2),
                int(radius * 2),
            )

        # Р“РѕСЂРёР·РѕРЅС‚Р°Р»СЊРЅС‹Рµ Р»РёРЅРёРё
        for i in range(-3, 4):
            y = cy + i * radius * 0.24

            width = radius * math.sqrt(
                max(0.1, 1 - (i * 0.24) ** 2)
            )

            painter.setPen(
                QPen(
                    self.color_alpha(
                        self.primary_color,
                        65,
                    ),
                    1,
                )
            )

            painter.drawLine(
                int(cx - width),
                int(y),
                int(cx + width),
                int(y),
            )

        # РЎРєР°РЅРёСЂСѓСЋС‰РёР№ Р»СѓС‡
        scan_y = cy + math.sin(self.phase * 1.5) * radius

        painter.setPen(
            QPen(
                self.color_alpha(
                    self.secondary_color,
                    180,
                ),
                2,
            )
        )

        painter.drawLine(
            int(cx - radius),
            int(scan_y),
            int(cx + radius),
            int(scan_y),
        )

    # -----------------------------
    # FLUID
    # -----------------------------

    def draw_fluid(self, painter, cx, cy, radius):
        self.draw_glow(
            painter,
            cx,
            cy,
            radius * 1.9,
            self.glow_intensity,
        )

        # РќРµСЃРєРѕР»СЊРєРѕ РїРµСЂРµР»РёРІР°СЋС‰РёС…СЃСЏ СЃР»РѕС‘РІ
        for i in range(5):
            angle = (
                self.phase * 0.45
                + i * math.pi * 2 / 5
            )

            offset = radius * 0.22

            x = cx + math.cos(angle) * offset
            y = cy + math.sin(angle) * offset

            blob_radius = radius * (
                0.58 + 0.08 * math.sin(
                    self.phase + i
                )
            )

            gradient = QRadialGradient(
                x - blob_radius * 0.25,
                y - blob_radius * 0.3,
                blob_radius * 1.5,
            )

            gradient.setColorAt(
                0.0,
                self.color_alpha(
                    self.secondary_color,
                    180,
                ),
            )

            gradient.setColorAt(
                0.5,
                self.color_alpha(
                    self.primary_color,
                    145,
                ),
            )

            gradient.setColorAt(
                1.0,
                self.color_alpha(
                    QColor("#765B9E"),
                    0,
                ),
            )

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)

            painter.drawEllipse(
                int(x - blob_radius),
                int(y - blob_radius),
                int(blob_radius * 2),
                int(blob_radius * 2),
            )

        # Р’РЅРµС€РЅСЏСЏ СЃС‚РµРєР»СЏРЅРЅР°СЏ РіСЂР°РЅРёС†Р°
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.setPen(
            QPen(
                self.color_alpha(
                    self.secondary_color,
                    90,
                ),
                1.3,
            )
        )

        painter.drawEllipse(
            int(cx - radius),
            int(cy - radius),
            int(radius * 2),
            int(radius * 2),
        )

    # -----------------------------
    # AURA
    # -----------------------------

    def draw_aura(self, painter, cx, cy, radius):
        pulse = math.sin(self.phase) * 8

        # РњСЏРіРєРѕРµ Р°С‚РјРѕСЃС„РµСЂРЅРѕРµ СЃРІРµС‡РµРЅРёРµ
        self.draw_glow(
            painter,
            cx,
            cy,
            radius * 2.3,
            self.glow_intensity * 1.2,
        )

        # РџРѕР»СѓРїСЂРѕР·СЂР°С‡РЅР°СЏ СЃС„РµСЂР°
        gradient = QRadialGradient(
            cx - radius * 0.25,
            cy - radius * 0.3,
            radius * 1.6,
        )

        gradient.setColorAt(
            0.0,
            self.color_alpha(
                self.secondary_color,
                155,
            ),
        )

        gradient.setColorAt(
            0.4,
            self.color_alpha(
                self.primary_color,
                115,
            ),
        )

        gradient.setColorAt(
            1.0,
            self.color_alpha(
                QColor("#765B9E"),
                5,
            ),
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)

        painter.drawEllipse(
            int(cx - radius + pulse),
            int(cy - radius + pulse),
            int((radius - pulse) * 2),
            int((radius - pulse) * 2),
        )

        # РЎРїРѕРєРѕР№РЅС‹Рµ РѕСЂР±РёС‚С‹
        for i in range(3):
            r = radius * (1.2 + i * 0.18)

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(
                QPen(
                    self.color_alpha(
                        self.primary_color,
                        45 - i * 10,
                    ),
                    1,
                )
            )

            painter.drawEllipse(
                int(cx - r),
                int(cy - r * 0.75),
                int(r * 2),
                int(r * 1.5),
            )

    # -----------------------------
    # Р вЂњР вЂєР С’Р вЂ™Р СњР С’Р Р‡ Р С›Р СћР В Р ВРЎРћР’РљРђ
    # -----------------------------
    
   
    def draw_verity(self, painter, cx, cy, radius):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        eye_offset = getattr(self, "eye_offset", 0.0)
        creepy = getattr(self, "creepy_smile", 0.0)

        # РўРµРЅСЊ
        shadow = QRadialGradient(
            cx, cy + radius * 0.82, radius * 0.65
        )
        shadow.setColorAt(0.0, QColor(55, 42, 10, 75))
        shadow.setColorAt(1.0, QColor(55, 42, 10, 0))

        painter.setBrush(shadow)
        painter.drawEllipse(
            cx - radius * 0.85,
            cy + radius * 0.65,
            radius * 1.7,
            radius * 0.38
        )

        # Р–С‘Р»С‚РѕРµ С‚РµР»Рѕ
        body = QRadialGradient(
            cx - radius * 0.28,
            cy - radius * 0.36,
            radius * 1.55
        )
        body.setColorAt(0.0, QColor("#FFF36A"))
        body.setColorAt(0.35, QColor("#FFE51D"))
        body.setColorAt(0.72, QColor("#F5C900"))
        body.setColorAt(1.0, QColor("#A77A0B"))

        painter.setBrush(body)
        painter.drawEllipse(
            cx - radius,
            cy - radius,
            radius * 2,
            radius * 2
        )

        # Р‘Р»РёРє
        shine = QRadialGradient(
            cx - radius * 0.32,
            cy - radius * 0.48,
            radius * 0.85
        )
        shine.setColorAt(0.0, QColor(255, 255, 190, 100))
        shine.setColorAt(0.45, QColor(255, 255, 190, 28))
        shine.setColorAt(1.0, QColor(255, 255, 190, 0))

        painter.setBrush(shine)
        painter.drawEllipse(
            cx - radius,
            cy - radius,
            radius * 2,
            radius * 2
        )

        # Р“Р»Р°Р·Р° СЃ РґРІРёР¶РµРЅРёРµРј РІР·РіР»СЏРґР°
        eye_w = radius * 0.105
        eye_h = radius * 0.22
        eye_y = cy - radius * 0.19
        shift = eye_offset * radius

        painter.setBrush(QColor("#100D05"))

        painter.drawEllipse(
            cx - radius * 0.34 - eye_w / 2 + shift,
            eye_y - eye_h / 2,
            eye_w,
            eye_h
        )

        painter.drawEllipse(
            cx + radius * 0.34 - eye_w / 2 + shift,
            eye_y - eye_h / 2,
            eye_w,
            eye_h
        )

        # РћР±С‹С‡РЅР°СЏ СѓР»С‹Р±РєР° вЂ” С‚РѕР»СЊРєРѕ РєРѕРіРґР° creepy-Р°РЅРёРјР°С†РёСЏ РЅРµ Р°РєС‚РёРІРЅР°
        if creepy <= 0.01:
            smile = QPainterPath()
            smile.moveTo(
                cx - radius * 0.45,
                cy + radius * 0.20
            )
            smile.quadTo(
                cx,
                cy + radius * 0.52,
                cx + radius * 0.45,
                cy + radius * 0.20
            )

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(
                QPen(
                    QColor("#171008"),
                    radius * 0.035,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin
                )
            )
            painter.drawPath(smile)

        # РџСѓРіР°СЋС‰Р°СЏ С€РёСЂРѕРєР°СЏ СѓР»С‹Р±РєР° вЂ” С‚РѕР»СЊРєРѕ РґРІР° СЂСЏРґР° Р·СѓР±РѕРІ
        if creepy > 0.01:
            painter.save()
            painter.setOpacity(creepy)
            painter.setPen(Qt.PenStyle.NoPen)

            # Р’РµСЂС…РЅРёР№ СЂСЏРґ Р·СѓР±РѕРІ
            upper = QPainterPath()
            upper.moveTo(
                cx - radius * 0.55,
                cy + radius * 0.12
            )
            upper.quadTo(
                cx, cy + radius * 0.40,
                cx + radius * 0.55,
                cy + radius * 0.12
            )
            upper.lineTo(
                cx + radius * 0.48,
                cy + radius * 0.30
            )
            upper.quadTo(
                cx, cy + radius * 0.48,
                cx - radius * 0.48,
                cy + radius * 0.30
            )
            upper.closeSubpath()

            painter.setBrush(QColor("#FFF9E8"))
            painter.drawPath(upper)


        # РќРёР¶РЅРёР№ СЂСЏРґ Р·СѓР±РѕРІ вЂ” РІРїР»РѕС‚РЅСѓСЋ Рє РІРµСЂС…РЅРµРјСѓ
            lower = QPainterPath()
            lower.moveTo(
                cx - radius * 0.48,
                cy + radius * 0.29
            )
            lower.quadTo(
                cx, cy + radius * 0.43,
                cx + radius * 0.48,
                cy + radius * 0.29
            )
            lower.lineTo(
                cx + radius * 0.43,
                cy + radius * 0.48
            )
            lower.quadTo(
                cx, cy + radius * 0.62,
                cx - radius * 0.43,
                cy + radius * 0.48
            )
            lower.closeSubpath()

            painter.drawPath(lower)

            # Р Р°Р·РґРµР»РёС‚РµР»Рё Р·СѓР±РѕРІ
            painter.setPen(
                QPen(
                    QColor("#A58B55"),
                    max(1.0, radius * 0.012)
                )
            )

            for x in [-0.34, -0.17, 0.0, 0.17, 0.34]:
                painter.drawLine(
                    int(cx + radius * x),
                    int(cy + radius * 0.25),
                    int(cx + radius * x),
                    int(cy + radius * 0.31)
                )

                painter.drawLine(
                    int(cx + radius * x),
                    int(cy + radius * 0.36),
                    int(cx + radius * x),
                    int(cy + radius * 0.43)
                )

            painter.restore()

        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        width = self.width()
        height = self.height()

        cx = width / 2
        cy = height / 2

        settings = self.states[self.state]

        radius = min(width, height) * 0.25
        radius *= self.orb_scale

        radius += math.sin(self.phase) * (
            settings["pulse"] * 0.35
        )

        movement = settings["movement"]

        if self.style == "ENERGY":
            self.draw_energy(
                painter, cx, cy, radius, movement
            )

        elif self.style == "PARTICLES":
            self.draw_particles(
                painter, cx, cy, radius
            )

        elif self.style == "HOLOGRAM":
            self.draw_hologram(
                painter, cx, cy, radius
            )

        elif self.style == "FLUID":
            self.draw_fluid(
                painter, cx, cy, radius
            )

        elif self.style == "AURA":
            self.draw_aura(
                painter, cx, cy, radius
            )

        elif self.style == "VERITY":
            self.draw_verity(
                painter, cx, cy, radius
            )

