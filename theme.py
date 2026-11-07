"""GoalWall's app palettes (goalwall/ui/static/app.css), light and dark, as a Qt palette + stylesheet."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

# name: (title, swatch dots, light, dark); each mode = (paper, surface, ink, muted, accent, on_accent)
PALETTES = {
    "route": ("Route card", ("#E7EDEB", "#2D5BD0", "#E9A62E"),
              ("#E7EDEB", "#FFFFFF", "#16232B", "#56646C", "#2D5BD0", "#FFFFFF"),
              ("#0F161A", "#162127", "#E6ECEE", "#9AA9AF", "#7D9CFF", "#0B1530")),
    "neon": ("Neon", ("#0A0A0A", "#007BA7", "#FF2D95"),
             ("#F2F3F5", "#FFFFFF", "#0A0A0A", "#5B5B64", "#007BA7", "#FFFFFF"),
             ("#0A0A0A", "#141417", "#F2F2F4", "#A0A0AA", "#007BA7", "#FFFFFF")),
    "aubergine": ("Aubergine", ("#DDE3E8", "#3A0F34", "#EAAA00"),
                  ("#DDE3E8", "#FFFFFF", "#3A0F34", "#6B5767", "#3A0F34", "#FFFFFF"),
                  ("#1C0719", "#2C0C27", "#EEF1F4", "#C6B3C2", "#EAAA00", "#2C0C27")),
    "mocha": ("Mocha", ("#6F4E37", "#E5E4E2", "#E6E0F0"),
              ("#E5E4E2", "#FCFBFA", "#2E2019", "#6A5C52", "#6F4E37", "#FFFFFF"),
              ("#17110E", "#241A15", "#E5E4E2", "#B5A99F", "#C9A487", "#241A15")),
    "catppuccin": ("Catppuccin", ("#1E1E2E", "#89B4FA", "#FAB387"),
                   ("#E6E9EF", "#EFF1F5", "#4C4F69", "#5C5F77", "#1E66F5", "#FFFFFF"),
                   ("#181825", "#1E1E2E", "#CDD6F4", "#A6ADC8", "#89B4FA", "#11111B")),
    "nord": ("Nord", ("#2E3440", "#88C0D0", "#EBCB8B"),
             ("#E5E9F0", "#F3F5F8", "#2E3440", "#4C566A", "#52749F", "#FFFFFF"),
             ("#2E3440", "#3B4252", "#ECEFF4", "#C5CCD8", "#88C0D0", "#2E3440")),
    "tokyo": ("Tokyo Night", ("#1A1B26", "#7AA2F7", "#BB9AF7"),
              ("#E1E2E7", "#F4F5F8", "#343B58", "#545C7E", "#2569D0", "#FFFFFF"),
              ("#16161E", "#1F2335", "#C0CAF5", "#A9B1D6", "#7AA2F7", "#16161E")),
    "dracula": ("Dracula", ("#282A36", "#BD93F9", "#FF79C6"),
                ("#F5F0DC", "#FFFBEB", "#1F1F1F", "#57536F", "#644AC9", "#FFFFFF"),
                ("#21222C", "#282A36", "#F8F8F2", "#C3C5D4", "#BD93F9", "#21222C")),
    "matcha": ("Matcha", ("#ECEEE3", "#58784A", "#C46B4A"),
               ("#ECEEE3", "#FBFAF4", "#26301F", "#56604E", "#58784A", "#FFFFFF"),
               ("#141812", "#1E241A", "#E8EADF", "#B3BAA8", "#A3C585", "#162012")),
    "swiss": ("Swiss", ("#FFFFFF", "#0A0A0A", "#E3120B"),
              ("#EFEFEC", "#FFFFFF", "#0A0A0A", "#4F4F4F", "#0A0A0A", "#FFFFFF"),
              ("#0A0A0A", "#161616", "#F5F5F3", "#B5B5B2", "#F5F5F3", "#0A0A0A")),
}
KEYS = ("paper", "surface", "ink", "muted", "accent", "on_accent")
current = {}  # tokens in use right now; the toggle switch paints with these


def tokens(name, dark):
    entry = PALETTES.get(name, PALETTES["route"])
    return dict(zip(KEYS, entry[3 if dark else 2]))


def rgba(hex_color, alpha):
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"


def stylesheet(t):
    ink, accent = t["ink"], t["accent"]
    return f"""
    QWidget {{ color: {ink}; font-size: 13px; }}
    QDialog, QMessageBox, #body {{ background: {t['paper']}; }}
    QScrollArea {{ background: transparent; border: none; }}
    QLabel {{ background: transparent; }}
    QLabel[muted="true"] {{ color: {t['muted']}; font-size: 12px; }}
    QLabel#title {{ font-family: "Lora"; font-size: 24px; font-weight: 600; }}
    QLabel#section {{ font-family: "Lora"; font-size: 17px; font-weight: 600; }}
    QFrame#card {{ background: {t['surface']}; border: 1px solid {rgba(ink, .08)}; border-radius: 20px; }}
    QPushButton {{ background: {rgba(ink, .065)}; border: none; border-radius: 14px; padding: 6px 14px; font-weight: 600; }}
    QPushButton:hover {{ background: {rgba(ink, .1)}; }}
    QPushButton:pressed {{ background: {rgba(ink, .15)}; }}
    QPushButton[primary="true"] {{ background: {accent}; color: {t['on_accent']}; padding: 7px 20px; border-radius: 15px; }}
    QPushButton[primary="true"]:hover {{ background: {QColor(accent).lighter(108).name()}; }}
    QPushButton[chip="true"] {{ border-radius: 10px; padding: 5px 11px; font-weight: 500; font-size: 12px; }}
    QPushButton[chip="true"]:checked {{ background: {accent}; color: {t['on_accent']}; }}
    QLineEdit {{ background: {t['surface']}; border: 1px solid {rgba(ink, .18)}; border-radius: 9px; padding: 5px 9px;
                 selection-background-color: {accent}; selection-color: {t['on_accent']}; }}
    QLineEdit:focus {{ border: 1px solid {accent}; }}
    QTableWidget {{ background: {t['surface']}; border: 1px solid {rgba(ink, .1)}; border-radius: 10px;
                    gridline-color: {rgba(ink, .08)}; selection-background-color: {rgba(accent, .22)}; selection-color: {ink}; }}
    QHeaderView::section {{ background: transparent; color: {t['muted']}; border: none;
                            border-bottom: 1px solid {rgba(ink, .1)}; padding: 5px 8px; font-weight: 600; }}
    QToolTip {{ background: {t['surface']}; color: {ink}; border: 1px solid {rgba(ink, .15)}; padding: 4px 6px; }}
    """


def apply(qapp, name, dark=None):
    """Recolour the whole app; follows the system's light/dark setting like GoalWall (tests can force `dark`)."""
    if dark is None:
        dark = qapp.styleHints().colorScheme() == Qt.ColorScheme.Dark
    t = tokens(name, dark)
    current.clear()
    current.update(t)
    pal = QPalette()  # Fusion draws scrollbars and focus rings from this
    for role, key in ((QPalette.Window, "paper"), (QPalette.Base, "surface"), (QPalette.Button, "surface"),
                      (QPalette.Text, "ink"), (QPalette.WindowText, "ink"), (QPalette.ButtonText, "ink"),
                      (QPalette.Highlight, "accent"), (QPalette.HighlightedText, "on_accent"),
                      (QPalette.PlaceholderText, "muted"), (QPalette.ToolTipBase, "surface"), (QPalette.ToolTipText, "ink")):
        pal.setColor(role, QColor(t[key]))
    qapp.setPalette(pal)
    qapp.setStyleSheet(stylesheet(t))
