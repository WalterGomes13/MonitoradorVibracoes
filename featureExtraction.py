#extrai as features de cada sinal de falha janelado (2048) e cria uma nova csv de features(RMS, curtose, fator de crista, valor de pico e desvio padrão)
import pandas as pd
import numpy as np
from scipy import stats
from app import processamento

WINDOW_SIZE = 2048
STEP_SIZE = 1024

df_raw = pd.read_csv('./sample_data/all_faults.csv')
labels = df_raw['fault'].unique()

all_rows = []

for label in labels:
    signal_segment = df_raw[df_raw['fault'] == label]['DE_data'].values

    for i in range(0, len(signal_segment) - WINDOW_SIZE, STEP_SIZE):
        window = signal_segment[i:i+WINDOW_SIZE]

        if len(window) < WINDOW_SIZE or np.std(window) == 0:
            continue

        fft_mags = processamento(window)[1:]
        row = list(fft_mags)
        row.append(label)
        all_rows.append(row)

print(f"Extração concluída. Total de {len(all_rows)} janelas processadas.")

if not all_rows:
    print("Nenhum dado foi processado. Encerrando")
else:
    num_features = len(all_rows[0]) - 1
    feature_columns = [f"Mag_bin_{i}" for i in range(num_features)]
    feature_columns.append('fault')

    df_features = pd.DataFrame(all_rows, columns=feature_columns)

    df_features.to_csv('dataset_de_features.csv', index=False)

    print("Novo dataset 'dataset_de_features.csv' salvo com sucesso!")
    print(df_features.head())