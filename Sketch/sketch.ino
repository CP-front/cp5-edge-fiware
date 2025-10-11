// --- BIBLIOTECAS ---
#include <WiFi.h>
#include <PubSubClient.h>
#include "DHTesp.h"
#include <string.h>

// --- CONFIGURAÇÃO DOS PINOS ---
const int DHT_PIN = 15;
const int LED_PIN = 2;
const int LDR_PIN = 34;
const int BUZZER_PIN = 4;
DHTesp dhtSensor;

// --- CONFIGURAÇÃO DE REDE E MQTT ---
const char* SSID = "FIAP-IOT";
const char* PASSWORD = "F!@p25.IOT";
const char* BROKER_MQTT = "20.81.162.205";
const int BROKER_PORT = 1883;
const char* ID_MQTT = "fiware_EDGE4";
const char* TOPIC_SUBSCRIBE = "/TEF/lampEDGE4/cmd";

// --- VARIÁVEIS GLOBAIS ---
WiFiClient espClient;
PubSubClient MQTT(espClient);

unsigned long lastPublishTime = 0;
const unsigned long publishInterval = 5000;

bool ledPiscando = false;
String tipoAlerta = "nenhum";
unsigned long previousLedMillis = 0;
unsigned long piscaIntervalo = 500;
int ledEstado = LOW;
unsigned int buzzerFreq = 1000; // Frequência do som do buzzer

// --- SETUP ---
void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  noTone(BUZZER_PIN); // Garante que o buzzer comece desligado

  dhtSensor.setup(DHT_PIN, DHTesp::DHT11);
  
  initWiFi();
  initMQTT();
}

// --- CALLBACK MQTT (AGORA SÓ RECEBE COMANDO "LED") ---
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  Serial.print("Comando recebido: ");
  Serial.println(msg);

  int at_pos = msg.indexOf('@');
  int bar_pos = msg.indexOf('|');

  if (at_pos == -1 || bar_pos == -1) return;

  String comando = msg.substring(at_pos + 1, bar_pos);
  String valor = msg.substring(bar_pos + 1);

  if (comando.equals("led")) {
    if (valor.equals("desligar")) {
      ledPiscando = false;
      tipoAlerta = "nenhum";
      digitalWrite(LED_PIN, LOW);
      noTone(BUZZER_PIN); // Desliga o buzzer ao parar o alerta
    } else {
      ledPiscando = true;
      if (valor.indexOf("temp") != -1) tipoAlerta = "temp";
      else if (valor.indexOf("umid") != -1) tipoAlerta = "umid";
      else if (valor.indexOf("lum") != -1) tipoAlerta = "lum";
    }
  }
}

// --- FUNÇÃO DE ALERTA (AGORA CONTROLA LED E BUZZER) ---
void handleAlerta() {
  if (ledPiscando) {
    // Define a velocidade do pisca e a frequência do som com base no tipo de alerta
    if (tipoAlerta.equals("temp")) {
      piscaIntervalo = 200;  // Rápido
      buzzerFreq = 1500;     // Som agudo
    } else if (tipoAlerta.equals("umid")) {
      piscaIntervalo = 500;  // Médio
      buzzerFreq = 1000;     // Som médio
    } else if (tipoAlerta.equals("lum")) {
      piscaIntervalo = 1000; // Lento
      buzzerFreq = 800;      // Som mais grave
    }

    unsigned long currentMillis = millis();
    if (currentMillis - previousLedMillis >= piscaIntervalo) {
      previousLedMillis = currentMillis;
      
      // Inverte o estado do LED
      ledEstado = (ledEstado == LOW) ? HIGH : LOW;
      digitalWrite(LED_PIN, ledEstado);
      
      // Sincroniza o buzzer com o LED
      if (ledEstado == HIGH) {
        tone(BUZZER_PIN, buzzerFreq); // Liga o som (sem duração)
      } else {
        noTone(BUZZER_PIN); // Desliga o som
      }
    }
  }
}

// --- FUNÇÕES DE CONEXÃO E PUBLICAÇÃO (sem alterações) ---
void publishSensorData() {
  TempAndHumidity data = dhtSensor.getTempAndHumidity();
  if (dhtSensor.getStatus() != 0) {
    Serial.println("Erro ao ler do sensor DHT!");
    return;
  }
  float humidity = data.humidity;
  float temperature = data.temperature;
  int sensorValue = analogRead(LDR_PIN);
  int luminosity = map(sensorValue, 4095, 0, 0, 100);

  char payload[100];
  sprintf(payload, "t|%.1f|h|%.1f|l|%d", temperature, humidity, luminosity);

  const char* TOPIC_PUBLISH_ATTRS = "/TEF/lampEDGE4/attrs";
  MQTT.publish(TOPIC_PUBLISH_ATTRS, payload);
  Serial.print("Dados publicados: ");
  Serial.println(payload);
}

void initWiFi() {
  delay(10);
  Serial.println("------ Conexão Wi-Fi ------");
  WiFi.begin(SSID, PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi conectado!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void initMQTT() {
  MQTT.setServer(BROKER_MQTT, BROKER_PORT);
  MQTT.setCallback(mqtt_callback);
}

void reconnectMQTT() {
  while (!MQTT.connected()) {
    Serial.print("* Tentando conectar ao Broker MQTT: ");
    Serial.println(BROKER_MQTT);
    if (MQTT.connect(ID_MQTT)) {
      Serial.println("Conectado com sucesso!");
      MQTT.subscribe(TOPIC_SUBSCRIBE);
      Serial.print("Subscrito em: ");
      Serial.println(TOPIC_SUBSCRIBE);
    } else {
      Serial.print("Falhou, rc=");
      Serial.print(MQTT.state());
      Serial.println(" Tentando novamente em 5 segundos...");
      delay(5000);
    }
  }
}

// --- LOOP PRINCIPAL ---
void loop() {
  if (WiFi.status() != WL_CONNECTED) initWiFi();
  if (!MQTT.connected()) reconnectMQTT();
  
  MQTT.loop();

  if (millis() - lastPublishTime >= publishInterval) {
    lastPublishTime = millis();
    publishSensorData();
  }

  handleAlerta();
}