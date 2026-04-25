#include <WiFi.h>

#define MQTT_MAX_PACKET_SIZE 2048 

#include <PubSubClient.h> // For MQTT communication

const char* ssid = "Sharvin";         // <<< Your Hotspot SSID >>>
const char* password = "12345678"; // <<< Your Hotspot Password >>>

const char* mqtt_broker = "broker.hivemq.com";
const int mqtt_port = 1883;

const char* mqtt_topic_subscribe = "sharvin_gestures/landmarks";
const char* mqtt_topic_publish = "sharvin_gestures/data_for_phone";

WiFiClient espClient;
PubSubClient mqttClient(espClient);

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
    Serial.print("Message arrived [");
    Serial.print(topic);
    Serial.print("]... ");
    Serial.print(length); // Print the length of the payload
    Serial.println(" bytes.");

    if (strcmp(topic, mqtt_topic_subscribe) == 0) {
        
        Serial.print("Relaying data to ");
        Serial.println(mqtt_topic_publish);
        
        mqttClient.publish(mqtt_topic_publish, payload, length);
    }
}

void mqtt_reconnect() {
    while (!mqttClient.connected()) {
        Serial.print("Attempting MQTT connection...");
        String clientId = "ESP32-Relay-";
        clientId += String(random(0xffff), HEX);
        
        if (mqttClient.connect(clientId.c_str())) {
            Serial.println("connected!");
            mqttClient.subscribe(mqtt_topic_subscribe);
            Serial.print("Subscribed to: ");
            Serial.println(mqtt_topic_subscribe);
        } else {
            Serial.print("failed, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" try again in 5 seconds");
            delay(5000); 
        }
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();
    Serial.println("WiFi connected!");
    Serial.print("ESP32 IP Address: ");
    Serial.println(WiFi.localIP());

    mqttClient.setServer(mqtt_broker, mqtt_port);
    mqttClient.setCallback(mqtt_callback); 

    mqttClient.setBufferSize(2048); 
}

void loop() {
    if (!mqttClient.connected()) {
        mqtt_reconnect(); 
    }
    mqttClient.loop(); 
}

