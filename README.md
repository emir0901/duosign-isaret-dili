# 🧠 DuoSign - Akıllı İşaret Dili Tanıma Arayüzü & Yapay Zeka Altyapısı

DuoSign, iki elli veri eldivenlerinden (ESP32 tabanlı) gelen sensör verilerini gerçek zamanlı olarak işleyen, gelişmiş yapay zeka sınıflandırma modelleri barındıran ve yazılan harfleri akıllı bir Türkçe Otomatik Düzeltme Motoru ile tamamlayan premium macOS Light Mode tasarımlı bir masaüstü uygulamasıdır.

---

## 🌟 Öne Çıkan Özellikler

* **🎨 Apple Light Mode Arayüzü:** macOS estetiklerine uygun minimalist, pürüzsüz geçişlere sahip butonlar, yuvarlatılmış kartlar ve canlı gösterge panelleri.
* **🎭 Soldan Kayan Model Çekmecesi (`ModelDrawer`):** Sol kenardan pürüzsüzce süzülen, yapay zeka model seçimini son derece kolaylaştıran modern bir yan panel.
* **🧲 Harf Kalibrasyon & Veri Toplama Merkezi:** 29 harfli Türkçe alfabeden istediğiniz harfi seçtiğiniz an sıfır gecikmeyle el hareketlerinizi okuyan ve `harfler.csv` dosyasına kaydeden veri toplama merkezi.
* **🤖 7 Farklı Makine Öğrenmesi Modeli:**
  * MLP (Multilayer Perceptron - Yapay Sinir Ağları)
  * XGBoost Classifier
  * Random Forest
  * Support Vector Machine (SVM)
  * K-Nearest Neighbors (KNN)
  * Decision Tree
  * Naive Bayes (Gaussian)
* **🟢/🟡 Dinamik Durum Takipçisi:** Seçilen modelin eğitilip eğitilmediğini kontrol eden, eğitilmemiş modelleri otomatik olarak `🟡 (Eğitilmedi)` olarak işaretleyen ve eğitildiği an `🟢 Aktif` yeşiline dönen durum paneli.
* **📝 Türkçe Otomatik Düzeltme Motoru (Real-time Word Auto-Correction):**
  * Harf harf hecelenen (örn: `S A L A M` veya `E M E R`) kelimeleri arka plandaki sözlükle asenkron kıyaslayan `SequenceMatcher` benzerlik algoritması.
  * Sözlük, root dizindeki [kelimeler.csv](kelimeler.csv) dosyasından dinamik yüklenir. İçerisinde Türkçe'de en sık kullanılan 50 kelime ile birlikte `EMİR`, `SERHAT`, `NASER`, `HARUN` gibi özel isimler yer almaktadır.
* **🔊 Sesli Geri Bildirim:** Algılanan harflerin `pyttsx3` aracılığıyla sesli olarak Türkçe seslendirilmesi desteği (isteğe bağlı).

---

## 🛠️ Gereksinimler & Kurulum

Proje Python 3.8+ ve PyQt5 tabanlıdır. Gerekli kütüphaneleri yüklemek için terminalinizden şu komutu çalıştırmanız yeterlidir:

```bash
pip install -r requirements.txt
```

---

## 🚀 Çalıştırma

Eldiveninizi USB (veya Serial) portu üzerinden bilgisayarınıza bağlayın. Uygulama, arka planda çalışan akıllı port tarayıcısı sayesinde eldiveni otomatik olarak algılayıp bağlanacaktır.

Uygulamayı başlatmak için:

```bash
python3 main.py
```

---

## 🧲 Veri Toplama & Harf Kalibrasyonu

Yapay zeka modellerini eğitebilmek için öncelikle kendi el hareketlerinizden oluşan bir veri kümesi toplamanız gerekmektedir.

1. Ana ekranın sol panelinde bulunan **"🧲 Kalibrasyon Merkezi"** butonuna tıklayın.
2. Açılan penceredeki 29 harflik alfabeden kalibre etmek istediğiniz harfe (örneğin `A` harfi) tıklayın.
3. **Harfe tıkladığınız an sistem otomatik olarak veri toplamaya başlayacaktır.** Alttaki ilerleme çubuğu (progress bar) hızla dolarken eldivenle ilgili harfin duruş şeklini koruyun.
4. Varsayılan 800 örnek toplandığında veri kaydı durur ve veriler otomatik olarak `harfler.csv` dosyasına yazılır.
5. **ÖNEMLİ:** Modellerin eğitilebilmesi ve sınıflandırma yapabilmesi için **en az 2 farklı harf** için veri toplamış olmanız gerekmektedir (Örn: Hem `A` hem de `B` harfleri için 800'er adet veri).

---

## 🤖 Yapay Zeka Modelinin Eğitilmesi

Verilerinizi başarıyla topladıktan sonra seçtiğiniz yapay zeka modelini tek tıkla eğitebilirsiniz:

1. Sol menüden **"🧠 Model Seçim Merkezi"**ni açın.
2. Eğitmek ve kullanmak istediğiniz yapay zeka modelini seçin (örneğin `MLP` veya `XGBoost`).
3. Kalibrasyon ekranındaki veya ana menüdeki mor **"🤖 Modeli Eğit"** butonuna tıklayın.
4. Sistem `harfler.csv` dosyasındaki verileri otomatik olarak okuyacak, test/eğitim verisi olarak bölecek (`train_test_split`), normalize edecek (`StandardScaler`) ve modeli eğitecektir.
5. Eğitim tamamlandığında elde edilen başarı oranı size bir bilgi kutusuyla gösterilir.
6. Eğitilen model ve ölçekleyici (scaler) dosyası otomatik olarak `models/` klasörünün içerisine (`models/mlp_model.pkl` ve `models/scaler.pkl` gibi) kaydedilir.
7. Eğitimden sonra sol alttaki gösterge anında yeşil renkli `🟢 [Model] Aktif` durumuna geçerek sistemin gerçek zamanlı tahmine başladığını bildirir!

---

## 📝 Kelime Sözlüğünü Özelleştirme

Otomatik düzeltme motorunun kelimeleri doğru tahmin edebilmesi için sözlüğe dilediğiniz kelimeleri veya yeni isimleri ekleyebilirsiniz:

1. Proje ana klasöründeki [kelimeler.csv](kelimeler.csv) dosyasını herhangi bir Excel veya metin düzenleyici ile açın.
2. En alt satıra geçerek büyük harflerle yeni kelimenizi ekleyin ve kaydedin.
3. Uygulama açılışta bu dosyayı otomatik olarak okur ve yeni yazdığınız kelimeyi de düzeltme listesine dahil eder.

---

*Geliştirici: emir0901 & DuoSign AI Team*
