"""
Garage-Manage Pico Controller
Raspberry Pi Pico W での距離センサー使用および、Web RPC構築
"""

import gc
from micropython import alloc_emergency_exception_buf, const
import math
from machine import ADC,Pin
import uasyncio as asyncio
import time
import ure
import ujson

from mqtt_as import MQTTClient, config
import consts
import secrets

alloc_emergency_exception_buf(100)

gc.collect()

# 距離計測間隔(秒)
DISTANCE_INTERVAL_SEC = const(10)
# メッセージ送信間隔(秒)
SENDMSG_INTERVAL_SEC = const(1)

# シャッター開 ボタン検知
GPIO_BTN_OPEN = Pin(2, Pin.IN, Pin.PULL_UP)
# シャッター開 リレー操作
GPIO_RLY_OPEN = Pin(3, Pin.OUT)
# シャッター閉 ボタン検知
GPIO_BTN_CLOSE = Pin(4, Pin.IN, Pin.PULL_UP)
# シャッター閉 リレー操作
GPIO_RLY_CLOSE = Pin(5, Pin.OUT)

# 照明 ボタン検知
GPIO_BTN_LIGHT = Pin(6, Pin.IN, Pin.PULL_DOWN)
# 照明 リレー操作
GPIO_RLY_LIGHT = Pin(7, Pin.OUT)
# 照明 LED
GPIO_LED_LIGHT = Pin(8, Pin.OUT)

# 換気扇 ボタン検知
GPIO_BTN_FAN = Pin(10, Pin.IN, Pin.PULL_DOWN)
# 換気扇 リレー操作
GPIO_RLY_FAN = Pin(11, Pin.OUT)
# 換気扇 LED
GPIO_LED_FAN = Pin(12, Pin.OUT)


# 超音波センサー 発信
GPIO_HCSR_TRIG = Pin(14, Pin.OUT)
# 超音波センサー 受信
GPIO_HCSR_ECHO = Pin(15, Pin.IN)

GPIO_HCSR_TRIG.value(0)

gc.collect()

rp2.country(secrets.COUNTRY)

# デバイスID
DEV_ID = '{:012x}'.format(int.from_bytes(machine.unique_id(), 'big'))
# トピック解析 正規表現
RE_TOPIC  = ure.compile(DEV_ID + '/(.+)')

#ステータス変化
status_changed = False

#シャッターステータス
shutter_state = 0;

# 閉じ完
STT_CLOSED = const(0)
# 閉じ中
STT_CLOSE = const(1)
# 開き中
STT_OPEN = const(2)
# 開き完
STT_OPENED = const(3)

# 電源ボタンステータス
BTN_LIGHT = const(0)
BTN_FAN = const(1)
# 電源ボタンステータス　配列
toggle = [0, 0]
# 電源ボタンGPIO　配列
button = [GPIO_RLY_LIGHT, GPIO_RLY_FAN]
# パイロットランプステータス　配列
toggle_pilot = [1, 0]
# パイロットランプボタンGPIO　配列
pilot = [GPIO_LED_LIGHT, GPIO_LED_FAN]

# 現状距離
current_distance = 0

"""
ガレージ状況 JSON 生成
"""
def getJsonGarageStatus():
    global current_distance
    global shutter_state
    global toggle
    return ujson.dumps({
            "ShutterPosition": current_distance,
            "ShutterState": shutter_state,
            "LightState": toggle[BTN_LIGHT],
            "FanState":  toggle[BTN_FAN]
        })

"""
シャッターボタン 押下処理
"""
def PushShutterButton(Button):
    Button.on()
    asyncio.sleep_ms(500)
    Button.off()

"""
シャッター 開ボタン押下処理
"""
def PushOpenButton(pin):
    print('button on {}'.format(pin))
    shutter_state = STT_OPEN
    PushShutterButton(GPIO_RLY_OPEN)

"""
シャッター 閉ボタン押下処理
"""
def PushCloseButton(pin):
    print('button on {}'.format(pin))
    shutter_state = STT_CLOSE
    PushShutterButton(GPIO_RLY_CLOSE)

