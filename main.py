import sys

from PyQt5.QtWidgets import QApplication
from app import MainWindow

def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()

# this main block is required to generate executable by pyinstaller
if __name__ == "__main__":
    main()