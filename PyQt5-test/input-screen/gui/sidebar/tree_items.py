from PyQt5.QtWidgets import QTreeWidgetItem

class ProblemDefinitionScreenItem(QTreeWidgetItem):
    def __init__(self, screen):
        super().__init__([screen.name])
        self.screen = screen
        # self.setIcon(0, None)  # Removed: QIcon required, None not allowed
        self.setToolTip(0, 'Problem Definition Screen')

    def get_data(self):
        return self.screen

class ResultScreenItem(QTreeWidgetItem):
    def __init__(self, screen):
        super().__init__([screen.name])
        self.screen = screen
        # self.setIcon(0, None)  # Removed: QIcon required, None not allowed
        view_label = str(getattr(screen, "view_type", "chart")).title()
        self.setToolTip(0, f'{view_label} Result Screen')

    def get_data(self):
        return self.screen
