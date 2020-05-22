import time
import string
import random
import threading

from wisepaasdatahubedgesdk.EdgeAgent import EdgeAgent
import wisepaasdatahubedgesdk.Common.Constants as constant
from wisepaasdatahubedgesdk.Model.Edge import EdgeAgentOptions, MQTTOptions, DCCSOptions, EdgeData, EdgeTag, EdgeStatus, EdgeDeviceStatus, EdgeConfig, NodeConfig, DeviceConfig, AnalogTagConfig, DiscreteTagConfig, TextTagConfig
from wisepaasdatahubedgesdk.Common.Utils import RepeatedTimer
import math

class App():

    def __init__(self):
        self.edgeAgent = None
        self.timer = None

        self.count = 0

        # function
        def connect():
            edgeAgentOptions = EdgeAgentOptions(nodeId="04f2206c-a6d5-44d5-ae02-375fc29b8079")
            edgeAgentOptions.connectType = constant.ConnectType['DCCS']
            dccsOptions = DCCSOptions(apiUrl="https://api-dccs-ensaas.sa.wise-paas.com/", credentialKey="c7b005554b8d527a1fdf2137aea055l7")
            edgeAgentOptions.DCCS = dccsOptions

            if self.edgeAgent is None:
                self.edgeAgent = EdgeAgent(edgeAgentOptions)
                self.edgeAgent.on_connected = onConnected
                self.edgeAgent.on_disconnected = onDisconnected
                self.edgeAgent.on_message = onMessage

            self.edgeAgent.connect()

        def onConnected(edgeAgent, isConnected):
            if isConnected:
                print("connected")

        def onDisconnected(edgeAgent, isDisconnected):
            if isDisconnected:
                self.edgeAgent = None
                self.timer = None
                print("disconnected")

        def onMessage(edgeAgent, message):
            if message.type == constant.MessageType['ConfigAck']:
                response = 'Upload Config Result: {0}'.format(str(message.message.result))
            elif message.type == constant.MessageType['WriteValue']:
                message = message.message
                for device in message.deviceList:
                    print("deviceId: {0}".format(device.id))
                    for tag in device.tagList:
                        print("tagName: {0}, Value: {1}".format(tag.name, str(tag.value)))

        def generateConfig():
            config = EdgeConfig()
            nodeConfig = NodeConfig(nodeType=constant.EdgeType['Gateway'])
            config.node = nodeConfig

            deviceConfig = DeviceConfig(id='Device', name='Device', description='Device', deviceType='Smart Device', retentionPolicyName='')
            heartRateAnalogConfig = AnalogTagConfig(name='heart rate', description='heart rate', readOnly=False, arraySize=0, spanHigh=1000, spanLow=0, engineerUnit='', integerDisplayFormat=4, fractionDisplayFormat=0)
            fetalMovementAnalogConfig = AnalogTagConfig(name='fetal movement', description='fetal movement', readOnly=False, arraySize=0, spanHigh=1000, spanLow=0, engineerUnit='', integerDisplayFormat=4, fractionDisplayFormat=0)
            uterineContractionAnalogConfig = AnalogTagConfig(name='uterine contraction', description='uterine contraction', readOnly=False, arraySize=0, spanHigh=1000, spanLow=0, engineerUnit='', integerDisplayFormat=4, fractionDisplayFormat=0)
            fetalMovementButtonPressedAnalogConfig = AnalogTagConfig(name='fetal movement pressed', description='fetal movement pressed', readOnly=False, arraySize=0, spanHigh=1000, spanLow=0, engineerUnit='', integerDisplayFormat=4, fractionDisplayFormat=0)

            deviceConfig.analogTagList.append(heartRateAnalogConfig)
            deviceConfig.analogTagList.append(fetalMovementAnalogConfig)
            deviceConfig.analogTagList.append(uterineContractionAnalogConfig)
            deviceConfig.discreteTagList.append(fetalMovementButtonPressedAnalogConfig)
            config.node.deviceList.append(deviceConfig)

            return config

        def generateData():
            heartRate = 0
            edgeData = EdgeData()

            def genHeartRateData():
                value = 135 - 30 * pow(math.sin(0.003 * self.count), 8) \
                            + 20 * pow(math.sin(0.009 * self.count), 8) \
                            + 10 * pow(math.sin(0.018 * self.count), 14) \
                            - 10 * pow(math.sin(0.012 * self.count), 3) \
                            - 5 * pow(math.sin(0.049 * self.count), 3) \
                            + 2 * pow(math.sin(0.17 * self.count), 10) \
                            - 2 * pow(math.sin(0.11 * self.count), 11) \
                            + 2 * pow(math.sin(0.29 * self.count), 40) \
                            - 2 * pow(math.sin(0.42 * self.count), 60) \
                            + math.sin(0.5 * self.count) * math.sin(0.6 * self.count) * math.sin(0.9 * self.count) \
                            + 0.2 * math.sin(4 * self.count) * math.sin(7 * self.count) \
                            + 0.1 * math.sin(13 * self.count) * math.sin(15 * self.count)

                fetalStatus = value
                self.count += 0.6
                tag = EdgeTag('Device', 'heart rate', value)
                edgeData.tagList.append(tag)
                print("generate heart rate data : " + str(value))

            def genButtonPressedData():
                if chance <= probabilityToPressButton and heartRate > 160:
                    tag = EdgeTag('Device', 'fetal movement pressed', 100)
                    edgeData.tagList.append(tag)
                    print("generate button pressed data")

            genHeartRateData()
            # genButtonPressedData()

            return edgeData

        def sendData():
            data = generateData()
            self.edgeAgent.sendData(data)

        connect()

        _config = generateConfig()
        self.edgeAgent.uploadConfig(action=constant.ActionType['Create'], edgeConfig=_config)

        frequency = 0.1

        if self.timer is None:
            self.timer = RepeatedTimer(frequency, sendData)
            sendData()


main = App()
