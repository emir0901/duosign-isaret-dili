import os
import csv
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler
import joblib

# Optional XGBoost import
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

class MLEngine:
    def __init__(self, workspace_path="/Users/emir/iki elli işaret dili projesi"):
        self.workspace_path = workspace_path
        self.models_dir = os.path.join(workspace_path, "models")
        os.makedirs(self.models_dir, exist_ok=True)
        
        self.scaler_path = os.path.join(self.models_dir, "scaler.pkl")
        self.scaler = None
        self.trained_models = {}
        
        # Load scaler if exists
        if os.path.exists(self.scaler_path):
            try:
                self.scaler = joblib.load(self.scaler_path)
            except Exception as e:
                print(f"Scaler yüklenirken hata oluştu: {e}")

    def save_sensor_data(self, file_name, sensor_values, label):
        """
        Saves a single frame of sensor values to the specified CSV file.
        sensor_values: list of 22 floats (10 flex + 6 Left IMU + 6 Right IMU)
        label: string target
        """
        file_path = os.path.join(self.workspace_path, file_name)
        if not os.path.exists(file_path):
            # Write headers if file doesn't exist
            headers = [
                "flex_l1","flex_l2","flex_l3","flex_l4","flex_l5",
                "flex_r1","flex_r2","flex_r3","flex_r4","flex_r5",
                "acc_l_x","acc_l_y","acc_l_z","gyro_l_x","gyro_l_y","gyro_l_z",
                "acc_r_x","acc_r_y","acc_r_z","gyro_r_x","gyro_r_y","gyro_r_z",
                "label"
            ]
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
        
        row = list(sensor_values) + [label]
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)

    def train_model(self, data_file, model_type):
        """
        Trains a classification model using data from the specified CSV file.
        model_type: 'MLP', 'XGBoost', 'Random Forest'
        """
        file_path = os.path.join(self.workspace_path, data_file)
        if not os.path.exists(file_path) or os.path.getsize(file_path) < 100:
            return False, "Eğitim dosyası bulunamadı veya yeterli veri yok."

        try:
            df = pd.read_csv(file_path)
            if len(df) < 5:
                return False, "Eğitim için en az 5 satır veri toplanmalıdır."

            X = df.drop(columns=['label']).values
            y = df['label'].values

            # En az 2 benzersiz harf (sınıf) kontrolü
            unique_classes = np.unique(y)
            if len(unique_classes) < 2:
                return False, f"Modeli eğitmek için en az 2 farklı harf (sınıf) verisi toplanmalıdır. Şu anki benzersiz harfler: {', '.join(unique_classes)}"

            # Scale inputs
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            joblib.dump(self.scaler, self.scaler_path)

            # Split dataset
            X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

            if model_type == 'MLP':
                model = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=1000, random_state=42)
            elif model_type == 'Random Forest':
                model = RandomForestClassifier(n_estimators=100, random_state=42)
            elif model_type == 'SVM':
                model = SVC(probability=True, random_state=42)
            elif model_type == 'KNN':
                model = KNeighborsClassifier(n_neighbors=5)
            elif model_type == 'Decision Tree':
                model = DecisionTreeClassifier(random_state=42)
            elif model_type == 'Naive Bayes':
                model = GaussianNB()
            elif model_type == 'XGBoost':
                if not XGBOOST_AVAILABLE:
                    return False, "Sisteminizde XGBoost kütüphanesi yüklü değil. Lütfen 'pip install xgboost' komutuyla kurun."
                # Map labels to integers for XGBoost
                from sklearn.preprocessing import LabelEncoder
                le = LabelEncoder()
                y_train_encoded = le.fit_transform(y_train)
                model = XGBClassifier(eval_metric='mlogloss', random_state=42)
                model.fit(X_train, y_train_encoded)
                # Save label encoder inside model metadata
                model.label_encoder = le
            else:
                return False, f"Bilinmeyen model tipi: {model_type}"

            if model_type != 'XGBoost':
                model.fit(X_train, y_train)

            # Test accuracy
            if model_type == 'XGBoost':
                y_pred_encoded = model.predict(X_test)
                y_pred = model.label_encoder.inverse_transform(y_pred_encoded)
            else:
                y_pred = model.predict(X_test)
                
            accuracy = np.mean(y_pred == y_test)

            # Save the trained model
            model_path = os.path.join(self.models_dir, f"{model_type.lower().replace(' ', '_')}_model.pkl")
            joblib.dump(model, model_path)
            self.trained_models[model_type] = model

            return True, f"Eğitim tamamlandı! Başarı oranı: %{accuracy*100:.2f}"

        except Exception as e:
            return False, f"Eğitim sırasında hata: {str(e)}"

    def load_model(self, model_type):
        """Loads a pre-trained model from disk."""
        model_path = os.path.join(self.models_dir, f"{model_type.lower().replace(' ', '_')}_model.pkl")
        if not os.path.exists(model_path):
            return False

        try:
            model = joblib.load(model_path)
            self.trained_models[model_type] = model
            return True
        except Exception as e:
            print(f"Model yüklenemedi: {e}")
            return False

    def predict(self, model_type, sensor_values):
        """
        Predicts the label for the given sensor values.
        sensor_values: list of 22 floats
        """
        if not self.scaler:
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
            else:
                return None, 0.0

        model = self.trained_models.get(model_type)
        if not model:
            if not self.load_model(model_type):
                return None, 0.0
            model = self.trained_models[model_type]

        try:
            X = np.array(sensor_values).reshape(1, -1)
            X_scaled = self.scaler.transform(X)

            if model_type == 'XGBoost':
                pred_encoded = model.predict(X_scaled)[0]
                label = model.label_encoder.inverse_transform([pred_encoded])[0]
                probs = model.predict_proba(X_scaled)[0]
                confidence = float(np.max(probs))
            else:
                label = model.predict(X_scaled)[0]
                probs = model.predict_proba(X_scaled)[0]
                confidence = float(np.max(probs))

            return label, confidence
        except Exception as e:
            print(f"Tahmin hatası: {e}")
            return None, 0.0