"""
トグルボタン押下処理
"""
def PushToggleButton(pin):
    global status_changed
    toggle[pin] = 1 if toggle[pin] == 0 else 0 
    toggle_pilot[pin] = 1 if toggle_pilot[pin] == 0 else 0 
    print('Pin {0} {1}'.format(pin, 'on' if toggle[pin] == 1 else 'off'))
    button[pin].value(toggle[pin])
    pilot[pin].value(toggle_pilot[pin])
    status_changed = True

"""
照明ボタン押下処理
"""
def PushLightButton(pin):
    print('light button on {}'.format(pin))
    PushToggleButton(BTN_LIGHT)

"""
換気扇ボタン押下処理
"""
def PushFanButton(pin):
    print('fan button on {}'.format(pin))
    PushToggleButton(BTN_FAN)

"""
外部からのスイッチ操作処理
"""
def SwitchButton(pin, sw):
    if toggle[pin] != sw:
        PushToggleButton(pin)

GPIO_BTN_OPEN.irq(trigger=Pin.IRQ_RISING,  handler=PushOpenButton)
GPIO_BTN_CLOSE.irq(trigger=Pin.IRQ_RISING,  handler=PushCloseButton)

GPIO_BTN_LIGHT.irq(trigger=Pin.IRQ_RISING,  handler=PushLightButton)
GPIO_BTN_FAN.irq(trigger=Pin.IRQ_RISING,  handler=PushFanButton)

coeff = 3.3 / 65535

a = ADC(4)

"""
距離計測
"""
def read_distance():
     #Trigger pulse < 10us
     GPIO_HCSR_TRIG.value(1)
     time.sleep_us(2)
     GPIO_HCSR_TRIG.value(0)
    #反射時間の測定
     while GPIO_HCSR_ECHO.value()==0:
         signaloff = time.ticks_us()
     while GPIO_HCSR_ECHO.value()==1:
         signalon = time.ticks_us()
     timepassed = signalon - signaloff

    #気温の測定(pico内部の温度計を利用)
     v = a.read_u16() * coeff
     temp = round((34-(v-0.706)/0.001721),1)
    #距離の計算
     vs = 331.5 + 0.6 * temp #音速の計算
     distance = round((vs*timepassed/2000),1)
     
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
        list.append(read_distance())
    return mid(list)

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
            status_changed = True
    else:
        print('invalid messages.')

"""
メッセージ受信
"""
async def receiveMessages(client): 
    async for topic, msg, retained in client.queue:
        topic = str(topic, 'utf-8')
        msg = str(msg, 'utf-8')
        print((topic, msg, retained))
        await mqcallback(topic, msg)

"""
(再)接続時処理
"""
async def up(client):
    while True:
        await client.up.wait()  # Wait on an Event
        client.up.clear()
        await client.subscribe(DEV_ID + '/#', 1)

"""
距離計測
"""
async def distance_loop(client):
    global current_distance
    global status_changed
    print('start distance loop')
    while True:
        await asyncio.sleep(DISTANCE_INTERVAL_SEC)
        new_distance = await get_distance()
        print("new distance" , new_distance)
        if abs(current_distance - new_distance) > 100:
            current_distance = new_distance
            status_changed = True
            print('distance:', current_distance, 'mm')
        
"""
メッセージ送信
"""
async def sendMessage(client):
    global current_distance
    global status_changed
    print('start send loop')
    while True:
        await asyncio.sleep(SENDMSG_INTERVAL_SEC)
        if status_changed:
            status_changed = False
            msg = getJsonGarageStatus()
            print('send msg : {}'.format(msg))
            await client.publish(b'gm-serv/' + DEV_ID, msg)
    
"""
メイン処理
"""
async def main(client):
    await client.connect()
    
    await asyncio.gather(
        asyncio.create_task(up(client)),
        asyncio.create_task(receiveMessages(client)),
        asyncio.create_task(distance_loop(client)),
        asyncio.create_task(sendMessage(client)),
    )

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
