from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from config.errorCode import *


class Kiwoom(QAxWidget):
    def __init__(self):
        # 상속받은 QAxWidget의 기능을 그대로 가져다 쓰기 위해 super()를 사용
        super().__init__()

        print("Kiwoom 클래스 입니다")

        ############## event loop 모음 ###################
        self.login_event_loop = None
        self.detail_account_info_event_loop = None
        #################################################

        ############## 변수 모음 #########################
        self.account_num = None
        #################################################

        ############# 함수 실행 #########################
        self.get_ocx_instance()
        self.event_slots()
        self.signal_login_commConnect()
        self.get_account_info()
        self.detail_account_info()
        ################################################
    
    def get_ocx_instance(self): # 응용프로그램 제어, 레지스트리에 등록된 경로 넣기
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')
    
    # 이벤트만 모아 놓는 함수
    def event_slots(self): 
        # OnEventConnect : 로그인 상태 전달
        ################## 여기서 connect는 OnEventConnect를 통해 나온 값(=인자)을 ()안의 함수에 넘겨주면서 함수를 실행하겠다는 뜻이다
        self.OnEventConnect.connect(self.login_slot)    # 자동 로그인
        # TR 요청 -> self.trdata_slot에 TR요청을 받는다
        self.OnReceiveTrData.connect(self.trdata_slot)
    
    def signal_login_commConnect(self): # 로그인을 시도하는 함수
        # commConnect() : 키움증권 API에 로그인을 시도하는 함수
        ################# dynamicCall : 다른 서버나 응용프로그램에 데이터를 전송할 수 있게 해주는 PyQt5의 내장 함수
        self.dynamicCall("CommConnect()")

        # QEventLoop() : PyQt5.QtCore에서 제공하는 클래스
        self.login_event_loop = QEventLoop()
        # 로그인이 완료될때까지 기다리게 만듦
        self.login_event_loop.exec_()

    def login_slot(self, errCode): # 로그인 신호 획득
        # errCode가 0이여야만 로그인이 성공했다는 뜻이다
        print(errors(errCode))
        
        self.login_event_loop.exit()
    
    def get_account_info(self): # 계좌번호 받아오기
        account_list = self.dynamicCall("GetLoginInfo(String)", "ACCNO")
        self.account_num = account_list.split(';')[0]
        print(f'나의 보유 계좌번호 : {self.account_num}')

    # signal로 키움 서버에 데이터를 요청하는 부분
    def detail_account_info(self): # 예수금상세현황요청(TR번호 : opw00001)
        print("예수금을 요청하는 부분")

        self.dynamicCall('SetInputValue(String, String)', '계좌번호', self.account_num)
        self.dynamicCall('SetInputValue(String, String)', '비밀번호', "0000")
        self.dynamicCall('SetInputValue(String, String)', '비밀번호입력매체구분', '00')
        self.dynamicCall('SetInputValue(String, String)', '조회구분', '2')
        # ('요청이름', 'TR번호', 'PreNext', '화면번호=screennumber')
        self.dynamicCall('CommRqData(String, String, int, String)', '예수금상세현황요청', 'opw00001', '0', '2000')

        # 쓰레드 처리
        self.detail_account_info_event_loop = QEventLoop()
        self.detail_account_info_event_loop.exec_()

    # 키움 서버에서 요청한 데이터를 받아들이는 함수
    # TR 요청만 모아 놓은 함수 
    def trdata_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):    #TR 함수로 꺼내오는 부분
        # tr 요청을 받는 슬롯(구역)
        # (self, 스크린번호, 내가 요청했을때 지은 이름, 요청 id/tr코드, 사용안함, 다음페이지가 있는지)

        if sRQName == "예수금상세현황요청":
            deposit = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '예수금')
            deposit = int(deposit)
            print(f"예수금 : {deposit}")

            ok_deposit = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '출금가능금액')
            ok_deposit = int(ok_deposit)
            print(f"출금가능금액 : {ok_deposit}")

        self.detail_account_info_event_loop.exit()





