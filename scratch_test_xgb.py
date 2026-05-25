# -*- coding: utf-8 -*-
# ==============================================================================
# 🧠 DuoSign - Akıllı İşaret Dili Tanıma Arayüzü & Yapay Zeka Altyapısı
# ✍️ Tasarım & Geliştirici: Recep Emirhan Öztürk (emir0901)
# ✉️ İletişim: emrhanozt06@gmail.com
# ==============================================================================

import joblib
import numpy as np
try:
    from xgboost import XGBClassifier
    from sklearn.preprocessing import LabelEncoder
    
    le = LabelEncoder()
    y = np.array(['A', 'B', 'A', 'B'])
    le.fit(y)
    
    model = XGBClassifier(use_label_encoder=False, eval_metric='mlogloss')
    X = np.random.rand(4, 22)
    y_enc = le.transform(y)
    model.fit(X, y_enc)
    
    model.label_encoder = le
    print("Saving model with label_encoder...")
    joblib.dump(model, "test_xgb.pkl")
    
    print("Loading model...")
    model_loaded = joblib.load("test_xgb.pkl")
    if hasattr(model_loaded, 'label_encoder'):
        print("Success! label_encoder exists.")
    else:
        print("Failure! label_encoder is missing.")
except Exception as e:
    print(f"Error occurred: {e}")
