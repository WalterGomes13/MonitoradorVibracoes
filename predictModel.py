import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, classification_report,
                             confusion_matrix, ConfusionMatrixDisplay)
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

accuracy  = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, average='macro', zero_division=0)
recall    = recall_score(y_test, y_pred, average='macro', zero_division=0)
f1        = f1_score(y_test, y_pred, average='macro', zero_division=0)

def tipo_falha(label):
    if 'n' in label: return 'Normal'
    if 'B' in label: return 'Bola'
    if 'I' in label: return 'Pista interna'
    if 'O' in label: return 'Pista externa'
    return 'Desconhecido'

def severidade(label):
    for tamanho in ('007', '014', '021', '028'):
        if tamanho in label:
            return tamanho
    return 'saudável'

def avaliar_modelo():
    print("=== Todas as classes ===")
    print(f"Acurácia : {accuracy*100:.2f}%")
    print(f"Precisão : {precision*100:.2f}% (média macro)")
    print(f"Recall   : {recall*100:.2f}% (média macro)")
    print(f"F1-score : {f1*100:.2f}% (média macro)")
    print(classification_report(y_test, y_pred, zero_division=0))

    # matriz de confusão completa, normalizada pela classe real
    cm = confusion_matrix(y_test, y_pred, labels=rf2.classes_, normalize='true')
    fig, ax = plt.subplots(figsize=(14, 14))
    ConfusionMatrixDisplay(cm, display_labels=rf2.classes_).plot(
        ax=ax, include_values=False, xticks_rotation=90, cmap='Blues')
    ax.set_title('Matriz de confusão normalizada (todas as classes)')
    plt.tight_layout()
    plt.savefig('matriz_confusao_classes.png', dpi=300)

    # por tipo de falha
    y_pred_s = pd.Series(y_pred, index=y_test.index)
    tipo_real = y_test.apply(tipo_falha)
    tipo_pred = y_pred_s.apply(tipo_falha)
    tipos = ['Normal', 'Bola', 'Pista interna', 'Pista externa']

    print("=== Por tipo de falha ===")
    print(classification_report(tipo_real, tipo_pred, labels=tipos, zero_division=0))

    cm_tipo = confusion_matrix(tipo_real, tipo_pred, labels=tipos)
    fig, ax = plt.subplots(figsize=(6, 6))
    ConfusionMatrixDisplay(cm_tipo, display_labels=tipos).plot(
        ax=ax, cmap='Blues', values_format='d', colorbar=False)
    ax.set_title('Matriz de confusão por tipo de falha')
    plt.tight_layout()
    plt.savefig('matriz_confusao_tipo.png', dpi=300)

    # por severidade (diâmetro do defeito)
    print("=== Por severidade (diâmetro) ===")
    print(classification_report(y_test.apply(severidade), y_pred_s.apply(severidade),
                                zero_division=0))
    plt.show()

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
    return erroProv, diametroFalha, cargaMotor[1]
    
def previsao(dados):
    X_data = scaler.transform(dados)
    X_data_sel = X_data[:, idx]
    y_pred_data = rf2.predict(X_data_sel)
    contagem = Counter(y_pred_data)
    probs = rf2.predict_proba(X_data_sel)

    # classe vencedora pela votação majoritária entre as janelas
    classe_vencedora = contagem.most_common(1)[0][0]

    # confiança: probabilidade média da classe vencedora nas janelas em que ela venceu
    col = list(rf2.classes_).index(classe_vencedora)
    confidence = probs[y_pred_data == classe_vencedora, col].mean() * 100
    resultado = []
    resultado.append(erroLabel(classe_vencedora))
    resultado.append(f"{confidence:.2f}%")
    return resultado

if __name__ == '__main__':
    avaliar_modelo()
