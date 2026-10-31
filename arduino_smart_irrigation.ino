#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>

// 1. KREDENSIAL WI-FI
const char* ssid     = "NAMA_WIFI";
const char* password = "PASSWORD-WIFI";

// 2. IP LAPTOP SERVER
const char* serverUrl = "http://IP_LAPTOP_SERVER/predict"; 

// 3. HARDWARE PIN
#define SOIL_PIN  32
#define DHT_PIN   14
#define RELAY_PIN 26
#define DHTTYPE   DHT22

// Inisialisasi LCD 20x4 (Alamat I2C 0x27, 20 Kolom, 4 Baris)
LiquidCrystal_I2C lcd(0x27, 20, 4);
DHT dht(DHT_PIN, DHTTYPE);

// Variabel Penyimpan Data Global
int g_suhu = 0;
int g_hum = 0;
int g_soil_percent = 0;
String g_status_tanah = "KERING";
int g_keputusan_ml = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[SYSTEM START] Memulai ESP32 Smart Irrigation System...");

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH); // Relay OFF default (Active LOW)

  dht.begin();
  lcd.init();
  lcd.backlight();

  lcd.setCursor(0, 0);
  lcd.print(" Smart Irrigation ");
  lcd.setCursor(0, 1);
  lcd.print(" Connect to WiFi... ");

  Serial.print("[WIFI] Menghubungkan ke ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n[WIFI] Terhubung! IP ESP32: " + WiFi.localIP().toString());

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(" WiFi Connected!    ");
  delay(1000);
  lcd.clear();
}

void loop() {
  // 1. Baca Sensor Fisik
  float suhu = dht.readTemperature();
  float hum = dht.readHumidity();
  int soilADC = analogRead(SOIL_PIN);

  if (!isnan(suhu) && !isnan(hum)) {
    g_suhu = (int)suhu;
    g_hum = (int)hum;
    mintaKeputusanML(g_suhu, g_hum, soilADC);
  } else {
    Serial.println("[ERROR] Gagal membaca sensor DHT22!");
  }

  // 2. Eksekusi Relay Pompa
  if (g_keputusan_ml == 1) {
    digitalWrite(RELAY_PIN, LOW);  // Pompa ON (Active LOW)
  } else {
    digitalWrite(RELAY_PIN, HIGH); // Pompa OFF
  }

  // 3. CETAK DATA KE SERIAL MONITOR ARDUINO IDE
  Serial.println("==================================================");
  Serial.printf(" [TELEMETRI] Suhu: %d C | Hum: %d %% | Soil: %d %% (ADC: %d)\n", g_suhu, g_hum, g_soil_percent, soilADC);
  Serial.println(" [STATUS]    Kondisi Tanah : " + g_status_tanah);
  Serial.println(" [KEPUTUSAN] Hasil ML      : " + String(g_keputusan_ml == 1 ? "SIRAM YA (1)" : "TUNDA SIRAM (0)"));
  Serial.println(" [POMPA]     Status Relay  : " + String(g_keputusan_ml == 1 ? "ON" : "OFF"));
  Serial.println("==================================================\n");

  // 4. TAMPILAN FULL LENGKAP LCD 20x4
  
  // Baris 1: Suhu (°C), Hum Udara (%), Soil Tanah (%)
  lcd.setCursor(0, 0);
  lcd.print("T:"); lcd.print(g_suhu); lcd.print("C H:"); lcd.print(g_hum); lcd.print("% S:"); lcd.print(g_soil_percent); lcd.print("%   ");

  // Baris 2: Kondisi Tekstual Tanah (KERING / LEMBAB / BASAH)
  lcd.setCursor(0, 1);
  lcd.print("Tanah : ");
  lcd.print(g_status_tanah);
  lcd.print("       "); 

  // Baris 3: Hasil ML (Rekomendasi)
  lcd.setCursor(0, 2);
  if (g_keputusan_ml == 1) {
    lcd.print("ML    : SIRAM YA    ");
  } else {
    lcd.print("ML    : TUNDA SIRAM ");
  }

  // Baris 4: Status Eksekusi Relay Pompa
  lcd.setCursor(0, 3);
  if (g_keputusan_ml == 1) {
    lcd.print("Pompa : [ON]        ");
  } else {
    lcd.print("Pompa : [OFF]       ");
  }

  delay(5000); // Send telemetri tiap 5 detik
}

void mintaKeputusanML(float t, float h, int soil) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  String jsonBody = "{\"suhu\":" + String(t) + 
                    ",\"kelembapan_udara\":" + String(h) + 
                    ",\"sensor_tanah\":" + String(soil) + "}";

  int httpResponseCode = http.POST(jsonBody);

  if (httpResponseCode == 200) {
    String response = http.getString();
    DynamicJsonDocument doc(512);
    deserializeJson(doc, response);
    
    g_keputusan_ml = doc["keputusan_siram"];
    g_soil_percent = doc["kelembapan_tanah_persen"];
    
    String statusTemp = doc["status_tanah"].as<String>();
    statusTemp.toUpperCase();
    g_status_tanah = statusTemp;
  } else {
  }

  http.end();
}