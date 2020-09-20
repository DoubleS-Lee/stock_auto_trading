import os
import sys

from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from PyQt5.QtTest import *
from config.errorCode import *
from config.kiwoomType import *


class Kiwoom(QAxWidget):
    def __init__(self):
        # 상속받은 QAxWidget의 기능을 그대로 가져다 쓰기 위해 super()를 사용
        super().__init__()

        print("Kiwoom 클래스 입니다")

        # config/kiwoomType.py 내의 RealType() 클래스 불러오기
        self.realType = RealType()

        ############## event loop 모음 ###################
        self.login_event_loop = None
        self.detail_account_info_event_loop = QEventLoop()  # 쓰레드 처리
        #################################################

        ############## 스크린 번호 모음 ##################
        self.screen_my_info = '2000'
        self.screen_calculation_stock = '4000'
        self.screen_real_stock = '5000' # 종목별로 할당할 스크린 번호
        self.screen_meme_stock = '6000' # 종목별 할당할 주문용 스크린 번호
        self.screen_start_stop_real = '1000'
        #################################################

        ############## 변수 모음 #########################
        self.account_num = None
        self.account_stock_dict = {}
        self.not_account_stock_dict = {}
        self.portfolio_stock_dict = {}  # 선별된 종목들은 다 여기로 들어간다
        self.jango_dict = {} # 오늘 산 종목에 대한 정보
        #################################################

        ############# 종목 분석용 #######################
        self.calcul_data = []
        ################################################

        ############## 계좌 관련 변수 ###################
        self.use_money = 0
        self.use_money_percent = 0.5
        ################################################

        ############# 함수 실행 #########################
        self.get_ocx_instance()
        self.event_slots()
        self.real_event_slots()
        self.signal_login_commConnect()
        self.get_account_info()
        self.detail_account_info()  # 예수금 가져오기
        self.detail_account_mystock()   # 계좌평가금액 가져오기
        self.not_concluded_account()
        # self.calculator_fnc()   # 종목 분석 실행 함수
        self.read_code() # 조건식에 의해 걸러진 종목들을 저장해놓은 파일 불러오기
        self.screen_number_setting()    #스크린 번호를 할당, 위의 변수 모음에 있는 변수들 간에 중복된 종목들이 있을텐데 이를 검사해서 중복된 종목들은 1개로 만들어준다
        ################################################

        # 장 시작시간인지 아닌지 알기 위해 사용
        # (스크린번호, 종목코드(필요없음), FID번호(KOA-실시간목록 안에 해당 번호들이 있다) 여기서는 215(장운영구분)가 꺼내와 질것이다, 0은 덮어쓰기 1은 붙여쓰기 여기서는 처음에 한번 불러오는 거니까 0을 썼다)
        self.dynamicCall('SetRealReg(String, String, String, String)', self.screen_start_stop_real, '', self.realType.REALTYPE['장시작시간']['장운영구분'], '0')

        for code in self.portfolio_stock_dict.keys():
            screen_num = self.portfolio_stock_dict[code]['스크린번호']
            fids = self.realType.REALTYPE['주식체결']['체결시간']
            # (스크린번호, 종목코드, FID번호(KOA-실시간목록 안에 해당 번호들이 있다) 여기서는 20(체결시간)이 꺼내와 질것이다, 추가 등록이어서 1로 설정해놓음)
            # SetRealReg로 실시간 등록
            self.dynamicCall('SetRealReg(String, String, String, String)', screen_num, code, fids, '1')
            print(f'실시간 등록 코드 : {code}, fid 번호 : {fids}, 스크린 번호 : {screen_num}')
        

    def get_ocx_instance(self): # 응용프로그램 제어, 레지스트리에 등록된 경로 넣기
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')
    
    # 이벤트만 모아 놓는 함수
    def event_slots(self): 
        # OnEventConnect : 로그인 상태 전달
        ################## 여기서 connect는 OnEventConnect를 통해 나온 값(=인자)을 ()안의 함수에 넘겨주면서 함수를 실행하겠다는 뜻이다
        self.OnEventConnect.connect(self.login_slot)    # 자동 로그인
        # TR 요청 -> self.trdata_slot에 TR요청을 받는다
        # 여기서 connect는 OnEventConnect를 통해 나온 값(=인자)을 ()안의 함수에 넘겨주면서 함수를 실행하겠다는 뜻이다
        self.OnReceiveTrData.connect(self.trdata_slot)
        self.OnReceiveMsg.connect(self.msg_slot)
    
    # 실시간 이벤트 처리 함수
    def real_event_slots(self):
        self.OnReceiveRealData.connect(self.realdata_slot)
        # 주문에 대한 이벤트 걸기
        # 앞으로 모든 주문은 여기서 받아질 예정
        self.OnReceiveChejanData.connect(self.chejan_slot)

    
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
        print("예수금 요청")

        self.dynamicCall('SetInputValue(String, String)', '계좌번호', self.account_num)
        self.dynamicCall('SetInputValue(String, String)', '비밀번호', "0000")
        self.dynamicCall('SetInputValue(String, String)', '비밀번호입력매체구분', '00')
        self.dynamicCall('SetInputValue(String, String)', '조회구분', '2')
        # ('요청이름', 'TR번호', 'PreNext', '화면번호=screennumber')
        self.dynamicCall('CommRqData(String, String, int, String)', '예수금상세현황요청', 'opw00001', '0', self.screen_my_info)

        # 쓰레드 처리
        self.detail_account_info_event_loop.exec_()

    # signal로 키움 서버에 데이터를 요청하는 부분
    def detail_account_mystock(self, sPrevNext='0'): # 계좌평가잔고내역요청(TR번호 : opw00018)
        print(f"계좌평가 잔고내역 요청")

        self.dynamicCall('SetInputValue(String, String)', '계좌번호', self.account_num)
        self.dynamicCall('SetInputValue(String, String)', '비밀번호', "0000")
        self.dynamicCall('SetInputValue(String, String)', '비밀번호입력매체구분', '00')
        self.dynamicCall('SetInputValue(String, String)', '조회구분', '2')
        # ('요청이름', 'TR번호', 'PreNext', '화면번호=screennumber')
        # CommRqData()는 조회를 요청하는 함수이다
        # dynamicCall : 다른 서버나 응용프로그램에 데이터를 전송할 수 있게 해주는 PyQt5의 내장 함수
        self.dynamicCall('CommRqData(String, String, int, String)', '계좌평가잔고내역요청', 'opw00018', sPrevNext, self.screen_my_info)

        # 쓰레드 처리
        self.detail_account_info_event_loop.exec_()

    # 미체결 내역 요청
    def not_concluded_account(self, sPrevNext="0"):
        print(f"미체결 내역 요청")

        self.dynamicCall('SetInputValue(String, String)', '계좌번호', self.account_num)
        self.dynamicCall('SetInputValue(String, String)', '체결구반', "1")
        self.dynamicCall('SetInputValue(String, String)', '매매구분', '0')

        self.dynamicCall('CommRqData(String, String, int, String)', '실시간미체결요청', 'opt10075', sPrevNext, self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    # 키움 서버에서 요청한 데이터를 받아들이는 함수
    # TR 요청만 모아 놓은 함수 
    def trdata_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):    #TR 함수로 꺼내오는 부분
        # tr 요청을 받는 슬롯(구역)
        # (self, 스크린번호, 내가 요청했을때 지은 이름, 요청 id/tr코드, 사용안함, 데이터가 많아서 다음페이지가 있는지)

        if sRQName == "예수금상세현황요청":
            deposit = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '예수금')
            deposit = int(deposit)
            print(f"예수금 : {deposit}")

            self.use_money = deposit * self.use_money_percent
            self.use_money = self.use_money / 4

            ok_deposit = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '출금가능금액')
            ok_deposit = int(ok_deposit)
            print(f"출금가능금액 : {ok_deposit}")

            self.detail_account_info_event_loop.exit()

        if sRQName == "계좌평가잔고내역요청":
            total_buy_money = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '총매입금액')
            total_buy_money_result = int(total_buy_money)
            print(f"총매입금액 : {total_buy_money_result}")


            total_profit_loss_rate = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '총수익률(%)')
            total_profit_loss_rate_result = float(total_buy_money)
            print(f"총수익률(%) : {total_profit_loss_rate_result}%")
            
            # GetRepeatCnt()는 멀티데이터 조회 용도이다 (데이터를 한줄한줄 반복해서 가져오게 하는 것)
            rows = self.dynamicCall('GetRepeatCnt(String, String)', sTrCode, sRQName)
            cnt = 0
            for i in range(rows):
                code = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '종목코드')
                code_nm = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '종목명')
                stock_quantity = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '보유수량')
                buy_price = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '매입가')
                learn_rate = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '수익률(%)')
                current_price = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '현재가')
                total_chegual_price = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '매입금액')
                possible_quantity = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '매매가능수량')
                
                code = code.strip()[1:]
                code_nm = code_nm.strip()
                stock_quantity = int(stock_quantity.strip())
                buy_price = int(buy_price.strip())
                learn_rate = float(learn_rate.strip())
                current_price = int(current_price.strip())
                total_chegual_price = int(total_chegual_price.strip())
                possible_quantity = int(possible_quantity.strip())

                if code in self.account_stock_dict:
                    pass
                else:
                    self.account_stock_dict.update({code:{}})
                
                self.account_stock_dict[code].update({'종목명':code_nm})
                self.account_stock_dict[code].update({'보유수량':stock_quantity})
                self.account_stock_dict[code].update({'매입가':buy_price})
                self.account_stock_dict[code].update({'수익률(%)':learn_rate})
                self.account_stock_dict[code].update({'현재가':current_price})
                self.account_stock_dict[code].update({'매입금액':total_chegual_price})
                self.account_stock_dict[code].update({'매매가능수량':possible_quantity})

                cnt += 1

            print(f'보유한 종목 수 : {cnt}')
            print(f'보유한 종목 정보 : {self.account_stock_dict}')

            # 보유 종목 수가 20이 넘어서 다음 페이지가 있을 경우
            if sPrevNext == "2":
                self.detail_account_mystock(sPrevNext='2')
            else:
                self.detail_account_info_event_loop.exit()

        elif sRQName == "실시간미체결요청":
            rows = self.dynamicCall('GetRepeatCnt(String, String)', sTrCode, sRQName)
            for i in range(rows):
                code = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '종목코드')
                code_nm = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '종목명')
                order_no = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '주문번호')
                order_status = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '주문상태') # 접수, 확인, 체결
                order_quantity = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '주문수량')
                order_price = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '주문가격')
                order_gubun = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '주문구분') # -매도, +매수, -매도
                not_quantity = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '미체결수량')
                ok_quatity = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, i, '체결량')

                code = code.strip()[1:]
                code_nm = code_nm.strip()
                order_no = int(order_no.strip())
                order_status = order_status.strip()
                order_quantity = int(order_quantity.strip())
                order_price = int(order_price.strip())
                order_gubun = order_gubun.strip().lstrip('+').lstrip('-')
                not_quantity = int(not_quantity.strip())
                ok_quatity = int(ok_quatity.strip())

                if order_no in self.not_account_stock_dict:
                    pass
                else:
                    self.not_account_stock_dict[order_no] = {}
                    
                # self.not_account_stock_dict[order_no] 이걸 변수에 할당하고 밑에 코드를 수정하면 연산 속도가 더 빨라진다
                self.not_account_stock_dict[order_no].update({"종목코드" : code})
                self.not_account_stock_dict[order_no].update({"종목명" : code_nm})
                self.not_account_stock_dict[order_no].update({"주문번호" : order_no})
                self.not_account_stock_dict[order_no].update({"주문상태" : order_status})
                self.not_account_stock_dict[order_no].update({"주문수량" : order_quantity})
                self.not_account_stock_dict[order_no].update({"주문가격" : order_price})
                self.not_account_stock_dict[order_no].update({"주문구분" : order_gubun})
                self.not_account_stock_dict[order_no].update({"미체결수량" : not_quantity})
                self.not_account_stock_dict[order_no].update({"체결량" : ok_quatity})

                print(f'미체결 종목 : {self.not_account_stock_dict[order_no]}')

            self.detail_account_info_event_loop.exit()

        elif sRQName == "주식일봉차트조회":            
            code = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '종목코드')
            code = code.strip()
            print(f"{code} 일봉데이터 요청")

            cnt = self.dynamicCall("GetRepeatCnt(String, String)", sTrCode, sRQName)
            print(f'데이터 갯수 : {cnt}일 치 데이터')

            # 한번 조회시 600일치까지 일봉데이터를 받을 수 있다
            for i in range(cnt):
                data = []

                current_price = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '현재가') #=종가
                value = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '거래량')
                trading_value = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '거래대금')
                date = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '일자')
                start_price = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '시가')
                high_price = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '고가')
                low_price = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, '저가')

                data.append('')
                data.append(current_price.strip())
                data.append(value.strip())
                data.append(trading_value.strip())
                data.append(date.strip())
                data.append(start_price.strip())
                data.append(high_price.strip())
                data.append(low_price.strip())
                data.append('')

                self.calcul_data.append(data.copy())
            # 만약 GetCommDataEX()방식을 사용한다면 위의 for문을 사용하지 않고 다음과 같이 쓸수있다#########################################
            # data = self.dynamicCall("GetCommDataEx(String, String)", sTrCode, sRQName)
            # 위의 출력이 다음과 같이 나온다 ['', '현재가', '거래량', '거래대금', '날짜', '시가', '고가', '저가', '']

            

            # 이전 데이터가 있는 경우 추가 조회 요청
            if sPrevNext == '2':
                self.day_kiwoom_db(code=code, sPrevNext=sPrevNext)

            
            else:
                print(f'해당 종목 총 데이터(일) 개수 : {len(self.calcul_data)}')

                # 불러오기가 끝났으면 조건에 부합하는 종목만을 골라서 따로 저장
                # 여기서는 이평선을 이용한 분석을 실시
                # 1. 120일 이평선을 그릴만큼의 데이터가 있는지 체크
                pass_success = False
                if self.calcul_data == None or len(self.calcul_data) < 120:
                    pass_success = False
                else:
                    total_price = 0
                    # 오늘 데이터부터 199일 전까지의 데이터(총 120개)
                    for value in self.calcul_data[:120]:
                        total_price += int(value[1])    #[1]번이 현재가(=종가)
                    moving_average_price = total_price / 120

                    # [0][7]번은 오늘의 저가, [0][6]번은 오늘의 고가
                    # 120일 이평선보다 오늘의 저가가 낮고, 고가가 높은 종목을 찾는다
                    # 오늘자 주가가 120일 이평선에 걸쳐있는지 확인
                    bottom_stock_price = False
                    check_price = None
                    if int(self.calcul_data[0][7]) <= moving_average_price and moving_average_price <= int(self.calcul_data[0][6]):
                        print('오늘의 고가와 저가사이에 120이평선이 속해있는 종목 확인')
                        bottom_stock_price = True
                        check_price = int(self.calcul_data[0][6])

                    # 과거 일봉들이 120일 이평선보다 밑에 있는지 확인
                    # 확인을 하다가 일봉이 120일 이평선보다 위에 있으면 계산 진행
                    prev_price = None   # 과거의 일봉 저가
                    if bottom_stock_price == True:
                        moving_average_price_prev = 0
                        price_top_moving = False

                        idx = 1
                        while True:
                            if len(self.calcul_data[idx:]) < 120:   # 120일치가 있는지 계속 확인
                                print("120일치가 없음!")
                                break
                            total_price = 0
                            for value in self.calcul_data[idx : 120+idx]:
                                total_price += int(value[1])
                            moving_average_price_prev = total_price / 120

                            if moving_average_price_prev <= int(self.calcul_data[idx][6]) and idx <= 20:
                                print("20일동안 주가가 120일 이평선과 같거나 위에 있으면 조건 통과 못함")
                                price_top_moving = False
                                break

                            elif int(self.calcul_data[idx][7]) > moving_average_price_prev and idx > 20:
                                print("120일 이평선 위에 있는 일봉 확인됨")
                                price_top_moving = True
                                prev_price = int(self.calcul_data[idx][7])
                                break

                            idx += 1

                        # 해당 부분 이평선이 가장 최근 일자의 이평선 가격보다 낮은지 확인
                        if price_top_moving == True:
                            if moving_average_price > moving_average_price_prev and check_price > prev_price:
                                print('포착된 이평선의 가격이 오늘자(최근일자) 이평선 가격보다 낮은 것 확인됨')
                                print('포착된 부분의 일봉 저가가 오늘자 일봉의 고가보다 낮은지 확인됨')
                                pass_success = True

                if pass_success == True:
                    print('조건부 통과됨')

                    code_nm = self.dynamicCall('GetMasterCodeName{QString)', code)

                    f = open('files/condition_stock.txt', 'a', encoding = 'utf8')
                    f.write(f'{code}\t{code_nm}\t{str(self.calcul_data[0][1])}\n')
                    # f.write('%s\t%s\t%s\n' %(code, code_nm, str(self.calcul_data[0][1])))
                    f.close()
                
                elif pass_success == False:
                    print('조건부 통과 못함')

                self.calcul_data.clear()
                self.detail_account_info_event_loop.exit()


    # 종목(코스닥) 코드들 받기
    def get_code_list_by_market(self, market_code):
        code_list = self.dynamicCall('GetCodeListByMarket(String)', market_code)
        code_list = code_list.split(';')[:-1]

        return code_list

    # 종목 분석 실행용 함수
    def calculator_fnc(self):
        # 코스닥 종목에 해당하는 코드를 받아온다
        code_list = self.get_code_list_by_market('10')  # 코스닥은 10번이다
        print(f'코스닥 갯수(전체) : {len(code_list)}')

        # 인덱스(idx)당 데이터를 같이 받기 위해 enumerate()를 사용
        for idx, code in enumerate(code_list):
            self.dynamicCall('DisconnectRealData(String)', self.screen_calculation_stock)

            print(f'{idx+1} / {len(code_list)} : KOSDAQ 주식 코드 : {code}를 업데이트 하는 중....')

            self.day_kiwoom_db(code=code)


    # 일봉데이터를 요청한다(sPrevNext 값에 따라 과거데이터를 요청할수도 있는 함수)
    def day_kiwoom_db(self, code=None, date=None, sPrevNext='0'):
        # 빠르게 데이터를 요청하면 서버에서 막아버리는 사태가 발생함 따라서 시간을 두고 코드를 실행시켜야함 (PyQt5.QtTest를 사용함)
        # 다음 코드가 실행되기 전에 3.6초 딜레이를 주는 코드
        QTest.qWait(3600)

        self.dynamicCall("SetInputValue(String, String)", '종목코드', code)
        self.dynamicCall("SetInputValue(String, String)", '수정주가구분', '1')

        if date != None:
            self.dynamicCall("SetInputValue(String, String)", '기준일자', date)
        
        self.dynamicCall("CommRqData(String, String, int, String)", '주식일봉차트조회', 'opt10081', sPrevNext, self.screen_calculation_stock)   # Tr서버로 전송
    
        self.detail_account_info_event_loop.exec_()

    ############## 이후에 매수법칙 계산들어가면 됨 #################
    
    def read_code(self):
        if os.path.exists('files/condition_stock.txt'): # 파일이 있으면 True, 없으면 False로 나옴
            f = open('diles/condition_stock.txt', 'r', encoding='utf8')

            lines = f.readlines()
            for line in lines:
                if line != '':
                    ls = line.split('\t')

                    stock_code = ls[0]
                    stock_name = ls[1]
                    stock_price = int(ls[2].split('\n')[0])
                    stock_price = abs(stock_price)  # 키움 API에서 현재가를 받아올때 하락이면 앞에 -가 붙어서 나오기 때문에 절대값을 씌워준다

                    self.portfolio_stock_dict.update({stock_code:{'종목명':stock_name, '현재가':stock_price}})  # 예시 {'200546':{'종목명':'삼성','현재가':50000}, '200546':{'종목명':'삼성','현재가':50000}}

            f.close()
            print(self.portfolio_stock_dict)

    def screen_number_setting(self):
        screen_overwrite = []

        # 계좌평가 잔고 내역에 있는 종목들(중복검사하여 없으면 넣어줌)
        for code in self.account_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 미체결에 있는 종목들(중복검사하여 없으면 넣어줌)
        for order_number in self.not_account_stock_dict.keys():
            code = self.not_account_stock_dict[order_number]['종목코드']
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 포트폴리오(조건식 검색후 찾아낸 종목들)에 담겨있는 종목들
        for code in self.portfolio_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 스크린 번호 할당 (스크린번호 하나에 요청갯수는 100개까지, 스크린번호는 200개까지 생성가능)
        cnt = 0
        for code in screen_overwrite:
            temp_screen = int(self.screen_real_stock)
            meme_screen = int(self.screen_meme_stock)

            # 스크린번호 1개당 종목코드 50개씩만 넣어주기 위해서 만듦
            if (cnt % 50) == 0:
                temp_screen += 1
                self.screen_real_stock = str(temp_screen)

            # 스크린번호 1개당 종목코드 50개씩만 넣어주기 위해서 만듦
            if (cnt % 50) == 0:
                meme_screen += 1
                self.screen_meme_stock = str(meme_screen)
            
            # self.portfolio_stock_dict에 종목 코드가 있다면 스크린번호, 주문용스크린번호만 업데이트
            if code in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict[code].update({'스크린번호':str(self.screen_real_stock)})
                self.portfolio_stock_dict[code].update({'주문용스크린번호':str(self.screen_meme_stock)})
            # self.portfolio_stock_dict에 종목 코드가 없다면 code와 스크린번호, 주문용스크린번호를 업데이트
            elif code not in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict.update({code: {'스크린번호':str(self.screen_real_stock), '주문용스크린번호':str(self.screen_meme_stock)}})

            cnt += 1
        print(self.potfolio_stock_dict)
    
    # 실시간 데이터 처리 함수
    def realdata_slot(self, sCode, sRealType, sRealData):
        if sRealType == "장시작시간":
            fid = self.realType.REALTYPE[sRealType]['장운영구분']
            value = self.dynamicCall('GetCommRealData(String, int)', sCode, fid)

            if value == '0':
                print('장 시작 전')

            elif value == '3':
                print('장 시작')

            elif value == '2':
                print('장 종료, 동시호가로 넘어감')

            elif value == '4':
                print('3시 30분 장 종료')

                for code in self.portfolio_stock_dict.keys():
                    self.dynamicCall('SetRealRemove(String, String', self.portfolio_stock_dict[code]['스크린번호'], code)

                QTest.qWait(5000)
                # 장이 끝나면 지금까지 썼던 메모장 파일을 지우고
                self.file_delete()
                # 오늘 장을 바탕으로 종목 분석에 들어간다
                self.calculator_fnc()

                sys.exit()
            
        elif sRealType == '주식체결':
            a = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['체결시간']) # 체결시간 출력 형태 HHMMSS
            b = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['현재가']) # +(-)2500
            c = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['전일대비']) # +(-)2500
            d = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['등락율']) # +(-)3.4%
            e = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['(최우선)매도호가']) # +(-)3.4% # 이 가격으로 팔면 바로 팔리는 가격
            f = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['(최우선)매수호가']) # +(-)3.4% # 이 가격으로 사면 바로 사지는 가격
            g = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['거래량']) # +(-)644
            h = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['누적거래량']) # +(-)644
            i = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['고가']) # +(-)644 # 오늘자 제일 높은 가격
            j = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['시가']) # +(-)644 # 
            k = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['저가']) # +(-)644 # 오늘자 제일 낮은 가격

            b = abs(int(b))
            c = abs(int(c))
            d = float(d)
            e = abs(int(e))
            f = abs(int(f))
            g = abs(int(g))
            h = abs(int(h))
            i = abs(int(i))
            j = abs(int(j))
            k = abs(int(k))

            if sCode not in self.portfolio_stock_dict:
                self.portfolio_stock_dict.update({sCode:{}})
            
            self.portfolio_stock_dict[sCode].update({'체결시간':a})
            self.portfolio_stock_dict[sCode].update({'현재가':b})
            self.portfolio_stock_dict[sCode].update({'전일대비':c})
            self.portfolio_stock_dict[sCode].update({'등락율':d})
            self.portfolio_stock_dict[sCode].update({'(최우선)매도호가':e})
            self.portfolio_stock_dict[sCode].update({'(최우선)매수호가':f})
            self.portfolio_stock_dict[sCode].update({'거래량':g})
            self.portfolio_stock_dict[sCode].update({'누적거래량':h})
            self.portfolio_stock_dict[sCode].update({'고가':i})
            self.portfolio_stock_dict[sCode].update({'시가':j})
            self.portfolio_stock_dict[sCode].update({'저가':k})

            print(self.portfolio_stock_dict[sCode])
            
            # 매수, 매도를 위한 조건문 작성 여기 if 문에서 매도를 하는 것이다 #########################################################################
            # 매도조건1!!!!!!! 계좌 잔고 평가 내역에 있고 오늘 산 잔고에는 없을 경우
            if sCode in self.account_stock_dict.keys() and sCode not in self.jango_dict.keys():
                print(f'신규 매도 조건 1 {sCode}')

                asd = self.account_stock_dict[sCode]

                meme_rate = ((b - asd['매입가']) / asd['매입가'])*100

                if asd['매매가능수량'] > 0 and (meme_rate > 5 or meme_rate < -5):
                    order_success = self.dynamicCall('SendOrder(String, String, String, int, String, int, int, String, String)',
                                                    ['신규매도', self.portfolio_stock_dict[sCode]['주문용스크린번호'], self.account_num, 2,
                                                    sCode, asd['매매가능수량'], 0, self.realType.SENDTYPE['거래구분']['시장가'], ''])
                    if order_success == 0:
                        print('매도주문 전달 성공')
                        del self.account_stock_dict[sCode]
                    else:
                        print('매도주문 전달 실패')


            # 매도조건2!!!! 오늘 산 잔고에 있을 경우 매도       
            elif sCode in self.jango_dict.keys():
                print(f'신규 매도 조건 2 {sCode}')

                jd = self.jango_dict[sCode]
                meme_rate = (b-jd['매입단가']) / jd['매입단가'] * 100

                if jd['주문가능수량'] > 0 and (meme_rate > 5 or meme_rate < -5):
                    order_success = self.dynamicCall('SendOrder(String, String, String, int, String, int, int, String, String)',
                                                    ['신규매도', self.portfolio_stock_dict[sCode]['주문용스크린번호'], self.account_num, 2,
                                                    sCode, jd['주문가능수량'], 0, self.realType.SENDTYPE['거래구분']['시장가'], ''])

                    if order_success == 0:
                        self.logging.logger.debug('매도주문 전달 성공')
                    else:
                        self.logging.logger.debug('매도주문 전달 실패')

            # 매수조건 !!!!   등락율이 2.0% 이상이고 오늘 산 잔고에 없을 경우/ d는 등락율
            elif d > 2.0 and sCode not in self.jango_dict:
                print(f'신규 매수 조건 1 {sCode}')

                # 얼만큼 살지 결정(quantity)
                # e는 (최우선)매도호가
                result = (self.user_money * 0.1 / e)
                quantity = int(result)

                order_success = self.dynamicCall('SendOrder(String, String, String, int, String, int, int, String, String)',
                                                ['신규매수', self.portfolio_stock_dict[sCode]['주문용스크린번호'], self.account_num, 1,
                                                sCode, quantity, e, self.realType.SENDTYPE['거래구분']['지정가'], ''])
                
                if order_success == 0:
                    self.logging.logger.debug('매수주문 전달 성공')
                else:
                    self.logging.logger.debug('매수주문 전달 실패')

            # 여기서 중요#####################
            # self.not_account_stock_dict를 다른 메모리에 복사해놓고 그걸로 계산을 진행해야한다
            # 안 그러면 self.not_account_stock_dict가 계산하고 있는 중에도 계속 업데이트가 되면서 오류를 발생시키기 때문 / .copy()를 써도 된다
            not_meme_list = list(self.not_account_stock_dict)
            for order_num in not_meme_list:
                code = self.not_account_stock_dict[order_num]['종목코드']
                meme_price = self.not_account_stock_dict[order_num]['주문가격']
                not_quantity = self.not_account_stock_dict[order_num]['미체결수량']
                order_gubun = self.not_account_stock_dict[order_num]['주문구분']

                # 매수 취소하는 경우 #############################################################
                # 매수명령 들어오고, 미체결수량이 0보다 크고, (최우선)매도호가가 주문가격보다 큰 경우에 진행
                if order_gubun == '매수' and not_quantity > 0 and e > meme_price:
                    print(f'매수취소 한다 {sCode}')
                    # 주문수량에 0을 넣으면 전량이라는 뜻이다
                    order_success = self.dynamicCall('SendOrder(String, String, String, int, String, int, int, String, String)',
                                                    ['매수취소', self.portfolio_stock_dict[sCode]['주문용스크린번호'], self.account_num, 3,
                                                    sCode, 0, 0, self.realType.SENDTYPE['거래구분']['지정가'], order_num])

                    if order_success == 0:
                        self.logging.logger.debug('매수취소 전달 성공')
                    else:
                        self.logging.logger.debug('매수취소 전달 실패')
                
                # 미체결 수량이 0이면 우리의 딕셔너리에서도 지워준다
                elif not_quantity == 0:
                    del self.not_account_stock_dict[order_num]

    # 체결 정보 받아오기
    def chejan_slot(self, sGubun, nItemCnt, sFIdList):
        # 체결구분 접수와 체결시 sGubun 이 0임
        if int(sGubun) == 0:
            print('주문체결')
            account_num = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['계좌번호'])
            sCode = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['종목코드'])[1:]
            stock_name = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['종목명'])
            origin_order_number = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['원주문번호'])
            order_number = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['주문번호'])
            order_status = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['주문상태'])   # 접수, 확인, 체결
            order_quan = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['주문수량'])
            order_price = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['주문가격'])
            not_chegual_quan = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['미체결수량'])
            order_gubun = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['주문구분'])
            chegual_time_str = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['주문/체결시간'])
            chegual_price = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['체결가'])

            srock_name = stock_name.strip()
            order_quan = int(order_quan)
            order_price = int(order_price)
            not_chegual_quan = int(not_chegual_quan)
            order_gubun = order_gubun.strip().lstrip('+').lstrip('-')

            if chegual_price == '':
                chegual_price = 0
            else:
                chegual_price = int(chegual_price)

            chegual_quantity = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['체결량'])

            if chegual_quantity == '':
                chegual_quantity = 0
            else:
                chegual_quantity = int(chegual_quantity)
            
            current_price = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['현재가'])
            current_price = abs(int(current_price))

            first_sell_price = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['(최우선)매도호가'])
            first_sell_price = abs(int(first_sell_price))

            first_buy_price = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['주문체결']['(최우선)매수호가'])
            first_buy_price = abs(int(first_buy_price))

            ##################### 새로 들어온 주문이면 주문번호 할당
            if order_number not in self.not_account_stock_dict.keys():
                self.not_account_stock_dict.update({order_number : {}})
            
            self.not_account_stock_dict[order_number].update({'종목코드':sCode})
            self.not_account_stock_dict[order_number].update({'주문번호':order_number})
            self.not_account_stock_dict[order_number].update({'종목명':stock_name})
            self.not_account_stock_dict[order_number].update({'주문상태':order_status})
            self.not_account_stock_dict[order_number].update({'주문수량':order_quan})
            self.not_account_stock_dict[order_number].update({'주문가격':order_price})
            self.not_account_stock_dict[order_number].update({'미체결수량':not_chegual_quan})
            self.not_account_stock_dict[order_number].update({'원주문번호':origin_order_number})
            self.not_account_stock_dict[order_number].update({'주문구분':order_gubun})
            self.not_account_stock_dict[order_number].update({'주문/체결시간':chegual_time_str})
            self.not_account_stock_dict[order_number].update({'체결가':chegual_price})
            self.not_account_stock_dict[order_number].update({'체결량':chegual_quantity})
            self.not_account_stock_dict[order_number].update({'현재가':current_price})
            self.not_account_stock_dict[order_number].update({'(최우선)매도호가':first_sell_price})
            self.not_account_stock_dict[order_number].update({'(최우선)매수호가':first_buy_price})
        
            print(self.not_account_stock_dict)

        # 국내주식 잔고전달일시 sGubun이 1임
        elif int(sGubun) == 1:
            print('잔고')

            account_num = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['잔고']['계좌번호'])
            sCode = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['잔고']['종목코드'])[1:]
            stock_name = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['잔고']['종목명'])
            current_price = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['잔고']['현재가'])
            stock_quan = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['잔고']['보유수량'])
            like_quan = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['잔고']['주문가능수량'])   # 접수, 확인, 체결
            buy_price = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['잔고']['매입단가'])
            total_buy_price = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['잔고']['총매입가'])
            meme_gubun = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['잔고']['매도매수구분'])
            first_sell_price = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['잔고']['(최우선)매도호가'])
            first_buy_price = self.dynamicCall('GetChejanData(int)', self.realType.REALTYPE['잔고']['(최우선)매수호가'])

            stock_name = stock_name.strip()
            current_price = abc(int(current_price))
            stock_quan = int(stock_quan)
            like_quan = int(like_quan)
            buy_price = abs(int(buy_price))
            total_buy_price = int(total_buy_price)
            meme_gubun = self.realType.REALTYPE['매도매수구분'][meme_gubun]
            first_sell_price = abs(int(first_sell_price))
            first_buy_price = abs(int(first_buy_price))

            # 딕셔너리에 업데이트를 시킨다
            if sCode not in self.jango_dict.keys():
                self.jango_dict.update({sCode:{}})

            self.jango_dict[sCode].update({'현재가': current_price})
            self.jango_dict[sCode].update({'종목코드': sCode})
            self.jango_dict[sCode].update({'종목명': stock_name})
            self.jango_dict[sCode].update({'보유수량': stock_quan})
            self.jango_dict[sCode].update({'주문가능수량': like_quan})
            self.jango_dict[sCode].update({'매입단가': buy_price})
            self.jango_dict[sCode].update({'총매입가': total_buy_price})
            self.jango_dict[sCode].update({'매도매수구분': meme_gubun})
            self.jango_dict[sCode].update({'(최우선)매도호가': first_sell_price})
            self.jango_dict[sCode].update({'(최우선)매수호가': first_buy_price})

            # 보유수량이 0이면 잔고에서 없앤다
            if stock_quan == 0:
                del self.jango_dict[sCode]
                self.dynamicCall('SetRealRemove(String, String)', self.portfolio_stock_dict[sCode]['스크린번호'], sCode)

    # 송수신 메세지 get
    def msg_slot(self,sScrNo, sRQName, sTrCode, msg):
        print(f'스크린 : {sScrNo}, 요청이름 : {sRQName}, tr코드 : {sTrCode} --- {msg}')

    # 장이 끝나면 다음날을 위해서 condition_stock.py 파일을 지우고 새로만들어주는 함수
    def file_delete(self):
        if os.path.isfile('files/condition_stock.txt'):
            os.remove('files/condition_stock.txt')



