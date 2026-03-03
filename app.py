import sys
import serial
import time
import struct
import numpy as np
import pyqtgraph as pg
from datetime import datetime
from PyQt6 import QtWidgets, QtCore, uic
from predictModel import previsao

COM_PORT = 'COM8'
BAUD_RATE = 921600
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
    predictionReady = QtCore.pyqtSignal(str,str, str, str, str)
    errorOccurred = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._is_running = True
        self.data_buffer_x = np.zeros(BUFFER_SIZE, dtype=np.float64)
        self.data_buffer_y = np.zeros(BUFFER_SIZE, dtype=np.float64)
        self.data_buffer_z = np.zeros(BUFFER_SIZE, dtype=np.float64)
        self.current_index = 0
        self.data_sample = []
        self.predictingFlag = False
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
                print(line)
                if line == 'PRONTO':
                    print("Worker: ESP32 pronto!")
                    self.ser.write(b'S')
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
                    valor_x, valor_y, valor_z = x, y, z
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

                        self.dataReady.emit(fft_mags_x, fft_mags_y, fft_mags_z)

                        if len(self.data_sample) < 15 and not self.predictingFlag: self.data_sample.append(list(fft_mags_y))

                        if len(self.data_sample) == 15:
                            self.predictingFlag = True
                            buffer = self.data_buffer_y
                            buffer_ac = buffer - np.mean(buffer)
                            rms = np.sqrt(np.mean(np.square(buffer_ac)))
                            hora = datetime.now().strftime("%H:%M:%S")
                            if rms < 0.02:
                                self.predictionReady.emit("Máquina parada", "Máquina parada", "Máquina parada", "Máquina parada", hora)
                            else:
                                predict = previsao(self.data_sample)
                                self.predictionReady.emit(predict[0][0], predict[0][1], predict[0][2], predict[1], hora)

                            self.data_sample = []
                            self.predictingFlag = False


            print("Worker: Loop encerrado. Enviando comando CLOSE...")
            if self.ser and self.ser.is_open:
                self.ser.write(b'C')
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

        uic.loadUi("mainwindow.ui", self)   # <<-- carregando sua UI

        pg.setConfigOption('background', '#111')
        pg.setConfigOption('foreground', 'w')
        pg.setConfigOption('antialias', True)

        self.grafico_widget: QtWidgets.QWidget = self.findChild(QtWidgets.QWidget, "widgetGrafico")

        # Remove label interna (Aguardando dados)
        self.labelAguardando = self.findChild(QtWidgets.QLabel, "labelAguardando")
        if self.labelAguardando:
            self.labelAguardando.hide()

        # Criamos um layout no widget do designer
        self.graph_layout = QtWidgets.QVBoxLayout(self.grafico_widget)
        self.grafico_widget.setLayout(self.graph_layout)

        # BOTÃO DO DESIGNER
        self.start_button = self.findChild(QtWidgets.QPushButton, "start_button")
        self.start_button.clicked.connect(self.start_monitoring)

        # LABEL DO RESULTADO (também pega do Designer5
        self.textHora = self.findChild(QtWidgets.QTextBrowser, "textBrowser")
        self.textFalha = self.findChild(QtWidgets.QTextBrowser, "textBrowser_2")
        self.textDimFalha = self.findChild(QtWidgets.QTextBrowser, "textBrowser_3")
        self.textCarga = self.findChild(QtWidgets.QTextBrowser, "textBrowser_7")
        self.textProb = self.findChild(QtWidgets.QTextBrowser, "textBrowser_8")
        #self.result_label.setText("Aguardando dados...")

        # Frequências para FFT
        self.freq_axis = np.fft.rfftfreq(BUFFER_SIZE, d=1.0 / SAMPLE_RATE)[1:]

        self.thread = None
        self.worker = None

    def start_monitoring(self):
        self.start_button.setEnabled(False)
        self.start_button.setText("Monitorando...")

        # Criar apenas o gráfico Y
        self.plot_y, self.line_y = self.create_plot("Eixo Y", color="#2ECC40")

        # Adicionar no layout do widget criado no DESIGNER
        self.graph_layout.addWidget(self.plot_y)

        # THREAD SERIAL
        self.thread = QtCore.QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.dataReady.connect(self.update_graphs)
        self.worker.errorOccurred.connect(self.show_error)
        self.worker.predictionReady.connect(self.update_prediction_label)

        self.thread.start()


    @QtCore.pyqtSlot(np.ndarray, np.ndarray, np.ndarray)
    def update_graphs(self, fft_mags_x, fft_mags_y, fft_mags_z):
        if len(self.freq_axis) == len(fft_mags_y):
            #self.line_x.setData(self.freq_axis, fft_mags_x)
            self.line_y.setData(self.freq_axis, fft_mags_y)
            #self.line_z.setData(self.freq_axis, fft_mags_z)

    @QtCore.pyqtSlot(str, str, str, str, str)
    def update_prediction_label(self,textoFalha, textoDimFalha, textoCarga, textoProb, hora):
        if "parada" in textoFalha.lower():
            cor = "#00A300"
        else:
            cor = "#FF3333"
        #self.result_label.setStyleSheet(f"color: {cor}; font-size: 10px;")
        #self.result_label.setText(f"[{hora}] {texto}")
        self.textHora.setStyleSheet(f"color: {cor}; font-size: 15px;")
        self.textHora.setText(f"{hora}")

        self.textFalha.setStyleSheet(f"color: {cor}; font-size: 15px;")
        self.textFalha.setText(f"{textoFalha}")

        self.textDimFalha.setStyleSheet(f"color: {cor}; font-size: 15px;")
        self.textDimFalha.setText(f"{textoDimFalha}")

        self.textCarga.setStyleSheet(f"color: {cor}; font-size: 15px;")
        self.textCarga.setText(f"{textoCarga}")

        self.textProb.setStyleSheet(f"color: {cor}; font-size: 15px;")
        self.textProb.setText(f"{textoProb}")

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
        