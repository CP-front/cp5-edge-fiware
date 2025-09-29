#include <WiFi.h>  // Include WiFi library for connecting to WiFi
#include <PubSubClient.h>  // Include PubSubClient library for MQTT
#include "DHTesp.h"  // Include DHTesp library for DHT sensor support

// Pin configuration
const int DHT_PIN = 15;  // Pin for DHT22 sensor
DHTesp dhtSensor;  // Create an instance of the DHT sensor

// WiFi and MQTT broker configuration
const char* SSID = "FIAP-IOT";  // WiFi SSID
const char* PASSWORD = "F!@p25.IOT";  // WiFi password (empty for open network)
const char* BROKER_MQTT = "20.81.162.205";  // MQTT broker IP address
const int BROKER_PORT = 1883;  // MQTT broker port
// MQTT topics for publishing and subscribing
const char* TOPIC_SUBSCRIBE = "/TEF/lampEDGE4/cmd";  // Command topic
const char* TOPIC_PUBLISH_1 = "/TEF/lampEDGE4/attrs";  // State topic
const char* TOPIC_PUBLISH_2 = "/TEF/lampEDGE4/attrs/l";  // Luminosity topic
const char* TOPIC_PUBLISH_3 = "/TEF/lampEDGE4/attrs/h";  // Humidity topic
const char* TOPIC_PUBLISH_4 = "/TEF/lampEDGE4/attrs/t";  // Temperature topic
const char* ID_MQTT = "fiware_EDGE4";  // MQTT client ID
const int D4 = 2;  // Pin for LED output

// Create instances for WiFi client and MQTT client
WiFiClient espClient;
PubSubClient MQTT(espClient);
char outputState = '0';  // Variable to track the output state (LED)

// Logging
unsigned long lastLogTime = 0;  // Timestamp of the last log message
const unsigned long logInterval = 2000;  // Interval between log messages in milliseconds

// Initialize Serial communication
void initSerial() {
    Serial.begin(115200);  // Start Serial communication at 115200 baud rate
}

// Initialize WiFi connection
void initWiFi() {
    delay(10);  // Delay for stability
    Serial.println("------Wi-Fi Connection------");  // Print WiFi connection message
    Serial.print("Connecting to network: ");  // Print connecting message
    Serial.println(SSID);  // Print the SSID
    reconnectWiFi();  // Attempt to reconnect to WiFi
}

// Initialize MQTT connection
void initMQTT() {
    MQTT.setServer(BROKER_MQTT, BROKER_PORT);  // Set the MQTT broker server and port
    MQTT.setCallback(mqtt_callback);  // Set the callback function for incoming messages
}

// Setup function runs once at the start
void setup() {
    initOutput();  // Initialize output pins
    initSerial();  // Initialize Serial communication
    dhtSensor.setup(DHT_PIN, DHTesp::DHT22);  // Setup DHT sensor
    initWiFi();  // Initialize WiFi connection
    initMQTT();  // Initialize MQTT connection
    MQTT.publish(TOPIC_PUBLISH_1, "s|on");  // Publish initial state to the MQTT broker
}

// Main loop runs repeatedly
void loop() {
    checkWiFiAndMQTTConnections();  // Check WiFi and MQTT connections
    sendOutputStateToMQTT();  // Send output state to the MQTT broker
    handleLuminosity();  // Handle luminosity sensor reading
    handleHumidity();  // Handle humidity sensor reading
    handleTemperature();  // Handle temperature sensor reading
    MQTT.loop();  // Process incoming messages
    delay(1000);  // Wait for 1 seconds before publishing next data


    // Handle logging at intervals
    if (millis() - lastLogTime >= logInterval) {
        lastLogTime = millis();  // Update the last log time
        logStatus();  // Log status at intervals
    }
}

// Function to log status
void logStatus() {
    // Read sensor data
    int luminosity = readLuminosity();
    float humidity = readHumidity();
    float temperature = readTemperature();
    
    // Log values
    Serial.print("Luminosity: ");
    Serial.print(luminosity);
    Serial.print(" | Humidity: ");
    Serial.print(humidity);
    Serial.print(" | Temperature: ");
    Serial.print(temperature);
    Serial.print(" | LED State: ");
    Serial.print(outputState == '1' ? "On" : "Off");
    Serial.print(" | Onboard LED State: ");
    Serial.println(digitalRead(D4) == HIGH ? "On" : "Off");
}

// Function to read luminosity
int readLuminosity() {
    const int potPin = 34;  // Pin for luminosity sensor
    int sensorValue = analogRead(potPin);  // Read the analog value from the sensor
    return map(sensorValue, 0, 4095, 0, 100);  // Map the value to a percentage (0-100)
}

// Function to read humidity
float readHumidity() {
    TempAndHumidity data = dhtSensor.getTempAndHumidity();  // Get temperature and humidity data from the sensor
    return data.humidity;  // Return humidity value
}

