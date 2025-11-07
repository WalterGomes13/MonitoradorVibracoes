#processa os dados de falhas e cria csv com todos os dados juntos, com coluna de dados e o rótulo do defeito
import scipy.io
import seaborn as sns
import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import signal

taxa_original = 12000
taxa_alvo = 1000
"""
df = pd.DataFrame(columns=['DE_data', 'fault'])

for root, dirs, files in os.walk("dados_vibracao_defeitos", topdown=False):
    for file_name in files:
        path = os.path.join(root, file_name)
        print(path)

        mat = scipy.io.loadmat(path)

        #key_name = list(mat.keys())[3]
        key_name = None
        for key in mat.keys():
            if 'DE_time' in key:
                key_name = key
                break

        if key_name is None:
            print(f"Aviso: Chave 'DE_time' não encontrada em {file_name}. Pulando arquivo!")
            continue

        DE_data = mat.get(key_name).flatten()

        duracao_sinal = len(DE_data) / taxa_original
        num_amostras_alvo = int(duracao_sinal*taxa_alvo)
        sinal_1kHz = signal.resample(DE_data, num_amostras_alvo)

        print(f"Shape do sinal original (12kHz): {DE_data.shape}")
        print(f"Shape do novo sinal (1kHz): {sinal_1kHz.shape}")

        fault = np.full((len(sinal_1kHz), 1), file_name[:-4])

        df_temp = pd.DataFrame({'DE_data':np.ravel(sinal_1kHz) , 'fault':np.ravel(fault)})

        df = pd.concat([df,df_temp], axis=0)
        print(df['fault'].unique())
    
df.to_csv('all_faults.csv', index = False)"""

"""df = pd.read_csv('all_faults.csv')

faults = df['fault'].unique()
for f in faults:
    plt.figure(figsize=(10,3))
    plt.plot(df[df['fault']==f].iloc[:,0])
    plt.title(f)
    plt.show()

print(df)"""