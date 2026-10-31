from flask import Flask, request, jsonify
from sklearn.ensemble import RandomForestClassifier
import numpy as np
import requests
from datetime import datetime
import logging

app = Flask(__name__)

# Matikan log HTTP bawaan Flask agar terminal tidak berantakan
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- 1. KOORDINAT MEDAN & API OPEN-METEO ---
LATITUDE = 3.596585
LONGITUDE = 98.712463

# --- 2. DATASET ML (HASIL KALIBRASI SENSOR TERBARU) ---
X_train = np.array([
    # [Suhu, Hum_Udara, Soil_ADC, Hujan_Window, Hujan_Jam_Ini]
    [32, 55, 3230, 10, 0],   # KERING (~3230), Window Cerah, Jam Ini Cerah   -> SIRAM (1)
    [30, 60, 3200, 70, 0],   # KERING (~3200), Window Ada Hujan, Jam Ini 0%  -> TUNDA (0)
    [28, 85, 3220, 80, 80],  # KERING (~3220), Sedang Hujan Saat Ini (80%)  -> TUNDA (0)
    [27, 85, 2590, 10, 0],   # BASAH (~2590), Window Cerah                 -> TUNDA (0)
    [25, 90, 2580, 90, 90],  # BASAH (~2580), Sedang Hujan                 -> TUNDA (0)
    [29, 75, 3230, 15, 0],   # KERING Malam (~3230), Window Cerah          -> SIRAM (1)
    [26, 88, 3210, 75, 0],   # KERING Malam (~3210), Window Hujan Malam    -> TUNDA (0)
])

y_train = np.array([1, 0, 0, 0, 0, 1, 0])

model = RandomForestClassifier(n_estimators=10, random_state=42)
model.fit(X_train, y_train)

# Variabel Global Penyimpan Data Cuaca & Tanggal Update
data_peluang = [0] * 24
tanggal_terakhir_fetch = ""

def perbarui_prakiraan_cuaca():
    """Mengambil dan menampilkan tabel prediksi cuaca 24 jam dari Open-Meteo"""
    global data_peluang, tanggal_terakhir_fetch
    
    hari_ini = datetime.now().strftime("%Y-%m-%d")
    
    # Ambil data baru jika belum ada data atau tanggal sudah berganti hari
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&hourly=precipitation_probability&timezone=auto&forecast_days=1"
        res = requests.get(url, timeout=5).json()
        
        times = res['hourly']['time']
        probs = res['hourly']['precipitation_probability']
        
        data_peluang = probs
        tanggal_terakhir_fetch = hari_ini
        
        print("\n" + "="*68)
        print(f"   PREDIKSI CUACA & PELUANG HUJAN 24 JAM ({datetime.now().strftime('%d-%m-%Y')})   ")
        print("="*68)
        print(f" {'JAM (WIB)':^12} | {'PELUANG HUJAN':^15} | {'STATUS PREDIKSI CUACA':^30} ")
        print("-" * 68)
        
        jadwal_hujan = []
        for t, p in zip(times, probs):
            jam = t.split("T")[1] # Ambil HH:00
            
            if p >= 90:
                status = "Hujan"
            elif p >= 50:
                status = "Berpotensi Hujan"
            elif p >= 30:
                status = "Berawan"
            else:
                status = "Cerah"
                
            print(f" {jam:^12} | {f'{p}%':^15} | {status:<30}")
            
            if p >= 40:
                jadwal_hujan.append((jam, p))
                
        print("="*68)
        if jadwal_hujan:
            print(" [RINGKASAN JAM RAIN WINDOW]:")
            for j, p in jadwal_hujan:
                print(f"  * Jam {j} WIB -> Peluang Hujan: {p}%")
        else:
            print(" [RINGKASAN JAM RAIN WINDOW]: Cuaca diprediksi cerah seharian.")
        print("="*68 + "\n")
        
    except Exception as e:
        print(f"[ERROR API CUACA] Gagal memperbarui data cuaca: {e}\n")

