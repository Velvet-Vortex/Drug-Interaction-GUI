'''
Code was adapted from the article "Drag & Drop Widgets with PySide6"
by Martin Fitzpatrick found at https://www.pythonguis.com/faq/pyside6-drag-drop-widgets/
'''

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QMainWindow,
    QVBoxLayout,
    QPushButton,
    QInputDialog,
    QTextEdit,
    QMessageBox,
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
        # Simple visual style
        self.setStyleSheet(
            """
            QLabel {
                border: 2px solid #cccccc;
                border-radius: 10px;
                background-color: #f0f0f0;
                color: #202020;
            }
            """
        )
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
        self.setMinimumSize(400, 600)
        self.setStyleSheet("background: #383838; border: 1px solid gray;")

    def add_component(self, text):
        comp = DragComponent(text, self)
        comp.adjustSize()

        # Simple staggered starting positions
        offset = 30 * len(self.items)
        start_pos = QPoint(20 + offset, 20 + offset)
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


class MainWindow(QMainWindow):
    def __init__(self):
        # Initializes parent class
        super().__init__()
        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle("Drug Interaction Explorer")

        self.canvas = Canvas(self)

        self.add_button = QPushButton("Add Drug")
        self.add_button.clicked.connect(self.add_new_component)

        # Text panel to show interaction and side effect info
        self.result_panel = QTextEdit()
        self.result_panel.setReadOnly(True)
        self.result_panel.setMinimumHeight(200)
        self.result_panel.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #555555;
            }
            """
        )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.add_button)
        layout.addWidget(self.canvas, 2)
        layout.addWidget(self.result_panel, 1)
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
        self.result_panel.append(
            f"\n=== Overlap detected: {name1} ↔ {name2} ===\nRunning interaction check..."
        )

        # Run the interaction and MedlinePlus queries
        try:
            self.display_interaction_results(name1, name2)
        except Exception as e:
            # Show error both in GUI and console
            self.result_panel.append(f"\nError while fetching data: {e}\n")
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

        full_text = (
            "\n"
            + "=" * 60
            + "\n"
            + interaction_section
            + "\n\n"
            + "-" * 60
            + "\n"
            + "\n\n".join(med_sections)
            + "\n"
            + "=" * 60
            + "\n"
        )

        self.result_panel.append(full_text)


if __name__ == "__main__":
    app = QApplication([])
    w = MainWindow()
    w.show()
    app.exec()
