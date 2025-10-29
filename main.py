import serial
import time
import struct
import numpy as np
import sys
from PyQt6 import QtWidgets
from plotter import start_gui, update_all_fft_plots

buffer_size = 2048
sample_rate = 1000
data_buffer_x = np.zeros(buffer_size, dtype=np.float64)
data_buffer_y = np.zeros(buffer_size, dtype=np.float64)
data_buffer_z = np.zeros(buffer_size, dtype=np.float64)
current_index = 0

#processamento de dados e criação da fft
def processamento(data_buffer):
    N = len(data_buffer)
    if N == 0:
        return np.array([])
    window = np.hanning(N)
    windowed_data = data_buffer*window
    fft_result_complex =  np.fft.rfft(windowed_data)
    fft_magnitudes_raw = np.abs(fft_result_complex)
    scaling_factor = N / 4.0
    if scaling_factor == 0:
        return fft_magnitudes_raw
    
    fft_magnitudes_g = fft_magnitudes_raw / scaling_factor
    return fft_magnitudes_g

#iniciando interface gráfica
print("Iniciando a interface gráfica...")
app, main_window_x, main_window_y, main_window_z = start_gui(sample_rate=sample_rate, window_size=buffer_size)

#abrir porta serial e receber dados
try:
    print("Abrindo porta serial...")
    ser = serial.Serial('COM8', 115200, timeout=1)
    time.sleep(2)

    print("Esperando o Esp32...")
    while True:
        line = ser.readline().decode('utf-8').strip()
        if line == "PRONTO":
            print("ESP32 pronto!")
            print("Enviando comando START...")
            ser.write(b'START\n')
            break
        elif line:
            print(f"Recebido lixo: {line}")

        app.processEvents()
    ser.flush()

    print("Lendo dados...")
    while main_window_x.isVisible() or main_window_y.isVisible() or main_window_z.isVisible():
        data = ser.read(12)

        if len(data) == 12:
            x, y, z = struct.unpack('<3f', data)
            valor_x, valor_y, valor_z = x/9.80665, y/9.80665, z/9.80665
            print(f"X: {valor_x}, Y: {valor_y}, Z: {valor_z}")

            if current_index < buffer_size:
                data_buffer_x[current_index] = valor_x
                data_buffer_y[current_index] = valor_y
                data_buffer_z[current_index] = valor_z
                current_index+=1

            elif current_index == buffer_size:
                current_index = 0
                fft_mags_x = processamento(data_buffer_x)
                fft_mags_y = processamento(data_buffer_y)
                fft_mags_z = processamento(data_buffer_z)
                update_all_fft_plots(main_window_x, main_window_y, main_window_z, fft_mags_x, fft_mags_y, fft_mags_z)

        else:
            pass

        app.processEvents()

except serial.SerialException as e:
    print(f"Erro ao abrir a porta serial: {e}")
    msgBox = QtWidgets.QMessageBox()
    msgBox.setIcon(QtWidgets.QMessageBox.Icon.Critical)
    msgBox.setText(f"Erro na porta serial: {e}")
    msgBox.setInformativeText("Verifique a porta COM e reinicie o programa.")
    msgBox.setWindowTitle("Erro de conexão")
    msgBox.exec()

finally: 
    if 'ser' in locals() and ser.is_open:
        print("Fechando porta serial.")
        ser.close()
    print("Encerrando aplicação.")
