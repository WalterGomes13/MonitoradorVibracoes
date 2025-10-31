import sys
from PyQt6 import QtWidgets
from app import VibrationAnalyzer

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    #Cria e mostra a janela principal
    main_window = VibrationAnalyzer()
    main_window.show()

    #Executa o aplicativo
    sys.exit(app.exec())