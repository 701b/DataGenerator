import time
import string
import random
import threading

from wisepaasdatahubedgesdk.EdgeAgent import EdgeAgent
import wisepaasdatahubedgesdk.Common.Constants as constant
from wisepaasdatahubedgesdk.Model.Edge import EdgeAgentOptions, MQTTOptions, DCCSOptions, EdgeData, EdgeTag, EdgeStatus, EdgeDeviceStatus, EdgeConfig, NodeConfig, DeviceConfig, AnalogTagConfig, DiscreteTagConfig, TextTagConfig
from wisepaasdatahubedgesdk.Common.Utils import RepeatedTimer


class App():

    def __init__(self):
        self.edgeAgent = None
        self.timer = None

        # 태아의 상태별 속성값
        upDownMaxVariation = 15

        # 정상 상태
        normalHeartRateStandard = random.randint(130, 140)  # 태아의 심박수 기준 (130 ~ 140)에서 랜덤
        normalHeartRateDeviation = 30  # 태아가 정상 상태일 때 심박수 편차
        normalHeartRateMaxVariance = 3  # 태아가 정상 상태일 때 초당 심박수 최대 변화량
        probabilityToNormalStatus = 70  # 태아가 정상 상태로 돌아올 확률 (value / 10000)
        probabilityToUpDown = 1000  #

        # 심박수 불규칙 상태
        irregularHeartRateDeviation = 40  # 태아의 심박수가 불규칙적일 때 심박수 편차
        irregularHeartRateMaxVariance = 15  # 태아의 심박수가 불규칙적일 때 초당 심박수 최대 변화량
        probabilityToIrregularHeartRateStatus = 2  # 태아의 심박수가 불규칙적으로 변하게 될 확률 (value / 10000)

        # 높은 심박수 상태
        highHeartRateIncrease = 20  # 태아의 심박수가 높은 상태일 때 심박수 기준 상승치
        highHeartRateDeviation = 35  # 태아의 심박수가 높은 상태일 때 심박수 편차
        highHeartRateMaxVariance = 8  # 태아의 심박수가 높은 상태일 때 초당 심박수 최대 변화량
        probabilityToHighHeartRateStatus = 1  # 태아의 심박수가 높은 상태로 변하게 될 확률 (value / 1000)

        probabilityToPressButton = 220  # 태아의 심박수가 높은 상태일 때 임산부가 버튼을 누를 확률 (value / 10000)

        # 낮은 심박수 상태
        lowHeartRateDecrease = 20  # 태아의 심박수가 낮은 상태일 때 심박수 기준 하락치
        lowHeartRateDeviation = 20  # 태아의 심박수가 낮은 상태일 때 심박수 편차
        lowHeartRateMaxVariance = 2  # 태아의 심박수가 낮은 상태일 때 초당 심박수 최대 변화량
        probabilityToLowHeartRateStatus = 1  # 태아의 심박수가 낮은 상태로 변하게 될 확률 (value / 10000)



        # 상태 변화까지 최소 카운트
        minCountUntilStatusVariation = 600

        # 현재 수치
        self.fetalStatus = 'normal'
        self.heartRate = normalHeartRateStandard
        self.count = 0
        self.upDown = 0

        print("normal heart rate standard : " + str(normalHeartRateStandard))

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
            edgeData = EdgeData()
            chance = random.randint(1, 10000)

            self.count += 1

            if self.count >= minCountUntilStatusVariation:
                if self.fetalStatus == 'normal':  # 태아가 정상 상태일 때
                    if chance <= probabilityToIrregularHeartRateStatus:
                        self.fetalStatus = 'irregular heart rate'
                        self.count = 0

                    elif self.heartRate > normalHeartRateStandard:  # 태아의 심박수가 높은 편일 때
                        if 100 < chance <= probabilityToHighHeartRateStatus + 100:
                            self.fetalStatus = 'high heart rate'
                            self.count = 0

                    elif self.heartRate < normalHeartRateStandard:  # 태아의 심박수가 낮은 편일 때
                        if 200 < chance <= probabilityToLowHeartRateStatus + 200:
                            self.fetalStatus = 'low heart rate'
                            self.count = 0

                else:  # 태아가 정상 상태가 아닐 때
                    if chance <= probabilityToNormalStatus:
                        if self.fetalStatus == 'irregular heart rate':  # 불규칙 상태에서 정상으로 돌아올 때 바로 정상 수치 주변으로 돌아오도록 함
                            self.heartRate = normalHeartRateStandard + random.randint(-normalHeartRateDeviation, normalHeartRateDeviation)

                        self.fetalStatus = 'normal'
                        self.count = 0

            chance = random.randint(1, 10000)

            if chance <= probabilityToUpDown:
                self.upDown = random.randint(-upDownMaxVariation, upDownMaxVariation)

            def genHeartRateData():
                if self.fetalStatus == 'normal':
                    if normalHeartRateStandard + self.upDown + normalHeartRateDeviation >= self.heartRate >= normalHeartRateStandard + self.upDown - normalHeartRateDeviation:
                        if normalHeartRateStandard + self.upDown < self.heartRate:
                            self.heartRate += random.randint(-normalHeartRateMaxVariance, int(normalHeartRateMaxVariance / 2))
                        else:
                            self.heartRate += random.randint(int(-normalHeartRateMaxVariance / 2), normalHeartRateMaxVariance)

                    elif self.heartRate > normalHeartRateStandard + self.upDown + normalHeartRateDeviation:
                        self.heartRate -= random.randint(int(-normalHeartRateMaxVariance / 2), normalHeartRateMaxVariance)

                    else:
                        self.heartRate += random.randint(int(-normalHeartRateMaxVariance / 2), normalHeartRateMaxVariance)

                elif self.fetalStatus == 'irregular heart rate':
                    if normalHeartRateStandard + self.upDown + irregularHeartRateDeviation >= self.heartRate >= normalHeartRateStandard + self.upDown - irregularHeartRateDeviation:
                        if normalHeartRateStandard + self.upDown < self.heartRate:
                            self.heartRate += random.randint(-irregularHeartRateMaxVariance, int(irregularHeartRateMaxVariance / 2))
                        else:
                            self.heartRate += random.randint(int(-irregularHeartRateMaxVariance / 2), irregularHeartRateMaxVariance)

                    elif self.heartRate > normalHeartRateStandard + self.upDown + irregularHeartRateDeviation:
                        self.heartRate -= random.randint(0, irregularHeartRateMaxVariance)

                    else:
                        self.heartRate += random.randint(0, irregularHeartRateMaxVariance)

                elif self.fetalStatus == 'high heart rate':
                    if normalHeartRateStandard + self.upDown + highHeartRateIncrease + highHeartRateDeviation >= self.heartRate >= normalHeartRateStandard + self.upDown + highHeartRateIncrease - highHeartRateDeviation:
                        if normalHeartRateStandard + self.upDown + highHeartRateIncrease < self.heartRate:
                            self.heartRate += random.randint(-highHeartRateMaxVariance, int(highHeartRateMaxVariance / 2))
                        else:
                            self.heartRate += random.randint(int(-highHeartRateMaxVariance / 2), highHeartRateMaxVariance)

                    elif self.heartRate > normalHeartRateStandard + self.upDown + highHeartRateIncrease + highHeartRateDeviation:
                        self.heartRate -= random.randint(0, highHeartRateMaxVariance)

                    else:
                        self.heartRate += random.randint(0, highHeartRateMaxVariance)

                elif self.fetalStatus == 'low heart rate':
                    if normalHeartRateStandard + self.upDown - lowHeartRateDecrease + lowHeartRateDeviation >= self.heartRate >= normalHeartRateStandard + self.upDown - lowHeartRateDecrease - lowHeartRateDeviation:
                        if normalHeartRateStandard + self.upDown - lowHeartRateDecrease < self.heartRate:
                            self.heartRate += random.randint(-lowHeartRateMaxVariance, int(lowHeartRateMaxVariance / 2))
                        else:
                            self.heartRate += random.randint(int(-lowHeartRateMaxVariance / 2), lowHeartRateMaxVariance)

                    elif self.heartRate > normalHeartRateStandard + self.upDown - lowHeartRateDecrease + lowHeartRateDeviation:
                        self.heartRate -= random.randint(0, lowHeartRateMaxVariance)

                    else:
                        self.heartRate += random.randint(0, lowHeartRateMaxVariance)

                tag = EdgeTag('Device', 'heart rate', self.heartRate)
                edgeData.tagList.append(tag)
                print("generate heart rate data : " + str(self.heartRate) + " (" + self.fetalStatus + ")")

            def genButtonPressedData():
                if chance <= probabilityToPressButton and self.fetalStatus == 'high heart rate' and self.count > 10:
                    tag = EdgeTag('Device', 'fetal movement pressed', 100)
                    edgeData.tagList.append(tag)
                    print("generate button pressed data")

            genHeartRateData()
            genButtonPressedData()

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