# Ambil cuaca 24 jam saat server startup
perbarui_prakiraan_cuaca()

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Cek apakah tanggal sudah berganti hari (Otomatis perbarui cuaca 24 jam harian)
        if datetime.now().strftime("%Y-%m-%d") != tanggal_terakhir_fetch:
            perbarui_prakiraan_cuaca()

        data = request.get_json(force=True)
        
        suhu = float(data.get('suhu', 0))
        kelembapan_udara = float(data.get('kelembapan_udara', 0))
        sensor_tanah = float(data.get('sensor_tanah', 3230))
        
        # --- KONVERSI ADC KE PERSENTASE (0% - 100%) ---
        ADC_DRY = 3230.0   # 0%
        ADC_WET = 2590.0   # 100%
        
        kelembapan_tanah_persen = ((ADC_DRY - sensor_tanah) / (ADC_DRY - ADC_WET)) * 100.0
        kelembapan_tanah_persen = max(0.0, min(100.0, kelembapan_tanah_persen))
        
        if kelembapan_tanah_persen < 30:
            status_kondisi_tanah = "Kering"
        elif kelembapan_tanah_persen <= 70:
            status_kondisi_tanah = "Lembab"
        else:
            status_kondisi_tanah = "Basah"

        # Ambil jam lokal laptop saat ini
        jam_sekarang = datetime.now().hour
        hujan_jam_ini = data_peluang[jam_sekarang] if len(data_peluang) > jam_sekarang else 0

        # --- EVALUASI JENDELA WAKTU PENYIRAMAN ---
        if 6 <= jam_sekarang < 16:
            keterangan_window = "Tahap 1 (Window 09.00-16.00 / 8 Jam)"
            hujan_window = max(data_peluang[9:16]) if len(data_peluang) >= 16 else 0
        else:
            keterangan_window = "Tahap 2 (Window 20.00-05.00 / 9 Jam)"
            hujan_malam = data_peluang[20:24] if len(data_peluang) >= 24 else []
            hujan_subuh = data_peluang[0:5] if len(data_peluang) >= 5 else []
            hujan_window = max(hujan_malam + hujan_subuh) if (hujan_malam or hujan_subuh) else 0

        # Prediksi ML
        input_data = np.array([[suhu, kelembapan_udara, sensor_tanah, hujan_window, hujan_jam_ini]])
        prediksi = model.predict(input_data)[0]
        
        respon = {
            "status": "success",
            "keputusan_siram": int(prediksi),
            "keterangan": "Pompa ON" if prediksi == 1 else "Pompa OFF",
            "kelembapan_tanah_persen": int(round(kelembapan_tanah_persen)),
            "status_tanah": status_kondisi_tanah,
            "window": keterangan_window,
            "hujan_jam_ini": float(hujan_jam_ini),
            "max_hujan_window": float(hujan_window)
        }
        
        # Log Telemetri di Terminal
        print("-" * 68)
        print(f" [TELEMETRI ESP32]  Suhu: {suhu:.1f}°C | Hum: {kelembapan_udara:.1f}% | Soil: {kelembapan_tanah_persen:.1f}% (ADC: {sensor_tanah:.0f})")
        print(f" [EVALUASI WAKTU]  Jam: {jam_sekarang:02d}:00 WIB | Peluang Hujan Jam Ini: {hujan_jam_ini}%")
        print(f" [LOGIKA WINDOW]   {keterangan_window} | Max Hujan: {hujan_window}%")
        print(f" [KEPUTUSAN ML]    >>> {respon['keterangan']} <<<")
        print("-" * 68 + "\n")
        
        return jsonify(respon), 200

    except Exception as e:
        print(f"[ERROR PREDICT] {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    print("\n=====================================================================")
    print("   SERVER SMART IRRIGATION MACHINE LEARNING (READY & LISTENING)     ")
    print("=====================================================================")
    app.run(host='0.0.0.0', port=5000, debug=True)