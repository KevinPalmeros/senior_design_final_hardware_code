import network
import time
from wifi import *
 
def wifi_connect(SSID = wifi['ssid'], PASSWORD= wifi['password']):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
 
    wait = 10
    while wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        wait -= 1
        print('Connecting...')
        time.sleep(1)
 
    if wlan.status() != 3:
        raise RuntimeError('Wifi Connection Failed.')
    else:
        print('Wifi Connected.')