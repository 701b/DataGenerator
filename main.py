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

        # 정상 상태
        normalHeartRateStandard = 135  # 태아의 심박수 기준
        normalHeartRateDeviation = 10  # 태아가 정상 상태일 때 심박수 편차
        normalHeartRateMaxVariance = 2  # 태아가 정상 상태일 때 초당 심박수 최대 변화량
        probabilityToNormalStatus = 20  # 태아가 정상 상태로 돌아올 확률 (value / 10000)

        # 심박수 불규칙 상태
        irregularHeartRateDeviation = 20  # 태아의 심박수가 불규칙적일 때 심박수 편차
        irregularHeartRateMaxVariance = 6  # 태아의 심박수가 불규칙적일 때 초당 심박수 최대 변화량
        probabilityToIrregularHeartRateStatus = 5  # 태아의 심박수가 불규칙적으로 변하게 될 확률 (value / 10000)

        # 높은 심박수 상태
        highHeartRateIncrease = 25  # 태아의 심박수가 높은 상태일 때 심박수 기준 상승치
        highHeartRateDeviation = 15  # 태아의 심박수가 높은 상태일 때 심박수 편차
        highHeartRateMaxVariance = 2.8  # 태아의 심박수가 높은 상태일 때 초당 심박수 최대 변화량
        probabilityToHighHeartRateStatus = 10  # 태아의 심박수가 높은 상태로 변하게 될 확률 (value / 1000)

        # 낮은 심박수 상태
        lowHeartRateDecrease = 20  # 태아의 심박수가 낮은 상태일 때 심박수 기준 하락치
        lowHeartRateDeviation = 6  # 태아의 심박수가 낮은 상태일 때 심박수 편차
        lowHeartRateMaxVariance = 1.2  # 태아의 심박수가 낮은 상태일 때 초당 심박수 최대 변화량
        probabilityToLowHeartRateStatus = 10  # 태아의 심박수가 낮은 상태로 변하게 될 확률 (value / 10000)

        # 상태 변화까지 최소 카운트 (value / 10)초
        minCountUntilStatusVariation = 900

        # 추세
        upDownMaxVariation = 15
        probabilityToUpDown = 100  # 추세가 바뀔 확률

        # 심박수 급락
        suddenDropAmount = 10  # 심박수가 급락할 때 그 정도
        probabilityOfSuddenDrop = 15  # 심박수가 급락할 확률 (value / 10000)

        # 태동 버튼
        probabilityToPressButton = 500  # 태아의 심박수가 높은 상태일 때 임산부가 버튼을 누를 확률 (value / 10000)
        minIntervalToPressButton = 150  # 임산부가 버튼을 누르는 최소 간격 (value / 10)초

        # 현재 수치
        self.fetalStatus = 'normal'
        self.heartRate = normalHeartRateStandard
        self.preHeartRate = self.heartRate
        self.count = 0
        self.trend = 0
        self.buttonCount = 0
        self.suddenDropCount = 21

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
            heartRateAnalogConfig = AnalogTagConfig(name='heart rate', description='heart rate', readOnly=False, arraySize=0, spanHigh=1000, spanLow=0, engineerUnit='', integerDisplayFormat=4, fractionDisplayFormat=1)
            fetalMovementAnalogConfig = AnalogTagConfig(name='fetal movement', description='fetal movement', readOnly=False, arraySize=0, spanHigh=1000, spanLow=0, engineerUnit='', integerDisplayFormat=4, fractionDisplayFormat=1)
            uterineContractionAnalogConfig = AnalogTagConfig(name='uterine contraction', description='uterine contraction', readOnly=False, arraySize=0, spanHigh=1000, spanLow=0, engineerUnit='', integerDisplayFormat=4, fractionDisplayFormat=1)
            fetalMovementButtonPressedAnalogConfig = AnalogTagConfig(name='fetal movement pressed', description='fetal movement pressed', readOnly=False, arraySize=0, spanHigh=1000, spanLow=0, engineerUnit='', integerDisplayFormat=4, fractionDisplayFormat=1)

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
            self.buttonCount += 1

            if self.count >= minCountUntilStatusVariation:
                if self.fetalStatus == 'normal':  # 태아가 정상 상태일 때
                    if chance <= probabilityToIrregularHeartRateStatus:
                        self.fetalStatus = 'irregular heart rate'
                        self.count = 0

                    elif self.heartRate > normalHeartRateStandard + normalHeartRateDeviation:  # 태아의 심박수가 높은 편일 때
                        if 2000 < chance <= probabilityToHighHeartRateStatus + 2000:
                            self.fetalStatus = 'high heart rate'
                            self.count = 0

                    elif self.heartRate < normalHeartRateStandard - normalHeartRateDeviation:  # 태아의 심박수가 낮은 편일 때
                        if 4000 < chance <= probabilityToLowHeartRateStatus + 4000:
                            self.fetalStatus = 'low heart rate'
                            self.count = 0

                else:  # 태아가 정상 상태가 아닐 때
                    if chance <= probabilityToNormalStatus:
                        if self.fetalStatus == 'irregular heart rate':  # 불규칙 상태에서 정상으로 돌아올 때 바로 정상 수치 주변으로 돌아오도록 함
                            self.heartRate = normalHeartRateStandard + self.trend

                        self.fetalStatus = 'normal'
                        self.count = 0

            chance = random.randint(1, 10000)

            if chance <= probabilityToUpDown and self.fetalStatus != 'irregular heart rate':
                self.trend += random.randint(-upDownMaxVariation / 3, upDownMaxVariation / 3)
                if self.trend > upDownMaxVariation:
                    self.trend = upDownMaxVariation
                elif self.trend < -upDownMaxVariation:
                    self.trend = -upDownMaxVariation

            def genHeartRateData():
                power = 8
                standard = self.trend;
                maxVariation = 0;
                deviation = self.trend;
                restorationProbabilityInRange = 0
                restorationProbabilityOutRange = 0
                decreaseBonus = 0
                increaseBonus = 0

                chance = random.randint(1, 10000)

                if self.fetalStatus == 'normal':
                    standard += normalHeartRateStandard
                    maxVariation = normalHeartRateMaxVariance
                    deviation += normalHeartRateDeviation
                    restorationProbabilityInRange = 5100
                    restorationProbabilityOutRange = 6000

                    if self.preHeartRate > self.heartRate:
                        increaseBonus = 2000
                    else:
                        decreaseBonus = 2000

                elif self.fetalStatus == 'irregular heart rate':
                    standard += normalHeartRateStandard
                    maxVariation = irregularHeartRateMaxVariance
                    deviation += irregularHeartRateDeviation
                    restorationProbabilityInRange = 7000
                    restorationProbabilityOutRange = 10000

                elif self.fetalStatus == 'high heart rate':
                    standard += normalHeartRateStandard + highHeartRateIncrease
                    maxVariation = highHeartRateMaxVariance
                    deviation += highHeartRateDeviation
                    restorationProbabilityInRange = 5100
                    restorationProbabilityOutRange = 6000

                elif self.fetalStatus == 'low heart rate':
                    standard += normalHeartRateStandard - lowHeartRateDecrease
                    maxVariation = lowHeartRateMaxVariance
                    deviation += lowHeartRateDeviation
                    restorationProbabilityInRange = 5100
                    restorationProbabilityOutRange = 6000

                # sudden drop인 경우 복원하기
                if self.suddenDropCount <= 20:
                    self.heartRate += (suddenDropAmount / 5) * pow(suddenDropAmount, (-self.suddenDropCount / 10))
                    self.suddenDropCount += 1

                # 범위에 있을 때 확률적으로 sudden drop
                if standard + deviation >= self.heartRate >= standard - deviation:
                    if chance <= probabilityOfSuddenDrop and self.suddenDropCount > 20:
                        self.heartRate -= suddenDropAmount
                        self.suddenDropCount = 0
                        # print("sudden drop!")

                    if standard > self.heartRate:
                        if chance <= restorationProbabilityInRange + increaseBonus:
                            self.heartRate += pow(random.uniform(0, 1), power) * maxVariation
                        else:
                            self.heartRate -= pow(random.uniform(0, 1), power) * maxVariation
                    else:
                        if chance <= restorationProbabilityInRange + decreaseBonus:
                            self.heartRate -= pow(random.uniform(0, 1), power) * maxVariation
                        else:
                            self.heartRate += pow(random.uniform(0, 1), power) * maxVariation
                elif self.heartRate > standard + deviation:
                    if chance <= restorationProbabilityOutRange + decreaseBonus:
                        self.heartRate -= pow(random.uniform(0, 1), power) * maxVariation
                    else:
                        self.heartRate += pow(random.uniform(0, 1), power) * maxVariation
                else:
                    if chance <= restorationProbabilityOutRange + increaseBonus:
                        self.heartRate += pow(random.uniform(0, 1), power) * maxVariation
                    else:
                        self.heartRate -= pow(random.uniform(0, 1), power) * maxVariation

                tag = EdgeTag('Device', 'heart rate', self.heartRate)
                edgeData.tagList.append(tag)
                # print("generate heart rate data : " + str(self.heartRate) + " (" + self.fetalStatus + "), (" + str(standard) + ")")

            def genButtonPressedData():
                if chance <= probabilityToPressButton and self.fetalStatus != 'irregular heart rate' and self.heartRate > 160 and self.buttonCount > minIntervalToPressButton:
                    tag = EdgeTag('Device', 'fetal movement pressed', 100)
                    edgeData.tagList.append(tag)
                    # print("generate button pressed data")
                    self.buttonCount = 0

            genHeartRateData()
            genButtonPressedData()

            return edgeData

        def sendData():
            data = generateData()
            self.edgeAgent.sendData(data)

        def start():
            connect()

            _config = generateConfig()
            self.edgeAgent.uploadConfig(action=constant.ActionType['Create'], edgeConfig=_config)

            frequency = 0.1

            if self.timer is None:
                self.timer = RepeatedTimer(frequency, sendData)
                sendData()

        t = threading.Thread(target=start)
        t.start()


main = App()
