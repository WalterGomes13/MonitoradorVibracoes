import sys
import serial
import time
import struct
import numpy as np
import pyqtgraph as pg
from datetime import datetime
from PyQt6 import QtWidgets, QtCore, QtGui
from predictModel import previsao

COM_PORT = 'COM8'
BAUD_RATE = 115200
BUFFER_SIZE = 2048
SAMPLE_RATE = 1000

def processamento(data_buffer):
    N = len(data_buffer)
    if N == 0:
        return np.array([])
    data_buffer_ac = data_buffer - np.mean(data_buffer)
    window = np.hanning(N)
    windowed_data = data_buffer_ac*window
    fft_result_complex =  np.fft.rfft(windowed_data)
    fft_magnitudes_raw = np.abs(fft_result_complex)
    scaling_factor = N / 4.0
    if scaling_factor == 0:
        return fft_magnitudes_raw
    
    fft_magnitudes_g = fft_magnitudes_raw / scaling_factor
    return fft_magnitudes_g

class SerialWorker(QtCore.QObject):
    dataReady = QtCore.pyqtSignal(np.ndarray, np.ndarray, np.ndarray)
    predictionReady = QtCore.pyqtSignal(str, str)
    errorOccurred = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._is_running = True
        self.data_buffer_x = np.zeros(BUFFER_SIZE, dtype=np.float64)
        self.data_buffer_y = np.zeros(BUFFER_SIZE, dtype=np.float64)
        self.data_buffer_z = np.zeros(BUFFER_SIZE, dtype=np.float64)
        self.current_index = 0
        self.data_sample = []
        self.ser = None

    def stop(self):
        self._is_running = False

    def run(self):
        try:
            print("Worker: Abrindo porta serial...")
            self.ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)

            print("Worker: Esperando o ESP 32...")
            while self._is_running:
                line = self.ser.readline().decode('utf-8').strip()
                if line == 'PRONTO':
                    print("Worker: ESP32 pronto!")
                    self.ser.write(b'START\n')
                    break
                elif not self._is_running:
                    if self.ser and self.ser.is_open:
                        self.ser.close()
                    return
                
            self.ser.flush()
            print("Worker: Lendo dados...")

            while self._is_running:
                data = self.ser.read(12)

                if len(data) == 12:
                    x, y, z = struct.unpack('<3f', data)
                    valor_x, valor_y, valor_z = x/9.80665, y/9.80665, z/9.80665
                    #print(f"X: {valor_x}, Y: {valor_y}, Z: {valor_z}")

                    if self.current_index < BUFFER_SIZE:
                        self.data_buffer_x[self.current_index] = valor_x
                        self.data_buffer_y[self.current_index] = valor_y
                        self.data_buffer_z[self.current_index] = valor_z
                        self.current_index+=1

                    if self.current_index >= BUFFER_SIZE:
                        self.current_index = 0
                        fft_mags_x = processamento(self.data_buffer_x)[1:]
                        fft_mags_y = processamento(self.data_buffer_y)[1:]
                        fft_mags_z = processamento(self.data_buffer_z)[1:]

                        self.data_sample.append(list(fft_mags_y))

                        if len(self.data_sample) == 15:
                            buffer = self.data_buffer_y
                            buffer_ac = buffer - np.mean(buffer)
                            rms = np.sqrt(np.mean(np.square(buffer_ac)))
                            hora = datetime.now().strftime("%H:%M:%S")
                            if rms < 0.02:
                                self.predictionReady.emit("Máquina parada - estado normal", hora)
                            else:
                                self.predictionReady.emit(previsao(self.data_sample), hora)

                            self.data_sample = []

                        self.dataReady.emit(fft_mags_x, fft_mags_y, fft_mags_z)

            print("Worker: Loop encerrado. Enviando comando CLOSE...")
            if self.ser and self.ser.is_open:
                self.ser.write(b'CLOSE\n')
                self.ser.flush()

        except serial.SerialException as e:
            self.errorOccurred.emit(f"Erro na porta serial: {e}")
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
            print("Worker: Thread encerrada.")

