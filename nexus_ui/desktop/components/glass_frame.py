from PySide6.QtCore import Qt, QPoint, QPointF, QRect
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient, QPainterPath, QPixmap
from PySide6.QtWidgets import QFrame
import math

class GlassFrame(QFrame):
    """Frosted glass with subtle background refraction."""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 16, 16)
        painter.setClipPath(path)

        window = self.window()
        root = window.centralWidget() if hasattr(window, "centralWidget") else None
        source = getattr(window, "background_source_pixmap", QPixmap())

        if root is not None and not source.isNull():
            root_size = root.size()
            scaled = source.scaled(
                root_size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )

            crop_x = max(0, (scaled.width() - root_size.width()) // 2)
            crop_y = max(0, (scaled.height() - root_size.height()) // 2)
            background = scaled.copy(
                crop_x, crop_y, root_size.width(), root_size.height()
            )

            pos = self.mapTo(root, QPoint(0, 0))
            margin = 18
            sample_rect = QRect(
                pos.x() - margin,
                pos.y() - margin,
                self.width() + margin * 2,
                self.height() + margin * 2
            ).intersected(background.rect())

            if not sample_rect.isEmpty():
                sample = background.copy(sample_rect)

                # Subtle frosted glass blur.
                small = sample.scaled(
                    max(1, sample.width() // 2),
                    max(1, sample.height() // 2),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                blurred = small.scaled(
                    sample.size(),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                local_x = max(0, pos.x() - sample_rect.x())
                local_y = max(0, pos.y() - sample_rect.y())

                # Slightly displace horizontal slices to simulate refraction.
                band_height = 5
                for y in range(0, self.height(), band_height):
                    h = min(band_height, self.height() - y)
                    dx = int(math.sin(y * 0.035) * 4)
                    dy = int(math.cos(y * 0.025) * 2)

                    sx = max(0, min(
                        blurred.width() - self.width(),
                        local_x + dx
                    ))
                    sy = max(0, min(
                        blurred.height() - h,
                        local_y + y + dy
                    ))

                    if sx + self.width() <= blurred.width() and sy + h <= blurred.height():
                        painter.drawPixmap(
                            QRect(0, y, self.width(), h),
                            blurred,
                            QRect(sx, sy, self.width(), h)
                        )

                dim = int(
                    getattr(window, "saved_settings", {}).get("background_dim", 0)
                )
                if dim > 0:
                    painter.fillPath(
                        path, QColor(0, 0, 0, int(dim * 255 / 100))
                    )
        else:
            painter.fillPath(path, QColor(28, 30, 38, 65))

        # Almost neutral glass tint instead of a purple overlay.
        painter.fillPath(path, QColor(205, 215, 235, 18))

        # Soft reflected light near the upper edge.
        glow = QRadialGradient(
            QPointF(0, 0), max(self.width(), self.height()) * 0.9
        )
        glow.setColorAt(0.0, QColor(255, 255, 255, 42))
        glow.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillPath(path, glow)

        painter.setClipping(False)

        painter.setPen(QPen(QColor(235, 240, 255, 105), 1))
        painter.drawPath(path)

        painter.setPen(QPen(QColor(255, 255, 255, 55), 1))
        painter.drawLine(18, 2, max(18, self.width() - 18), 2)

        painter.end()

