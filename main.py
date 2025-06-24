import json, network, time
from umqtt.simple import MQTTClient
from machine import SoftI2C, Pin
from aht10 import AHT10
from ota import OTAUpdater

#Versionsänderung_V2
#Die Version wurde angepasst
# Konfiguration
WIFI_SSID = 'BZTG-IoT'
WIFI_PASSWORD = 'WerderBremen24'
MQTT_BROKER = '192.168.1.145'
MQTT_PORT = 1883
MQTT_TOPIC = b'BZTG/Ehnern/E101'
CLIENT_ID = b'ESP32 S3 Jerrit'
I2C_SCL_PIN = 8
I2C_SDA_PIN = 3
FIRMWARE_URL = "https://raw.githubusercontent.com/jerrit151/206_OTA/"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Verbinde mit WiFi...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(20):
            if wlan.isconnected():
                break
            time.sleep(1)
    if wlan.isconnected():
        print('WiFi verbunden. IP:', wlan.ifconfig()[0])
        return wlan
    else:
        print('WiFi-Verbindung fehlgeschlagen!')
        return None

def disconnect_wifi(wlan):
    if wlan:
        wlan.disconnect()
        wlan.active(False)
        print('WiFi getrennt.')

def connect_mqtt():
    client = None
    try:
        client = MQTTClient(CLIENT_ID, MQTT_BROKER, MQTT_PORT)
        client.connect()
        print('MQTT Broker verbunden')
        return client
    except Exception as e:
        print('Fehler beim MQTT-Connect:', e)
        return None

def send_json(client, json_data):
    try:
        message = json.dumps(json_data)
        client.publish(MQTT_TOPIC, message)
        print(f'Gesendet: {message} an Thema: {MQTT_TOPIC}')
        return True
    except Exception as e:
        print('Fehler beim Senden:', e)
        return False

def init_sensors():
    i2c = SoftI2C(scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=100000)
    return AHT10(i2c)

def read_sensors(sensor):
    try:
        temp = sensor.temperature()
        hum = sensor.humidity()
        return temp, hum
    except Exception as e:
        print('Fehler beim Sensor-Lesen:', e)
        return None, None

def mittelwert(liste, new_value):
    if len(liste) == 10:
        liste.pop(0)
    liste.append(new_value)
    calc_list = sorted(liste)[1:-1] if len(liste) >= 3 else liste
    return sum(calc_list) / len(calc_list), liste

def main():
    # WLAN für OTA verbinden
    wlan_ota = connect_wifi()
    if wlan_ota:
        # OTA-Update prüfen
        ota_updater = OTAUpdater(WIFI_SSID, WIFI_PASSWORD, FIRMWARE_URL, "main.py")
        ota_updater.download_and_install_update_if_available()
        disconnect_wifi(wlan_ota)
    
    # Hauptprogramm
    sensor = init_sensors()
    temp_list, hum_list = [], []
    
    while True:
        temp, hum = read_sensors(sensor)
        if temp is not None and hum is not None:
            temp_avg, temp_list = mittelwert(temp_list, temp)
            hum_avg, hum_list = mittelwert(hum_list, hum)
            json_data = {
                "Temperatur": round(temp_avg),
                "Luftfeuchtigkeit": round(hum_avg)
            }
            print('Messwerte:', json_data)
            
            wlan = connect_wifi()
            if wlan:
                client = connect_mqtt()
                if client:
                    if send_json(client, json_data):
                        print('Daten erfolgreich gesendet.')
                    else:
                        print('Senden fehlgeschlagen.')
                    time.sleep(0.5)
                    client.disconnect()
                disconnect_wifi(wlan)
            else:
                print('Keine WLAN-Verbindung, überspringe Senden.')
        else:
            print('Fehler beim Sensor-Lesen, überspringe Senden.')
        time.sleep(15)

main()
