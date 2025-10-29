import sys
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, sample_rate, window_size, axis: str):
        super().__init__()

        self.sample_rate = sample_rate
        self.window_size = window_size

        self.plot_graph = pg.PlotWidget()
        self.setCentralWidget(self.plot_graph)

        plot_item = self.plot_graph.getPlotItem()
        plot_item.setTitle(f"Espectro de frequência (FFT) em tempo real - Eixo {axis}")
        plot_item.setLabel('left', 'Amplitude (g)')
        plot_item.setLabel('bottom', 'Frequência (Hz)')
        plot_item.showGrid(x=True, y=True, alpha=0.3)
        plot_item.setYRange(0, 2)

        self.freq_axis = np.fft.rfftfreq(self.window_size, d=1.0 / self.sample_rate)
        colors = {'X': '#FF4136', 'Y': '#2ECC40', 'Z': '#0074D9'}
        pen_color = colors.get(axis, 'y')
        self.plot_line = self.plot_graph.plot([], [], pen=pen_color)

    def update_fft_plot(self, fft_magnitudes):
        if len(self.freq_axis) == len(fft_magnitudes):
            start_index = 11
            self.plot_line.setData(self.freq_axis[start_index:], fft_magnitudes[start_index:])

    def closeEvent(self, event):
        event.accept()

def update_all_fft_plots(window_x: MainWindow, window_y: MainWindow, window_z: MainWindow, fft_magsX, fft_magsY, fft_magsZ):
    window_x.update_fft_plot(fft_magsX)
    window_y.update_fft_plot(fft_magsY)
    window_z.update_fft_plot(fft_magsZ)

def start_gui(sample_rate, window_size):
    pg.setConfigOption('background', '#111')
    pg.setConfigOption('foreground', 'w')
    pg.setConfigOption('antialias', True)
    app = QtWidgets.QApplication(sys.argv)
    main_window_x = MainWindow(sample_rate=sample_rate, window_size=window_size, axis='X')
    main_window_x.setGeometry(50, 50, 800, 500)

    main_window_y = MainWindow(sample_rate=sample_rate, window_size=window_size, axis='Y')
    main_window_y.setGeometry(860, 50, 800, 500)

    main_window_z = MainWindow(sample_rate=sample_rate, window_size=window_size, axis='Z')
    main_window_z.setGeometry(50, 560, 800, 500)

    main_window_x.show()
    main_window_z.show()
    main_window_y.show()
    return app, main_window_x, main_window_y, main_window_z