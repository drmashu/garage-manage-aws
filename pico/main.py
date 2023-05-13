"""
Garage-Manage Pico Controller
Raspberry Pi Pico W での距離センサー使用および、Web RPC構築
"""

import gc
from micropython import alloc_emergency_exception_buf, const
import math
from machine import Pin
import uasyncio as asyncio
import time
import ure

#import network_utils
from mqtt_as import MQTTClient, config
import consts
import secrets

DISTANCE_INTERVAL_SEC = const(10)
alloc_emergency_exception_buf(100)

gc.collect()

# 超音波センサー 発信
GPIO_HCSR_TRIG = Pin(14, Pin.OUT)
# 超音波センサー 受信
GPIO_HCSR_ECHO = Pin(15, Pin.IN)

# シャッター開 リレー操作
GPIO_RLY_OPEN = Pin(6, Pin.OUT)
# シャッター開 ボタン検知
GPIO_BTN_OPEN = Pin(7, Pin.IN, Pin.PULL_UP)
# シャッター閉 リレー操作
GPIO_RLY_CLOSE = Pin(8, Pin.OUT)
# シャッター閉 ボタン検知
GPIO_BTN_CLOSE = Pin(9, Pin.IN, Pin.PULL_UP)

STT_CLOSED = 0
STT_CLOSE = 1
STT_OPEN = 2
STT_OPENED = 3

shutter_state = 0;

# 照明 リレー操作
GPIO_RLY_LIGHT = Pin(10, Pin.OUT)
# 照明 ボタン検知
GPIO_BTN_LIGHT = Pin(11, Pin.IN, Pin.PULL_DOWN)

# 換気扇 リレー操作
GPIO_RLY_FAN = Pin(12, Pin.OUT)
# 換気扇 ボタン検知
GPIO_BTN_FAN = Pin(13, Pin.IN, Pin.PULL_DOWN)


# 照明 LED
GPIO_LED_LIGHT = Pin(16, Pin.OUT)
# 換気扇 LED
GPIO_LED_FAN = Pin(17, Pin.OUT)

gc.collect()

rp2.country(secrets.COUNTRY)

DEV_ID = '{:012x}'.format(int.from_bytes(machine.unique_id(), 'big'))
RE_TOPIC  = ure.compile(DEV_ID + '/(.+)')


def PushButton(Button):
    print('button on')
    Button.on()
    asyncio.sleep_ms(500)
    Button.off()

def PushOpenButton(pin):
    PushButton(GPIO_RLY_OPEN)

def PushCloseButton(pin):
    PushButton(GPIO_RLY_CLOSE)

BTN_LIGHT = const(0)
BTN_FAN = const(1)
toggle = [0, 0]
button = [GPIO_RLY_LIGHT, GPIO_RLY_FAN]

def SwButton(pin):
    print('Pin {0} {1}'.format(pin, 'on' if toggle[pin] == 1 else 'off'))
    button[pin].value(toggle[pin])

def ToggleButton(pin):
    toggle[pin] = 1 if toggle[pin] == 0 else 0 
    SwButton(pin)

def PushLightButton(pin):
    ToggleButton(BTN_LIGHT)

def PushFanButton(pin):
    ToggleButton(BTN_FAN)

GPIO_BTN_OPEN.irq(trigger=Pin.IRQ_RISING,  handler=PushOpenButton)
GPIO_BTN_CLOSE.irq(trigger=Pin.IRQ_RISING,  handler=PushCloseButton)

GPIO_BTN_LIGHT.irq(trigger=Pin.IRQ_RISING,  handler=PushLightButton)
GPIO_BTN_FAN.irq(trigger=Pin.IRQ_RISING,  handler=PushFanButton)

