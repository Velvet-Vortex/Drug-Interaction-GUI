'''
Code was adapted from the article "Drag & Drop Widgets with PySide6"
by Martin Fitzpatrick found at https://www.pythonguis.com/faq/pyside6-drag-drop-widgets/
'''

from PySide6.QtCore import (
    Qt,
    Signal,
    QPoint,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QInputDialog,
    QMessageBox,
    QGraphicsDropShadowEffect,
    QSizePolicy,
    QSplitter,
    QStackedLayout,
    QGraphicsOpacityEffect,
    QScrollArea,
)

# Import the interaction + MedlinePlus logic
from interaction_xml_parser import get_drug_interactions
from medline_plus_parsing import extract_medline_data


class DragComponent(QLabel):
    moved = Signal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setContentsMargins(25, 5, 25, 5)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            """
            QLabel {
                background-color: #001f3f;
                color: #e6f2ff;
                border: 2px solid #3399ff;
                border-radius: 10px;
                font-size: 16px;
            }
            QLabel:hover {
                border: 2px solid #66b3ff;
            }
            """
        )

        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(25)
        glow.setColor(QColor("#3399ff"))
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)

        # Store data separately from display label, but use label for default
        self.data = text
        self._drag_offset = QPoint(0, 0)

    def set_data(self, data):
        self.data = data

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            # Remember where inside the widget the click occurred
            self._drag_offset = e.position().toPoint()
            # Bring to front
            self.raise_()

    # Enables dragging
    def mouseMoveEvent(self, e):
        # Check if left mouse button pressed
        if e.buttons() & Qt.LeftButton:
            new_pos = self.mapToParent(e.position().toPoint() - self._drag_offset)
            self.move(new_pos)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self.moved.emit()

class Canvas(QWidget):
    overlapped = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.setMinimumSize(400, 0)
        self.setStyleSheet(
            """
                background-color: #001733;
                border: 1px solid #333333;
            """
        )

    def add_component(self, text):
        comp = DragComponent(text, self)
        comp.adjustSize()

        # Simple staggered starting positions
        offset = 50 * len(self.items)
        start_pos = QPoint(40 + offset, 40 + offset)
        comp.move(start_pos)
        comp.show()

        comp.moved.connect(self.check_overlaps)
        self.items.append(comp)

    def check_overlaps(self):
        # Check all pairs for intersection
        for i in range(len(self.items)):
            for j in range(i + 1, len(self.items)):
                a = self.items[i]
                b = self.items[j]
                if a.geometry().intersects(b.geometry()):
                    # Emit signal with their labels
                    self.overlapped.emit(a.text(), b.text())


class FlashCards(QWidget):
    def __init__(self, front_text: str, back_text: str, parent=None):
        super().__init__(parent)

        self.front_label = QLabel(front_text)
        self.back_label = QLabel(back_text)

        for lbl in (self.front_label, self.back_label):
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                """
                QLabel {
                    background-color: #001f3f;
                    color: #e6f2ff;
                    border: 2px solid #3399ff;
                    border-radius: 10px;
                    font-size: 16px;
                }
                QLabel:hover {
                    border: 2px solid #66b3ff;
                }
                """
            )
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.stack = QStackedLayout()
        self.stack.addWidget(self.front_label)
        self.stack.addWidget(self.back_label)
        self.stack.setCurrentIndex(0)

        root_layout = QVBoxLayout(self)
        root_layout.addLayout(self.stack)

        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)

        self.anim = QPropertyAnimation(self.effect, b"opacity", self)
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.anim.finished.connect(self._on_anim_finished)

        self._fading_out = False
        self._is_front = True

        self.setMinimumSize(220, 120)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.flip()
        super().mousePressEvent(event)

    def flip(self):
        self._fading_out = True
        self.anim.stop()
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.start()

    def _on_anim_finished(self):
        if self._fading_out:
            # swap side when fully transparent
            self._is_front = not self._is_front
            self.stack.setCurrentIndex(0 if self._is_front else 1)

            # fade back in
            self._fading_out = False
            self.anim.stop()
            self.anim.setStartValue(0.0)
            self.anim.setEndValue(1.0)
            self.anim.start()


class ResultsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.container = QWidget()
        self.vlayout = QVBoxLayout(self.container)
        self.vlayout.setAlignment(Qt.AlignTop)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.container)

        root_layout = QVBoxLayout(self)
        root_layout.addWidget(self.scroll)
        self.setStyleSheet(
            """
            background-color: #000066;
            color: #ffffff;
            border: 1px solid #555555;
            """
        )

    def add_flashcard(self, front_text: str, back_text: str):
        card = FlashCards(front_text, back_text)
        self.vlayout.addWidget(card)
        return card


