# File: main.py
"""
Main entry point for EM Wave Visualization Tool
"""
import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from gui.main_window import EMWaveGUI

def main():

    # scale screen
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    os.environ["QT_SCALE_FACTOR"] = "1.0"

    app = QApplication(sys.argv)
    app.setStyle('Windows')

    #set global font size
    font = app.font()
    font.setPointSize(12)
    app.setFont(font)

    window = EMWaveGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

