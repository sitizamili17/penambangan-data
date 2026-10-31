# Penambangan Data Agroklimatologi Open-Meteo Berbasis IoT dengan Random Forest Classifier

Kode proyek tim **DIMAS-TI AMLI 2026 – Divisi Penambangan Data**
Program Studi Ilmu Komputer, FMIPA, Universitas Negeri Medan.

Prototipe irigasi cerdas yang memutuskan **Siram** atau **Tunda Siram** berdasarkan kondisi tanah, kondisi udara, dan prakiraan peluang hujan per jam dari Open-Meteo (Kota Medan).

## Tim
- Siti Haliza Zamili (4241250019) – Ketua
- Khodotun Hadawiyah Margolang (4242250002)
- Hafizham Mufti Siregar (4243250020)
- Dosen Pendamping: Dedy Kiswanto

## Cara kerja
1. ESP32 membaca suhu dan kelembapan udara (DHT22) serta nilai ADC sensor tanah kapasitif.
2. ESP32 mengirim data JSON (`suhu`, `kelembapan_udara`, `sensor_tanah`) lewat HTTP POST ke server Flask di `http://<IP_LAPTOP>:5000/predict`.
3. Server mengambil `precipitation_probability` per jam dari Open-Meteo, membentuk fitur peluang hujan jam berjalan dan jendela waktu, lalu menjalankan `RandomForestClassifier(n_estimators=10, random_state=42)`.
4. Server membalas keputusan (`keputusan_siram`: 1 = siram, 0 = tunda). ESP32 menggerakkan relai/pompa dan menampilkan status di LCD 20x4.

**Lima fitur model:** suhu, kelembapan udara, ADC tanah, peluang hujan maksimum pada jendela waktu, peluang hujan jam berjalan.

**Jendela waktu:** Tahap 1 (pukul 06.00–15.59) memakai maksimum pukul 09.00–15.59; Tahap 2 (di luar itu) memakai maksimum pukul 20.00–04.59.

## Struktur folder
```
arduino_smart_irrigation/   kode ESP32 (Arduino IDE)
server/server_ml.py         server Flask + model Random Forest
requirements.txt            pustaka Python
```

## Perangkat keras
ESP32, DHT22 (pin 14), sensor kelembapan tanah kapasitif (pin 32), modul relai active LOW (pin 26), pompa mini, LCD I2C 20x4 (alamat 0x27).

Kalibrasi sensor tanah: ADC 3230 = kering (0%), ADC 2590 = basah (100%).

## Cara menjalankan
**Server (laptop)**
```bash
pip install -r requirements.txt
python server/server_ml.py
```
Server berjalan di port 5000 dan membutuhkan internet untuk mengambil data Open-Meteo.

**ESP32 (Arduino IDE)**
1. Pasang pustaka: ArduinoJson, LiquidCrystal_I2C, DHT sensor library.
2. Buka `arduino_smart_irrigation/arduino_smart_irrigation.ino`.
3. Ganti `NAMA_WIFI`, `PASSWORD_WIFI`, dan `IP_LAPTOP_SERVER` (laptop dan ESP32 harus berada di Wi-Fi yang sama).
4. Unggah ke ESP32, lalu buka Serial Monitor (115200 baud).

## Keterbatasan
Model dilatih dari tujuh sampel yang disusun manual (ada di `server/server_ml.py`) dan belum dievaluasi dengan data uji terpisah.
