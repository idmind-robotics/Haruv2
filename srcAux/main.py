import time
import machine
from machine import Timer, SoftI2C
from machine import Pin, ADC

from src import imu
from src import gsm
from src import hw
import json

DEBUG_API="http://idmind-webdev-server.herokuapp.com/api/gps"

URL_BIKE_ID="http://idmind-webdev-server.herokuapp.com/api/bike_registry"

URL_BIKE_COMMANDS="http://idmind-webdev-server.herokuapp.com/api/command"

UDP_IP_URL = "http://hpovoa.pythonanywhere.com/surf_address"

hw = hw.HW()
hw.turnOff()
time.sleep(1)

print("DEBUG: Turning hardware on")
hw.turnOn()
print("DEBUG: Turning GSM on")
hw.turnOnGps()
hw.turnOffMotors()

modem=gsm.Modem(MODEM_TX_PIN=2, MODEM_RX_PIN=4)
modem.initialize()
hw.beep()
time.sleep(1)
modem.setupGSM()
hw.beep()
hw.beep()
response = modem.http_request(UDP_IP_URL, mode='GET', data=json.dumps({}))
ip = response.content
ip = ip.strip('\n')
bike_id = {}
CONTEXT = {
    "hw": hw,
    "modem": modem,
    "shutdown": False, 
    "turnon": False,
    "hasBikeUpdate":False,
    "apiInfo": {},
    "lastBikeSent": time.time(),
    "debug": False, 
    "reprogram": False,
    "msgTime" : 1,
    "bike": bike_id,
    "udp_ip": ip,
    "last_ip_request": time.time()
}
CONTEXT["modem"].updateUdpIp(CONTEXT["udp_ip"])
modem.setupUDP()

def hw_routine(t):
    CONTEXT["hw"].read()

def comm_routine(t):
    if time.time() - CONTEXT["last_ip_request"] > 3600:
        response = CONTEXT["modem"].http_request(UDP_IP_URL, mode='GET', data=json.dumps({}))
        ip = response.content
        ip = ip.strip('\n')
        if(ip != CONTEXT["udp_ip"]):
            CONTEXT["udp_ip"] = ip
            if(CONTEXT["udp_ip"] != ""):
                CONTEXT["modem"].updateUdpIp(CONTEXT["udp_ip"])
                CONTEXT["modem"].setupUDP()
    
    CONTEXT["modem"].getGpsStatus()
    CONTEXT["modem"].getGpsData()
    
    final = {}
    final = CONTEXT["bike"].copy()
    if CONTEXT["modem"].values["GPSFix"] == "Location not Fix":
        print("GPS not fix")
        CONTEXT["gpsFix"] = False
    else:
        CONTEXT["gpsFix"] = True
    
    final.update(CONTEXT["modem"].values)
    # final.update(CONTEXT["hw"].values)
    CONTEXT["lastBikeSent"] = time.time()
    # bike_commands = CONTEXT["modem"].http_request(URL_BIKE_API, mode='POST', data=json.dumps(final))
    # print("DEBUG: bike status -> {}".format(json.dumps(final)))
    start = time.ticks_ms()
    # bike_commands = CONTEXT["modem"].http_request(DEBUG_API, mode='POST', data=json.dumps(final))
    CONTEXT["modem"].sendToUDP(json.dumps(final))
    # print("DEBUG: time to acquire data {}".format(time.ticks_ms() - start))
    
hw_routine_timer = Timer(3)
hw_routine_timer.init(period=100, mode=Timer.PERIODIC, callback=hw_routine)

comm_routine_timer = Timer(1)
comm_routine_timer.init(period=50, mode=Timer.PERIODIC, callback=comm_routine)

while True:
    time.sleep(1.0)