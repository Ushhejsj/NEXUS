from PySide6.QtGui import QColor, QFont

class NexusDesign:
    APP_NAME = "NEXUS"

    COLORS = {
        "background": "#09090F",
        "surface": "#11111B",
        "surface_elevated": "#191925",
        "surface_hover": "#222231",
        "border": "#302B40",
        "border_subtle": "#242333",
        "text": "#F4F0FA",
        "text_secondary": "#A49AAF",
        "text_muted": "#716A80",
        "accent": "#B995E8",
        "accent_hover": "#C9A9F2",
        "accent_soft": "#382A4B",
        "secondary": "#F1C2A9",
        "success": "#79D6AE",
        "warning": "#E8BD78",
        "danger": "#E88491",
    }

    TYPOGRAPHY = {
        "family": "Segoe UI",
        "display": 28,
        "heading": 20,
        "subheading": 15,
        "body": 13,
        "caption": 11,
    }

    SPACING = {
        "xs": 4,
        "sm": 8,
        "md": 12,
        "lg": 16,
        "xl": 24,
        "xxl": 32,
    }

    RADIUS = {
        "sm": 8,
        "md": 12,
        "lg": 18,
        "xl": 24,
        "pill": 999,
    }

    EFFECTS = {
        "glass_blur": 22,
        "glass_opacity": 0.72,
        "shadow_blur": 28,
        "shadow_opacity": 0.28,
    }

    @classmethod
    def color(cls, name):
        return QColor(cls.COLORS[name])

    @classmethod
    def font(cls, size="body", weight=400):
        font = QFont(cls.TYPOGRAPHY["family"])
        font.setPixelSize(cls.TYPOGRAPHY[size])
        font.setWeight(weight)
        return font
