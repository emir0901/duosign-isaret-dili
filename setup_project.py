import os
import csv
import numpy as np
from ml_engine import MLEngine

def generate_synthetic_data(workspace_path, file_name="harfler.csv", samples_per_letter=200):
    """
    Generates realistic synthetic sensor data for 5 Turkish sign language letters
    ('A', 'B', 'C', 'D', 'E') and saves it to the specified CSV file.
    """
    file_path = os.path.join(workspace_path, file_name)
    
    # Write headers
    headers = [
        "flex_l1","flex_l2","flex_l3","flex_l4","flex_l5",
        "flex_r1","flex_r2","flex_r3","flex_r4","flex_r5",
        "acc_l_x","acc_l_y","acc_l_z","gyro_l_x","gyro_l_y","gyro_l_z",
        "acc_r_x","acc_r_y","acc_r_z","gyro_r_x","gyro_r_y","gyro_r_z",
        "label"
    ]
    
    # Signatures for 5 letters (base values for flex sensors)
    # 10 values: 5 for Left Hand, 5 for Right Hand (TİD Two-Handed Sign Language Alphabet)
    letter_signatures = {
        'A': [150, 100, 900, 900, 900] + [900, 100, 900, 900, 900], # Sol el yumruk işaret aşağı, sağ el yumruk işaret yatay değiyor
        'B': [100, 110, 120, 115, 105] + [105, 115, 125, 98, 102],   # İki el düz açık, avuçlar/eklemler birbirine değiyor
        'C': [400, 420, 450, 430, 410] + [100, 100, 100, 100, 100],  # Sol el kıvrık C şekli, sağ el serbest düz açık
        'D': [400, 420, 450, 430, 410] + [900, 100, 900, 900, 900],  # Sol el kıvrık C şekli, sağ el işaret açık dikey değiyor
        'E': [900, 100, 900, 900, 900] + [900, 100, 100, 100, 900]   # Sol el işaret açık dikey, sağ el 3 parmak yatay değiyor
    }
    
    rows = []
    for letter, base_flex in letter_signatures.items():
        for _ in range(samples_per_letter):
            # Flex sensor values with some noise (clipped to 0-1023 range)
            flex_vals = [float(np.clip(val + np.random.normal(0, 25), 0, 1023)) for val in base_flex]
            
            # IMU accelerometer values (resting on flat surface, z is ~9.8, x/y ~0 with noise)
            acc_l = [float(np.random.normal(0, 0.2)), float(np.random.normal(0, 0.2)), float(np.random.normal(9.8, 0.2))]
            acc_r = [float(np.random.normal(0, 0.2)), float(np.random.normal(0, 0.2)), float(np.random.normal(9.8, 0.2))]
            
            # IMU gyroscope values (resting, ~0 with noise)
            gyro_l = [float(np.random.normal(0, 0.05)), float(np.random.normal(0, 0.05)), float(np.random.normal(0, 0.05))]
            gyro_r = [float(np.random.normal(0, 0.05)), float(np.random.normal(0, 0.05)), float(np.random.normal(0, 0.05))]
            
            # Combine sensor values
            sensor_vals = flex_vals + acc_l + gyro_l + acc_r + gyro_r
            rows.append(sensor_vals + [letter])
            
    # Write to CSV file
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
        
    print(f"Başarıyla {len(rows)} adet yapay veri '{file_name}' dosyasına kaydedildi!")

def main():
    workspace_path = "/Users/emir/iki elli işaret dili projesi"
    
    # 1. Generate realistic data
    print("1. Harf kalibrasyonu için yapay veri seti üretiliyor...")
    generate_synthetic_data(workspace_path, samples_per_letter=250)
    
    # 2. Train all 7 models
    print("\n2. Yapay zeka modelleri eğitiliyor...")
    ml_engine = MLEngine(workspace_path=workspace_path)
    
    models = [
        "MLP",
        "XGBoost",
        "Random Forest",
        "SVM",
        "KNN",
        "Decision Tree",
        "Naive Bayes"
    ]
    
    for m in models:
        print(f"Eğitiliyor: {m}...")
        success, msg = ml_engine.train_model("harfler.csv", m)
        print(f"Sonuç - {m}: {msg}")
        
    print("\n🎉 Tüm yapay zeka modelleri başarıyla eğitildi ve models/ klasörüne kaydedildi!")

if __name__ == '__main__':
    main()