"""
距離計測
"""
async def read_distance():
    GPIO_HCSR_TRIG.low()
    time.sleep_us(2)
    GPIO_HCSR_TRIG.high()
    time.sleep_us(10)
    GPIO_HCSR_TRIG.low()
    signaloff = 0
    signalon = 0
    while GPIO_HCSR_ECHO.value() == 0:
        signaloff = time.ticks_us()
    while GPIO_HCSR_ECHO.value() == 1:
        signalon = time.ticks_us()
    timepassed = signalon - signaloff
    distance = math.floor((timepassed * 0.0343) / 2 * 10)
    return distance

"""
中央値取得
"""
def mid(list):
    newList = sorted(list)
    return math.floor((newList[4] + newList[5]) / 2)

"""
距離取得
"""
async def get_distance():
    list = []
    for i in range(1, 10):
        list.append(await read_distance())
    return mid(list)

current_distance = 0

"""
外部からのスイッチ操作処理
"""
def SwitchButton(pin, sw):
    toggle[pin] = sw
    SwButton(pin)

"""
MQTT向け証明書情報の取得
"""
def get_ssl_params():
    global DEV_ID

    keyfile = '/certs/' + DEV_ID + '.private.der'
    with open(keyfile, 'rb') as f:
        key = f.read()
    certfile = '/certs/' + DEV_ID + '.cert.der'
    with open(certfile, 'rb') as f:
        cert = f.read()    
    ssl_params = {'key': key, 'cert': cert, 'server_side': False}
    return ssl_params


"""
MQTT メッセージ受信コールバック
"""
async def mqcallback(topic, msg):
    global RE_TOPIC
    print('mqcallback : topic "{0}" msg "{1}"'.format(topic, msg))
    target = RE_TOPIC.match(topic).group(1)
    if  target == 'light':
        if msg == 'off':
            SwitchButton(BTN_LIGHT, 0)
        elif msg == 'on':
            SwitchButton(BTN_LIGHT, 1)
    elif target == 'fan':
        if msg == 'off':
            SwitchButton(BTN_FAN, 0)
        elif msg == 'on':
            SwitchButton(BTN_FAN, 1)
    elif target == 'shutter':
        if msg == 'up':
            PushOpenButton(0)
        elif msg == 'down':
            PushCloseButton(0)
        elif msg == 'getPosition':
            await client.publish(b'gm-serv/' + DEV_ID,
                             b'{"ShutterPosition":"%s"}' % current_distance)
    else:
        print('invalid messages.')

async def messages(client):  # Respond to incoming messages
    async for topic, msg, retained in client.queue:
        topic = str(topic, 'utf-8')
        msg = str(msg, 'utf-8')
        print((topic, msg, retained))
        await mqcallback(topic, msg)

async def up(client):  # Respond to connectivity being (re)established
    while True:
        await client.up.wait()  # Wait on an Event
        client.up.clear()
        await client.subscribe(DEV_ID + '/#', 1)

async def distance_loop(client):
    global current_distance
    print('start distance loop')
    while True:
        await asyncio.sleep(DISTANCE_INTERVAL_SEC)
        new_distance = await get_distance()
        print("new distance" , new_distance)
        if abs(current_distance - new_distance) > 100:
            current_distance = new_distance
            print('distance:', current_distance, 'mm')

            await client.publish(b'gm-serv/' + DEV_ID,
                             b'{"ShutterPosition":"%s"}' % current_distance)
    
async def main(client):
    await client.connect()
    
    up_task = asyncio.create_task(up(client))
    messages_task = asyncio.create_task(messages(client))
    distance_task = asyncio.create_task(distance_loop(client))

    await up_task
    await messages_task
    await distance_task

print('pico dev_id: {}'.format(DEV_ID))

config["client_id"] = DEV_ID
config["server"] = consts.MQ_URL
config["ssid"] = secrets.WIFI_SSID
config["wifi_pw"] = secrets.WIFI_PASSWORD
config["ssl"] = True
config["ssl_params"] = get_ssl_params()
config["keepalive"] = 7200
config["queue_len"] = 5

MQTTClient.DEBUG = True
client = MQTTClient(config);

try:
    asyncio.run(main(client))
finally:
    client.close()
