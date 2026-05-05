from PyQt5.QtWidgets import QMenu, QAction
from .screen_models import ProblemDefinitionScreen, ResultScreen


class TreeContextMenu(QMenu):
    def __init__(self, tree_view, parent=None):
        super().__init__(parent)
        self.tree_view = tree_view
        self._setup_actions()

    def _setup_actions(self):
        self.add_problem_action = QAction("Add Problem Definition Screen", self)
        self.add_problem_action.triggered.connect(self._add_problem_screen)
        self.add_chart_result_action = QAction("Add Chart Result Screen", self)
        self.add_chart_result_action.triggered.connect(self._add_chart_result_screen)
        self.add_heatmap_result_action = QAction("Add Heatmap Result Screen", self)
        self.add_heatmap_result_action.triggered.connect(self._add_heatmap_result_screen)
        self.add_result_action = QAction("Add Result Screen", self)
        self.add_result_action.triggered.connect(self._add_chart_result_screen)
        self.delete_action = QAction("Delete Screen", self)
        self.delete_action.triggered.connect(self._delete_screen)

    def show_for(self, pos, item=None):
        self.clear()
        self.addAction(self.add_problem_action)
        self.addAction(self.add_chart_result_action)
        self.addAction(self.add_heatmap_result_action)
        if item and not item.isDisabled() and hasattr(item, "get_data"):
            self.addSeparator()
            self.addAction(self.delete_action)
        self.exec_(self.tree_view.viewport().mapToGlobal(pos))

    def _add_problem_screen(self):
        screen = ProblemDefinitionScreen("Problem Setup")
        self.tree_view.add_problem_screen(screen)

    def _add_chart_result_screen(self):
        screen = ResultScreen("Chart", view_type="chart")
        self.tree_view.add_result_screen(screen)

    def _add_heatmap_result_screen(self):
        screen = ResultScreen("Heatmap", view_type="heatmap")
        self.tree_view.add_result_screen(screen)

    def _delete_screen(self):
        item = self.tree_view.currentItem()
        if item and not item.isDisabled() and hasattr(item, "get_data"):
            self.tree_view.remove_screen(item)