class MainWindow(QMainWindow):
    def __init__(self):
        # Initializes parent class
        super().__init__()
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowTitle("Drug Interaction Explorer")

        self.canvas = Canvas(self)

        self.add_button = QPushButton("Add Drug")
        self.add_button.clicked.connect(self.add_new_component)
        self.add_button.setFixedHeight(48)
        self.add_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.add_button.setStyleSheet(
            """
            QPushButton {
                background-color: #01264d;
                color: #ffffff;
                border-radius: 12px;
                padding: 8px 24px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #055bb5;
            }
            QPushButton:pressed {
                background-color: #0053A6;
            }
            """
        )

        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(20)
        glow.setColor(QColor("#3399ff"))
        glow.setOffset(0, 0)
        self.add_button.setGraphicsEffect(glow)
        self.results_panel = ResultsPanel()

        container = QWidget()
        layout = QVBoxLayout(container)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.add_button)
        layout.addLayout(button_row)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.results_panel)
        splitter.setSizes([600, 400])
        layout.addWidget(splitter)

        self.setCentralWidget(container)

        # Pre-populate a few drugs
        for name in ["caffeine", "aspirin", "acetaminophen"]:
            self.canvas.add_component(name)

        # Connect overlap signal to actual logic
        self.canvas.overlapped.connect(self.handle_overlap)

        # Track which pairs we've already processed to avoid duplicate work
        self._seen_pairs = set()

    def add_new_component(self):
        # Prompt the user for the drug name
        name, ok = QInputDialog.getText(self, "New Drug", "Enter drug name:")

        if ok and name.strip():
            self.canvas.add_component(name.strip())

    def handle_overlap(self, name1, name2):
        key = tuple(sorted((name1.lower(), name2.lower())))
        if key in self._seen_pairs:
            # Already processed this combo; just ignore
            return

        self._seen_pairs.add(key)

        # Run the interaction and MedlinePlus queries
        try:
            self.display_interaction_results(name1, name2)
        except Exception as e:
            # Show error both in GUI and console
            QMessageBox.warning(self, "Error", f"An error occurred:\n{e}")

    def display_interaction_results(self, drug1: str, drug2: str):
        """
        Use get_drug_interactions and extract_medline_data
        Display a combined summary in the GUI.
        """
        # Drug-drug interaction from interaction_xml_parser
        interaction_array = get_drug_interactions(drug1, drug2)
        # [0] Drug 1, [1] Drug 2, [2] Severity, [3] URL, [4] Description, [5] Extras

        # Build interaction text
        if interaction_array and interaction_array[2] != "N/A":
            inter_text = []
            inter_text.append("DRUG–DRUG INTERACTION")
            inter_text.append(
                f"Drugs: {interaction_array[0]} and {interaction_array[1]}"
            )
            inter_text.append(f"Severity: {interaction_array[2]}")
            inter_text.append("")
            inter_text.append(interaction_array[4])  # description
            if interaction_array[3] and interaction_array[3] != "N/A":
                inter_text.append(f"Source: {interaction_array[3]}")
            interaction_section = "\n".join(inter_text)
        else:
            interaction_section = (
                f"No interaction found between {drug1} and {drug2} "
                f"(according to XML/Drugs.com scraper). This does not guarantee safety."
            )

        # Individual drug info from MedlinePlus
        med1_array = extract_medline_data(drug1)
        med2_array = extract_medline_data(drug2)

        med_sections = []

        def format_med_section(label: str, arr):
            # arr: [0] Drug 1 (title), [1] N/A, [2] N/A, [3] URL, [4] Description, [5] Extras
            if not arr:
                return f"{label}: No MedlinePlus data found."
            title = arr[0]
            url = arr[3]
            desc = arr[4]
            text = [f"{label}: {title}", ""]
            text.append(desc)
            if url and url != "N/A":
                text.append(f"Source: {url}")
            return "\n".join(text)

        med_sections.append(format_med_section("Drug 1 details", med1_array))
        med_sections.append(format_med_section("Drug 2 details", med2_array))

        self.results_panel.add_flashcard(f"interaction between {drug1} and {drug2}", interaction_section)
        self.results_panel.add_flashcard(f"{drug1} side effects", med_sections[0])
        self.results_panel.add_flashcard(f"{drug2} side effects", med_sections[1])


if __name__ == "__main__":
    app = QApplication([])
    w = MainWindow()
    w.show()
    app.exec()
