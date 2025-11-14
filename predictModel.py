import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from collections import Counter

df_sample = pd.read_csv('./sample_data/dataset_de_features.csv')
#df_sample.info()

X = df_sample.drop('fault', axis = 1)
y = df_sample['fault']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, 
    test_size=0.25, 
    random_state=42, 
    stratify=y
)

scaler = MinMaxScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)
#print(f"Training set size: {X_train.shape}, Testing set size: {X_test.shape}")

rf = RandomForestClassifier(
    n_estimators=500,
    max_depth=15,
    random_state=42,
    n_jobs=-1
)
rf.fit(X_train, y_train)
importances = rf.feature_importances_

idx = np.argsort(importances)[-200:]

X_train_sel = X_train[:, idx]
X_test_sel = X_test[:, idx]

rf2 = RandomForestClassifier(
    n_estimators=500,
    max_depth=15,
    random_state=42,
    n_jobs=-1
)

rf2.fit(X_train_sel, y_train)
y_pred = rf2.predict(X_test_sel)
accuracy = accuracy_score(y_test, y_pred)
#print(f"Accuracy of the model: {accuracy *100:.2f}%")

def erroLabel(erro):
    print(erro)
    erroProv, diametroFalha, cargaMotor = '', '',''
    indexUnderscore = erro.index('_')
    if 'B' in erro: erroProv = 'Bola'
    if 'I' in erro: erroProv = 'Pista interna'
    if 'n' in erro: erroProv = 'Vibração normal'
    if 'O' in erro:
        indexArrob = erro.index('@')
        positionRelative = erro[indexArrob:indexUnderscore]
        if positionRelative == '6': erroProv = 'Pista externa, Posição relativa à zona de carga: Centrada'
        if positionRelative == '3': erroProv = 'Pista externa, Posição relativa à zona de carga: Ortogonal'
        if positionRelative == '12': erroProv = 'Pista externa, Posição relativa à zona de carga: Oposta'
    if '007' in erro: diametroFalha = '0.007 polegadas'
    if '014' in erro: diametroFalha = '0.014 polegadas'
    if '021' in erro: diametroFalha = '0.021 polegadas'
    if '028' in erro: diametroFalha = '0.028 polegadas'
    cargaMotor = erro[indexUnderscore:]
    return f"ERRO PROVÁVEL: {erroProv} | DIAMETRO DA FALHA: {diametroFalha} | CARGA DO MOTOR: {cargaMotor[1]}"
    
def previsao(dados):
    X_data = scaler.transform(dados)
    X_data_sel = X_data[:, idx]
    y_pred_data = rf2.predict(X_data_sel)
    contagem = Counter(y_pred_data)
    probs = rf2.predict_proba(X_data_sel)
    confidence = np.max(probs) * 100
    resultado = f"{erroLabel(contagem.most_common(1)[0][0])} ; confiança = {confidence:.2f}%"
    return resultado

