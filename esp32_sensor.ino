#include "DHT.h"
#include <WiFi.h>
#include <HTTPClient.h>

// ==========================================
// CONFIGURAÇÃO DE REDE E API
// ==========================================
const char* ssid = "iPhone de Gabriel";
const char* password = "gabriel1234";

const char* serverName = "https://pyros-vision-backend-production.up.railway.app/api/sensores";

// ==========================================
// CONFIGURAÇÃO DE HARDWARE
// ==========================================
const int PINO_DHT = 14;
const int TIPO_DHT = DHT11;
const int PINO_MQ2 = 34;
const int PINO_BUZZER = 32;

const int FREQUENCIA = 2000;
const int RESOLUCAO = 8;

DHT dht(PINO_DHT, TIPO_DHT);

const int LIMIAR_FUMACA = 1500;

// Temporizador não-bloqueante para envio Wi-Fi
unsigned long ultimoEnvio = 0;
const long intervaloEnvio = 5000; // Envia dados a cada 5 segundos

// ==========================================
// ATUADORES
// ==========================================
void buzzerLigar(int frequencia) {
  ledcWriteTone(PINO_BUZZER, frequencia);
}

void buzzerDesligar() {
  ledcWriteTone(PINO_BUZZER, 0);
}

void alertaNormal() {
  buzzerDesligar();
}

void alertaAtencao() {
  buzzerLigar(1500);
  delay(100);
  buzzerDesligar();
  delay(80);
  buzzerLigar(1500);
  delay(100);
  buzzerDesligar();
  delay(600);
}

void alertaPerigo() {
  for (int i = 0; i < 3; i++) {
    for (int freq = 2000; freq <= 4000; freq += 30) {
      ledcWriteTone(PINO_BUZZER, freq);
      delay(5);
    }
    for (int freq = 4000; freq >= 2000; freq -= 30) {
      ledcWriteTone(PINO_BUZZER, freq);
      delay(5);
    }
  }
}

// ==========================================
// TRANSMISSÃO HTTP (POST)
// ==========================================
void enviarDadosNuvem(float temperatura, float umidade, int valorFumaca, String nivel) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");

    // Construção do JSON
    String payloadJSON = "{";
    payloadJSON += "\"temperatura\":" + String(temperatura) + ",";
    payloadJSON += "\"umidade\":" + String(umidade) + ",";
    payloadJSON += "\"fumaca\":" + String(valorFumaca) + ",";
    payloadJSON += "\"nivel\":\"" + nivel + "\"";
    payloadJSON += "}";

    int httpResponseCode = http.POST(payloadJSON);

    Serial.print(">>> Enviando pacote JSON: ");
    Serial.println(payloadJSON);

    if (httpResponseCode > 0) {
      Serial.print(">>> Resposta do Servidor (HTTP): ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print(">>> Erro na requisição HTTP: ");
      Serial.println(httpResponseCode);
    }

    http.end();
  } else {
    Serial.println(">>> Erro: Wi-Fi desconectado. Reconectando...");
    WiFi.begin(ssid, password);
  }
}

// ==========================================
// SETUP
// ==========================================
void setup() {
  Serial.begin(9600);
  delay(2000);

  pinMode(PINO_DHT, INPUT_PULLUP);
  dht.begin();
  ledcAttach(PINO_BUZZER, FREQUENCIA, RESOLUCAO);

  Serial.print("Conectando ao Wi-Fi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi Conectado!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  Serial.println("Sistema iniciado. Aguardando aquecimento...");
  delay(2000);
}

// ==========================================
// LOOP
// ==========================================
void loop() {
  float umidade = dht.readHumidity();
  float temperatura = dht.readTemperature();
  int valorFumaca = analogRead(PINO_MQ2);
  bool fumacaDetectada = valorFumaca > LIMIAR_FUMACA;

  String nivel = "NORMAL";
  if (fumacaDetectada || temperatura > 40.0) {
    nivel = "PERIGO";
  } else if (temperatura > 35.0 || umidade < 30.0) {
    nivel = "ATENCAO";
  }

  // Atuação física do alarme
  if (nivel == "PERIGO") {
    alertaPerigo();
  } else if (nivel == "ATENCAO") {
    alertaAtencao();
  } else {
    alertaNormal();
  }

  // Motor de transmissão para a Nuvem
  unsigned long tempoAtual = millis();
  if (tempoAtual - ultimoEnvio >= intervaloEnvio) {
    ultimoEnvio = tempoAtual;

    Serial.println("=========================");
    if (isnan(umidade) || isnan(temperatura)) {
      Serial.println("DHT11: ERRO - sem leitura.");
    } else {
      Serial.print("Temperatura: ");
      Serial.print(temperatura);
      Serial.println(" C");
      Serial.print("Umidade:     ");
      Serial.print(umidade);
      Serial.println(" %");

      enviarDadosNuvem(temperatura, umidade, valorFumaca, nivel);
    }
    Serial.print("MQ-2 bruto:  ");
    Serial.println(valorFumaca);
    Serial.print("Nivel:       ");
    Serial.println(nivel);
    Serial.println("=========================");
  }

  delay(100); // Mantém a estabilidade da CPU do ESP32
}
