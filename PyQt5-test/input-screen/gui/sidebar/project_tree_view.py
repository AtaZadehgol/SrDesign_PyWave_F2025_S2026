from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt, pyqtSignal
from .tree_items import ProblemDefinitionScreenItem, ResultScreenItem


class ProjectTree(QTreeWidget):
    screen_selected = pyqtSignal(object)  # Emits the screen object
    RESULTS_LABEL = "Results"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setMinimumWidth(250)
        self.setDragDropMode(self.NoDragDrop)
        self.setIndentation(16)
        self._show_empty_state()
        self.itemClicked.connect(self._on_item_clicked)

    def _show_empty_state(self):
        self.clear()
        empty_item = QTreeWidgetItem(["No screens. Right-click to add a screen."])
        empty_item.setDisabled(True)
        self.addTopLevelItem(empty_item)

    def add_problem_screen(self, screen):
        if self.topLevelItemCount() == 1 and self.topLevelItem(0).isDisabled():
            self.clear()
        item = ProblemDefinitionScreenItem(screen)
        self.addTopLevelItem(item)
        self.setCurrentItem(item)

    def add_result_screen(self, screen):
        if self.topLevelItemCount() == 1 and self.topLevelItem(0).isDisabled():
            self.clear()

        parent = self._ensure_results_group()
        item = ResultScreenItem(screen)
        parent.addChild(item)
        parent.setExpanded(True)
        self.setCurrentItem(item)

    def remove_screen(self, item):
        parent = item.parent()
        if parent is not None:
            parent.removeChild(item)
            if parent.text(0) == self.RESULTS_LABEL and parent.childCount() == 0:
                idx = self.indexOfTopLevelItem(parent)
                if idx != -1:
                    self.takeTopLevelItem(idx)
            if self.topLevelItemCount() == 0:
                self._show_empty_state()
            return

        idx = self.indexOfTopLevelItem(item)
        if idx != -1:
            self.takeTopLevelItem(idx)
        if self.topLevelItemCount() == 0:
            self._show_empty_state()

    def _ensure_results_group(self):
        for i in range(self.topLevelItemCount()):
            top_item = self.topLevelItem(i)
            if top_item.text(0) == self.RESULTS_LABEL and not hasattr(top_item, "get_data"):
                return top_item

        group = QTreeWidgetItem([self.RESULTS_LABEL])
        # Group header is intentionally non-selectable; it should only collapse/expand children.
        group.setFlags(Qt.ItemIsEnabled)
        self.addTopLevelItem(group)
        return group

    def iter_screen_items(self):
        def _walk(node):
            for idx in range(node.childCount()):
                child = node.child(idx)
                if hasattr(child, "get_data"):
                    yield child
                yield from _walk(child)

        root = self.invisibleRootItem()
        yield from _walk(root)

    def get_result_screens(self):
        result_screens = []
        for item in self.iter_screen_items():
            screen = item.get_data()
            if screen.__class__.__name__ == "ResultScreen":
                result_screens.append(screen)
        return result_screens

    def find_item_for_screen(self, screen):
        for item in self.iter_screen_items():
            if item.get_data() == screen:
                return item
        return None

    def _on_item_clicked(self, item, column):
        if item.text(0) == self.RESULTS_LABEL and not hasattr(item, "get_data"):
            item.setExpanded(not item.isExpanded())
            return

        if hasattr(item, "get_data"):
            self.screen_selected.emit(item.get_data())