class VibrationAnalyzer(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Monitorador de Vibração (3 eixos)")
        self.setGeometry(100, 100, 1000, 800)

        #Configurações do PyQtGraph
        pg.setConfigOption('background', '#111')
        pg.setConfigOption('foreground', 'w')
        pg.setConfigOption('antialias', True)

        #Layout principal
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)

        #Botão de iniciar
        self.start_button = QtWidgets.QPushButton("Iniciar monitoramento")
        font = self.start_button.font()
        font.setPointSize(16)
        self.start_button.setFont(font)
        self.start_button.clicked.connect(self.start_monitoring)
        self.main_layout.addWidget(self.start_button)

        #Container para os gráficos (incialmente vazio)
        self.graph_container = QtWidgets.QWidget()
        self.graph_layout = QtWidgets.QVBoxLayout(self.graph_container)
        self.main_layout.addWidget(self.graph_container)

        self.result_label = QtWidgets.QLabel("Aguardando dados...")
        font = self.result_label.font()
        font.setPointSize(14)
        self.result_label.setFont(font)
        self.result_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.result_label)

        self.freq_axis = np.fft.rfftfreq(BUFFER_SIZE, d=1.0 / SAMPLE_RATE)[1:]

        self.thread = None
        self.worker = None

    def start_monitoring(self):
        #Desativa o botão
        self.start_button.setEnabled(False)
        self.start_button.setText("Monitorando...")

        #Cria os 3 gráficos e adiciona ao layout
        #self.plot_x, self.line_x = self.create_plot("Eixo X", color = '#FF4136')
        self.plot_y, self.line_y = self.create_plot("Eixo Y", color = '#2ECC40')
        #self.plot_z, self.line_z = self.create_plot("Eixo Z", color = '#0074D9')

        #self.graph_layout.addWidget(self.plot_x)
        self.graph_layout.addWidget(self.plot_y)
        #self.graph_layout.addWidget(self.plot_z)
        
        #Configura e inicia a thread
        self.thread = QtCore.QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self.thread)

        #Conecta os sinais da thread às funções da interface
        self.thread.started.connect(self.worker.run)
        self.worker.dataReady.connect(self.update_graphs)
        self.worker.errorOccurred.connect(self.show_error)

        self.worker.predictionReady.connect(self.update_prediction_label)

        #Inicia a thread
        self.thread.start()

    @QtCore.pyqtSlot(np.ndarray, np.ndarray, np.ndarray)
    def update_graphs(self, fft_mags_x, fft_mags_y, fft_mags_z):
        if len(self.freq_axis) == len(fft_mags_y):
            #self.line_x.setData(self.freq_axis, fft_mags_x)
            self.line_y.setData(self.freq_axis, fft_mags_y)
            #self.line_z.setData(self.freq_axis, fft_mags_z)

    @QtCore.pyqtSlot(str, str)
    def update_prediction_label(self,texto, hora):
        if "parada" in texto.lower():
            cor = "#00FF00"
        else:
            cor = "#FF3333"
        self.result_label.setStyleSheet(f"color: {cor}; font-size: 18px;")
        self.result_label.setText(f"[{hora}] {texto}")

    def create_plot(self, title, color):
        plot_widget = pg.PlotWidget()
        plot_item = plot_widget.getPlotItem()
        plot_item.setTitle(f"Espectro de Frequência - {title}", size="16pt")
        plot_item.setLabel('left', 'Amplitude(g)')
        plot_item.setLabel('bottom', 'Frequência (Hz)')
        plot_item.showGrid(x=True, y=True, alpha=0.3)
        plot_item.setYRange(0,0.5)
        
        line = plot_widget.plot([], [], pen=pg.mkPen(color=color, width=2))
        return plot_widget, line
    
    def show_error(self, error_message):
        print(f"Erro:{error_message}")
        self.start_button.setText("Falha na Conexão")
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msgBox.setText(error_message)
        msgBox.setInformativeText("Verifique a porta COM e reinicie o programa")
        msgBox.setWindowTitle("Erro de Conexão")
        msgBox.exec()

    def closeEvent(self, event):
        print("Fechando aplicação...")
        if self.worker:
            self.worker.stop()
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        event.accept()
        