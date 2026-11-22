from pathlib import Path

class NexusThemeLoader:
    def __init__(self, theme_file=None):
        self.theme_file = (
            Path(theme_file) if theme_file
            else Path(__file__).with_name("theme.qss")
        )

    def load(self):
        if not self.theme_file.is_file():
            raise FileNotFoundError(
                f"NEXUS theme not found: {self.theme_file}"
            )

        return self.theme_file.read_text(encoding="utf-8-sig")

    def apply(self, app):
        app.setStyleSheet(self.load())
