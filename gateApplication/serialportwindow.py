# 导入模块
import sys
import time
import datetime
from threading import Timer, Thread
from PyQt5.QtWidgets import QMainWindow, QApplication
import serial
from mainWindow import Ui_MainWindow
import serial.tools.list_ports

import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTTv311
import struct
import json
import base64
import hmac
import time
from urllib.parse import quote
# from main import SharedVariables
import json

import mythread  # 自定义模块


# 定义串口类和设定程序框架
class SerialPortWindow(QMainWindow, Ui_MainWindow):
    # 定义构造函数
    def __init__(self, parent=None):
        super(SerialPortWindow, self).__init__(parent)
        self.setupUi(self)

        # 定义成员变量
        # 串口通信部分
        ser = None
        readLux_tread = None  # 读取串口线程

        # mqtt通信部分
        self.ServerUrl = "mqtts.heclouds.com"  # 服务器url
        self.ServerPort = 1883  # 服务器端口
        self.DeviceName = "gate"  # 设备ID
        self.Productid = "7v08xAeKs5"  # 产品ID
        self.accesskey = "TzVoTjVmUEdnMkVvMGIxWERUa1h2U2pTVjV4VG51V3k="

        # 发布的topic
        self.led = 'true'
        self.wendu = '0'
        self.Pub_topic1 = "$sys/" + self.Productid + "/" + self.DeviceName + "/thing/property/post"

        # 需要订阅的topic
        # 数据上传成功的消息
        self.Sub_topic1 = "$sys/" + self.Productid + "/" + self.DeviceName + "/thing/property/set"
        # 接收属性设置的消息
        self.Sub_topic2 = "$sys/" + self.Productid + "/" + self.DeviceName + "/thing/property/post/reply"
        # 测试用json数据格式

        self.json_close_led = '{"id":"123","version":"1.0","params":{ "kaiguan":{"value":false}}}'
        self.json_open_led = '{"id":"123","version":"1.0","params":{ "kaiguan":{"value":true}}}'
        self.json_wendu1 = '{"id":"123","version":"1.0","params":{ "wendu":{"value":88}}}'#+self.wendu+
        self.json_wendu2 = '{"id":"123","version":"1.0","params":{ "wendu":{"value":66}}}'
        # self.json_wendu = f'{{"id":"123","version":"1.0","params":{{"wendu":{{"value":"{self.wendu}"}}}}}}'


        # print(self.json_wendu) #

        self.passw = self.get_token(self.DeviceName, self.accesskey)
        print(self.passw)
        self.mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, self.DeviceName)
        self.mqttc.on_connect = self.on_connect
        self.mqttc.on_disconnect = self.on_disconnect
        self.mqttc.on_message = self.on_message
        self.mqttc.on_subscribe = self.on_subscribe
        self.mqttc.on_unsubscribe = self.on_unsubscribe

        # client = mqtt.Client(DeviceName,protocol=MQTTv311)
        # client.tls_set(certfile='/Users/mryu/PycharmProjects/MyProject/onenet/MQTTS-certificate.pem') #鉴权证书
        self.mqttc.username_pw_set(self.Productid, self.passw)

        ports_list = list(serial.tools.list_ports.comports())
        self.comboBox.clear()
        if len(ports_list) <= 0:
            self.comboBox.addItem("未发现串口设备", 0)
        else:
            for comport in ports_list:
                self.comboBox.addItem(comport[0], comport[1])

        # 绑定按钮单击事件处理函数（槽函数）
        self.detectButton.clicked.connect(self.detect_button_click)
        self.startButton.clicked.connect(self.start_button_click)
        self.stopButton.clicked.connect(self.stop_button_click)
        self.openLedButton.clicked.connect(self.open_led_button_click)
        self.closeLedButton.clicked.connect(self.close_led_button_click)

        # 初始化按钮的初始状态
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.openLedButton.setEnabled(False)
        self.closeLedButton.setEnabled(False)
        self.guangzhaoValueLabel.setText("----")
        self.wenduValueLabel.setText("----")
        self.shiduValueLabel.setText("----")
        # 设置窗体标题
        # self.setWindowTitle("智能家居系统")

    # 定义各个事件处理函数，注意函数名称与构造方法里面绑定的事件处理函数名称一致
    # 定义检测设备按钮事件处理函数
    def detect_button_click(self):
        self.ports_list = list(serial.tools.list_ports.comports())
        self.comboBox.clear()
        if len(self.ports_list) <= 0:
            self.comboBox.addItem("未发现串口设备", 0)
        else:
            for self.comport in self.ports_list:
                self.comboBox.addItem(self.comport[0], self.comport[1])

    # 定义开启系统按钮事情处理函数
    def start_button_click(self):
        cur_comport = self.comboBox.currentText()
        # https: // blog.csdn.net / bryanwang_3099 / article / details / 120493736
        '''
        timeout - 读超时时间，可取值为None, 0 或者其他具体数值（支持小数）。当设置为None
        时，表示阻塞式读取，一直读到期望的所有数据才返回；当设置为0 时，表示非阻塞式读取，无论读取到多少数据都立即返回；
        当设置为其他数值时，表示设置具体的超时时间（以秒为单位），如果在该时间内没有读取到所有数据，则直接返回。
        write_timeout: 写超时时间，可取值为 None, 0 或者其他具体数值（支持小数）。参数值起到的效果参考timeout   参数。       '''

        try:
            self.ser = serial.Serial(cur_comport, baudrate=57600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                                     stopbits=serial.STOPBITS_TWO, timeout=500)

            self.mqttc.connect(self.ServerUrl, port=self.ServerPort, keepalive=120)
            self.mqttc.loop_start()
            self.mqttc.subscribe(self.Sub_topic1)
            self.mqttc.subscribe(self.Sub_topic2)

        except serial.SerialException:
            self.comLabel.setText("开启系统失败，请检查设备是否正确连接...")
            self.stopButton.setEnabled(False)
            self.startButton.setEnabled(True)
            self.openLedButton.setEnabled(False)
            self.closeLedButton.setEnabled(False)
            return

        finally:
            print("启动系统")

        if self.ser.isOpen():
            self.comLabel.setText("系统已开启")
            self.stopButton.setEnabled(True)
            self.startButton.setEnabled(False)
            self.openLedButton.setEnabled(True)

            #  启动读取串口的线程
            self.readSensor_thread = Thread(target=self.readSensorData)
            self.readSensor_thread.start()

        self.sendLabel.setText("--------")
        self.receiveLabel.setText("--------")


    # 定义关闭系统按钮事情处理函数
    def stop_button_click(self):
        # 停止接收串口数据的线程
        mythread.stop_thread(self.readSensor_thread)

        # 关闭串口
        self.ser.close()
        # 断开云端连接
        self.mqttc.unsubscribe(self.Sub_topic1)
        self.mqttc.unsubscribe(self.Sub_topic2)
        self.mqttc.loop_stop()
        self.mqttc.disconnect()
        # 复位各个按钮
        self.stopButton.setEnabled(False)
        self.startButton.setEnabled(True)
        self.openLedButton.setEnabled(False)
        self.closeLedButton.setEnabled(False)

        self.guangzhaoLabel.setText("----")
        self.wenduValueLabel.setText("----")
        self.shiduValueLabel.setText("----")
        self.comLabel.setText("系统已关闭")
        self.sendLabel.setText("--------")
        self.receiveLabel.setText("--------")

    # 定义开灯按钮事情处理函数
    def open_led_button_click(self):
        num = 3  # 最多发送次数
        while num > 0:
            write_len = self.ser.write("0:1".encode('utf-8'))
            if write_len == len("0:1"):
                self.sendLabel.setText("发送：开灯指令（0:1）")
                self.openLedButton.setEnabled(False)
                self.closeLedButton.setEnabled(True)
                self.mqttc.publish(self.Pub_topic1, self.json_open_led, qos=0)
                break
            else:
                num -= 1


        else:
            self.comLabel.setText("无法发出开灯指令，请检查设备线路是否正确连接")

    # 定义关灯按钮事情处理函数
    def close_led_button_click(self):
        num = 3  # 最多发送次数
        while num > 0:
            write_len = self.ser.write("0:0".encode('utf-8'))
            if write_len == len("0:0"):
                self.sendLabel.setText("发送：关灯指令（0:0）")
                self.openLedButton.setEnabled(True)
                self.closeLedButton.setEnabled(False)
                self.mqttc.publish(self.Pub_topic1, self.json_close_led, qos=0)
                break
            else:
                num -= 1


        else:
            self.comLabel.setText("无法发出关灯指令，请检查设备线路是否正确连接")

    # 定义周期性读取并显示传感器数据函数
    def readSensorData(self):
        while True:
            data = self.ser.read_all()
            text = data.decode(encoding="utf-8").strip()
            if text:
                current_time = datetime.datetime.now()
                self.receiveLabel.setText(str(current_time) + "收到： " + text)
                
                # 解析传感器数据
                if len(text) >= 3:
                    # 光照度数据格式：3:xxx
                    if text[0] == '3':
                        guangzhao = text[2:]
                          self.guangzhaoValueLabel.setText(guangzhao)
                        self.json_guangzhao = f'{{"id":"123","version":"1.0","params":{{"guangzhao":{{"value":{guangzhao}}}}}}}'
                        self.mqttc.publish(self.Pub_topic1, self.json_guangzhao, qos=0)
                    # 温度数据格式：4:xxx
                    elif text[0] == '4':
                        wendu = text[2:]
                        self.wenduValueLabel.setText(wendu)
                        self.json_wendu = f'{{"id":"123","version":"1.0","params":{{"wendu":{{"value":{wendu}}}}}}}'
                        self.mqttc.publish(self.Pub_topic1, self.json_wendu, qos=0)
                    # 湿度数据格式：5:xxx
                    elif text[0] == '5':
                        shidu = text[2:]
                        self.shiduValueLabel.setText(shidu)
                        self.json_shidu = f'{{"id":"123","version":"1.0","params":{{"shidu":{{"value":{shidu}}}}}}}'
                        self.mqttc.publish(self.Pub_topic1, self.json_shidu, qos=0)

    # 认证token生成函数
    def get_token(self, id, access_key):
        version = '2018-10-31'
        #   res = 'products/%s' % id  # 通过产品ID访问产品API
        # res = 'userid/%s' % id  # 通过产品ID访问产品API
        res = "products/" + self.Productid + "/devices/" + self.DeviceName
        # 用户自定义token过期时间
        et = str(int(time.time()) + 36000000)
        # et = str(int(1722499200))
        # 签名方法，支持md5、sha1、sha256
        method = 'sha1'
        method1 = 'sha256'
        # 对access_key进行decode
        key = base64.b64decode(access_key)

        # 计算sign
        org = et + '\n' + method + '\n' + res + '\n' + version
        sign_b = hmac.new(key=key, msg=org.encode(), digestmod=method)
        sign = base64.b64encode(sign_b.digest()).decode()

        # value 部分进行url编码，method/res/version值较为简单无需编码
        sign = quote(sign, safe='')
        res = quote(res, safe='')

        # token参数拼接
        token = 'version=%s&res=%s&et=%s&method=%s&sign=%s' % (version, res, et, method, sign)

        return token


    def on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        # Since we subscribed only for a single channel, reason_code_list contains
        # a single entry
        # print("userdata:",reason_code_list)
        if reason_code_list[0].is_failure:
            print(f"on_subcribe:Broker rejected you subscription: {reason_code_list[0]}")
        else:
            print(f"on_subcribe:Broker granted the following QoS: {reason_code_list[0].value}")


    def on_unsubscribe(self, client, userdata, mid, reason_code_list, properties):
        # Be careful, the reason_code_list is only present in MQTTv5.
        # In MQTTv3 it will always be empty
        if len(reason_code_list) == 0 or not reason_code_list[0].is_failure:
            print("unsubscribe succeeded (if SUBACK is received in MQTTv3 it success)")
        else:
            print(f"Broker replied with failure: {reason_code_list[0]}")
        client.disconnect()


    # 当客户端收到来自服务器的CONNACK响应时的回调。也就是申请连接，服务器返回结果是否成功等
    def on_connect(self,client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"on_connect: Failed to connect: {reason_code}. loop_forever() will retry connection")
        else:
            # we should always subscribe from on_connect callback to be sure
            # our subscribed is persisted across reconnections.
            # client.subscribe("$SYS/#")
            print("on_connect:" + mqtt.connack_string(reason_code))
            # 连接成功后就订阅topic
            client.subscribe(self.Sub_topic1)
            client.subscribe(self.Sub_topic2)


    def on_disconnect( self, client, userdata, disconnect_flags, rc, properties):
        if rc != 0:
            print(f"Unexpected disconnection. Reason code: {rc}")
        else:
            print("Disconnected cleanly")

    # 从服务器接收发布消息时的回调。
    def on_message(self, client, userdata, message):
        print("on_message:")
        try:
            # 解码消息内容
            msg_payload = message.payload.decode('utf-8')
            # 打印原始有效负载
            print("----- 收到消息 -----")
            print(f"话题: {message.topic}")
            print(f"有效负载: {msg_payload}")

            # 尝试解析为 JSON 数据
            try:
                data = json.loads(msg_payload)
                # print("data:",data)
                params_data = data.get("params", {})
                # 打印 dp 数据的内容
                if not params_data:
                    print("dp 数据为空或不存在")
                else:
                    for key, value in params_data.items():
                        print(f"{key}: {value}")
                        if key=="kaiguan" and value==True:
                            num = 3  # 最多发送次数
                            while num > 0:
                                write_len = self.ser.write("0:1".encode('utf-8'))
                                if write_len == len("0:1"):
                                    self.sendLabel.setText("发送：开灯指令（0:1）")
                                    self.openLedButton.setEnabled(False)
                                    self.closeLedButton.setEnabled(True)
                                    self.mqttc.publish(self.Pub_topic1, self.json_open_led, qos=0)
                                    break
                                else:
                                    num -= 1
                            else:
                                self.comLabel.setText("无法发出开灯指令，请检查设备线路是否正确连接")
                        elif key=="kaiguan" and value==False:
                            num = 3  # 最多发送次数
                            while num > 0:
                                write_len = self.ser.write("0:0".encode('utf-8'))
                                if write_len == len("0:0"):
                                    self.sendLabel.setText("发送：关灯指令（0:0）")
                                    self.openLedButton.setEnabled(True)
                                    self.closeLedButton.setEnabled(False)
                                    self.mqttc.publish(self.Pub_topic1, self.json_close_led, qos=0)
                                    break
                                else:
                                    num -= 1
                            else:
                                self.comLabel.setText("无法发出关灯指令，请检查设备线路是否正确连接")


            except json.JSONDecodeError:
                print("无法解析 JSON 数据")

            print("--------------------")

        except Exception as e:
            print(f"处理消息时发生错误: {e}")

    # 当消息已经被发送给中间人，on_publish()回调将会被触发
    def on_publish(self, client, userdata, mid):
        print("on_publish:")
        print(str(mid))



# 定义main()函数
# 注：函数和类的定义之间间隔2行，这是PEP8推荐格式
def main():
    app = QApplication(sys.argv)
    serialWindow = SerialPortWindow()
    serialWindow.show()
    app.exec_()

#判定执行代码是否在主模块中，如果是则调用main()函数
if __name__ == '__main__':
    main()