// Function to read temperature
float readTemperature() {
    TempAndHumidity data = dhtSensor.getTempAndHumidity();  // Get temperature and humidity data from the sensor
    return data.temperature;  // Return temperature value
}

// Function to reconnect to WiFi
void reconnectWiFi() {
    if (WiFi.status() == WL_CONNECTED) return;  // If already connected, return
    WiFi.begin(SSID, PASSWORD);  // Begin WiFi connection
    // Wait for connection
    while (WiFi.status() != WL_CONNECTED) {
        delay(100);  // Delay for stability
        Serial.print(".");  // Print dot to indicate connection attempt
    }
    // Print connection success message and IP address
    Serial.println("\nSuccessfully connected to the network");
    Serial.print(SSID);
    Serial.println(" Obtained IP: ");
    Serial.println(WiFi.localIP());
    digitalWrite(D4, LOW);  // Set LED pin LOW to indicate connection success
}

// Callback function for handling incoming MQTT messages
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
    String msg;  // Create a string for the incoming message
    // Construct the message from the payload
    for (int i = 0; i < length; i++) {
        msg += (char)payload[i];  // Append each byte to the message string
    }
    Serial.print("- Message received: ");  // Print received message
    Serial.println(msg);
    // Define command topics for turning the LED on/off
    String onTopic = String("lampEDGE4") + "@on|";
    String offTopic = String("lampEDGE4") + "@off|";
    // Check if the message is to turn the LED on
    if (msg.equals(onTopic)) {
        digitalWrite(D4, HIGH);  // Set LED pin HIGH
        outputState = '1';  // Update output state
    }
    // Check if the message is to turn the LED off
    if (msg.equals(offTopic)) {
        digitalWrite(D4, LOW);  // Set LED pin LOW
        outputState = '0';  // Update output state
    }
}

// Function to verify WiFi and MQTT connections
void checkWiFiAndMQTTConnections() {
    if (!MQTT.connected()) reconnectMQTT();  // Reconnect MQTT if not connected
    reconnectWiFi();  // Ensure WiFi connection
}

// Function to send output state to the MQTT broker
void sendOutputStateToMQTT() {
    if (outputState == '1') {
        MQTT.publish(TOPIC_PUBLISH_1, "s|on");  // Publish LED ON state
    }
    if (outputState == '0') {
        MQTT.publish(TOPIC_PUBLISH_1, "s|off");  // Publish LED OFF state
    }
}

// Function to initialize output pins
void initOutput() {
    pinMode(D4, OUTPUT);  // Set D4 as an output pin
    digitalWrite(D4, HIGH);  // Initially turn the LED OFF
    boolean toggle = false;  // Toggle variable for LED blinking
    // Blink the LED for initialization feedback
    for (int i = 0; i <= 10; i++) {
        toggle = !toggle;  // Toggle the state
        digitalWrite(D4, toggle);  // Set the LED state
        delay(200);  // Wait for 200 milliseconds
    }
}

// Function to reconnect to the MQTT broker
void reconnectMQTT() {
    while (!MQTT.connected()) {  // While not connected to MQTT
        Serial.print("* Attempting to connect to MQTT Broker: ");  // Print connection attempt message
        Serial.println(BROKER_MQTT);  // Print the broker IP address
        // Attempt to connect to the MQTT broker
        if (MQTT.connect(ID_MQTT)) {
            Serial.println("Successfully connected to the MQTT broker!");  // Print connection success message
            MQTT.subscribe(TOPIC_SUBSCRIBE);  // Subscribe to the command topic
        } else {
            Serial.println("Failed to reconnect to the broker.");  // Print connection failure message
            delay(2000);  // Wait before retrying
        }
    }
}

// Function to handle luminosity sensor readings
void handleLuminosity() {
    const int potPin = 34;  // Pin for luminosity sensor
    int sensorValue = analogRead(potPin);  // Read the analog value from the sensor
    int luminosity = map(sensorValue, 0, 4095, 0, 100);  // Map the value to a percentage (0-100)
    String message = String(luminosity);  // Create a string for the luminosity value
    MQTT.publish(TOPIC_PUBLISH_2, message.c_str());  // Publish the luminosity value to the MQTT broker
}

// Function to handle humidity sensor readings
void handleHumidity() {
    TempAndHumidity data = dhtSensor.getTempAndHumidity();  // Get temperature and humidity data from the sensor
    String message = String(data.humidity, 1) + "%";  // Create a string for the humidity value
    MQTT.publish(TOPIC_PUBLISH_3, message.c_str());  // Publish the humidity value to the MQTT broker
}

// Function to handle temperature sensor readings
void handleTemperature() {
    TempAndHumidity data = dhtSensor.getTempAndHumidity();  // Get temperature and humidity data from the sensor
    String message = String(data.temperature, 2) + "°C";  // Create a string for the temperature value
    MQTT.publish(TOPIC_PUBLISH_4, message.c_str());  // Publish the temperature value to the MQTT broker
}
