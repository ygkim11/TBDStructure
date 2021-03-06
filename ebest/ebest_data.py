import win32com.client
import pythoncom
import time
import pandas as pd
import numpy as np
import pickle

class MyObjects:
    server = "demo"  # hts:실투자, demo: 모의투자
    credentials = pd.read_csv("./credentials/credentials.csv", index_col=0, dtype=str).loc[server, :]

    login_ok = False  # Login
    tr_ok = False  # TR요청
    real_ok = False  # 실시간 요청
    acc_no_stock = credentials["acc_no_stocks"]  # 주식 계좌번호
    acc_no_future = credentials["acc_no_futures"] # 주식선물 계좌번호
    acc_pw = credentials["acc_pw"] # 계좌비밀번호

    code_list = []
    stock_total_code_list = []  # < 종목코드 모아놓는 리스트
    stock_KOSPI_code_list = []
    stock_KOSDAQ_code_list = []
    stock_futures_code_list = []  # 주식선물 코드
    stock_futures_basecode_list = []  # 주식선물의 기초자산 종목코드

    stock_futures_basecode_dict = {}
    stock_futures_basecode_pickle = {}
    whole_universe_code_list = []

    #### 요청 함수 모음
    tr_event = None  # TR요청에 대한 API 정보
    real_event_market = None
    real_event_KOSPI = None  # 실시간 요청에 대한 API 정보
    real_event__KOSPI_hoga = None  # 실시간 요청에 대한 API 정보
    real_event_KOSDAQ = None  # 실시간 요청에 대한 API 정보
    real_event_KOSDAQ_hoga = None  # 실시간 요청에 대한 API 정보
    real_event_fu = None
    real_event_fu_hoga = None

    t8412_request = None  # 차트데이터 조회 요청함수
    ##################

    monitor_stocks = None
    api_queue = None

# 실시간으로 수신받는 데이터를 다루는 구간
class XR_event_handler:

    def OnReceiveRealData(self, code):

        if code == "JIF":  # 장운영정보
            jangubun = self.GetFieldData("OutBlock", "jangubun")
            jstatus = self.GetFieldData("OutBlock", "jstatus")

            print("jangubun: ", jangubun, "jstatus: ", jstatus)

            if jangubun == "1" and jstatus == "21":
                market_open = {"type": "Market_Open"}
                MyObjects.api_queue.put(market_open)

            if jangubun == "1" and jstatus == "31":
                market_close = {"type": "Market_Close"}
                MyObjects.api_queue.put(market_close)

        elif code == "K3_": # KOSDAQ 주식체결
            tick_data = {"type": "tick",
                         "code": self.GetFieldData("OutBlock", "shcode"),
                         "datetime": self.GetFieldData("OutBlock", "chetime"),
                         "current_price": int(self.GetFieldData("OutBlock", "price")),
                         "open": int(self.GetFieldData("OutBlock", "open")),
                         "high": int(self.GetFieldData("OutBlock", "high")),
                         "low": int(self.GetFieldData("OutBlock", "low")),
                         "volume": int(self.GetFieldData("OutBlock", "cvolume")),
                         "cum_volume": int(self.GetFieldData("OutBlock", "volume")),
                         "trade_sell_hoga1": int(self.GetFieldData("OutBlock", "offerho")),
                         "trade_buy_hoga1": int(self.GetFieldData("OutBlock", "bidho"))}

            MyObjects.api_queue.put(tick_data)

        elif code == "HA_": # KOSDAQ 주식 호가
            hoga_data = {"type": "hoga",
                         "code": self.GetFieldData("OutBlock", "shcode"),
                         "hogatime": int(self.GetFieldData("OutBlock", "hotime"))}
            for i in range(1,11):
                hoga_data["buy_hoga" + str(i)] = int(self.GetFieldData("OutBlock", "bidho" + str(i)))
                hoga_data["sell_hoga" + str(i)] = int(self.GetFieldData("OutBlock", "offerho" + str(i)))
                hoga_data["buy_hoga"+str(i)+"_stack"] = int(self.GetFieldData("OutBlock", "bidrem"+str(i)))
                hoga_data["sell_hoga"+str(i)+"_stack"] = int(self.GetFieldData("OutBlock", "offerrem"+str(i)))

            MyObjects.api_queue.put(hoga_data)

        elif code == "S3_": # KOSPI 주식체결
            tick_data = {"type": "tick",
                         "code": self.GetFieldData("OutBlock", "shcode"),
                         "datetime": self.GetFieldData("OutBlock", "chetime"),
                         "current_price": int(self.GetFieldData("OutBlock", "price")),
                         "open": int(self.GetFieldData("OutBlock", "open")),
                         "high": int(self.GetFieldData("OutBlock", "high")),
                         "low": int(self.GetFieldData("OutBlock", "low")),
                         "volume": int(self.GetFieldData("OutBlock", "cvolume")),
                         "cum_volume": int(self.GetFieldData("OutBlock", "volume")),
                         "trade_sell_hoga1": int(self.GetFieldData("OutBlock", "offerho")),
                         "trade_buy_hoga1": int(self.GetFieldData("OutBlock", "bidho"))}

            MyObjects.api_queue.put(tick_data)

        elif code == "H1_": # KOSPI 주식 호가
            hoga_data = {"type": "hoga",
                         "code": self.GetFieldData("OutBlock", "shcode"),
                         "hogatime": int(self.GetFieldData("OutBlock", "hotime"))}
            for i in range(1, 11):
                hoga_data["buy_hoga" + str(i)] = int(self.GetFieldData("OutBlock", "bidho" + str(i)))
                hoga_data["sell_hoga" + str(i)] = int(self.GetFieldData("OutBlock", "offerho" + str(i)))
                hoga_data["buy_hoga" + str(i) + "_stack"] = int(self.GetFieldData("OutBlock", "bidrem" + str(i)))
                hoga_data["sell_hoga" + str(i) + "_stack"] = int(self.GetFieldData("OutBlock", "offerrem" + str(i)))

            MyObjects.api_queue.put(hoga_data)

        elif code == "JC0": # 주식선물 체결
            tick_data = {"type": "tick", "code": self.GetFieldData("OutBlock", "futcode"),
                         "datetime": self.GetFieldData("OutBlock", "chetime"),
                         "current_price": int(self.GetFieldData("OutBlock", "price")),
                         "open": int(self.GetFieldData("OutBlock", "open")),
                         "high": int(self.GetFieldData("OutBlock", "high")),
                         "low": int(self.GetFieldData("OutBlock", "low")),
                         "volume": int(self.GetFieldData("OutBlock", "cvolume")),
                         "cum_volume": int(self.GetFieldData("OutBlock", "volume")),
                         "trade_sell_hoga1": int(self.GetFieldData("OutBlock", "offerho1")),
                         "trade_buy_hoga1": int(self.GetFieldData("OutBlock", "bidho1"))}

            MyObjects.api_queue.put(tick_data)

        elif code == "JH0": # 주식선물 호가
            hoga_data = {"type": "hoga",
                         "code": self.GetFieldData("OutBlock", "futcode"),
                         "hogatime": int(self.GetFieldData("OutBlock", "hotime"))}
            for i in range(1, 11):
                hoga_data["buy_hoga" + str(i)] = int(self.GetFieldData("OutBlock", "bidho" + str(i)))
                hoga_data["sell_hoga" + str(i)] = int(self.GetFieldData("OutBlock", "offerho" + str(i)))
                hoga_data["buy_hoga" + str(i) + "_stack"] = int(self.GetFieldData("OutBlock", "bidrem" + str(i)))
                hoga_data["sell_hoga" + str(i) + "_stack"] = int(self.GetFieldData("OutBlock", "offerrem" + str(i)))

            MyObjects.api_queue.put(hoga_data)


# TR 요청 이후 수신결과 데이터를 다루는 구간
class XQ_event_handler:

    def OnReceiveData(self, code):
        print("EbestAPI Data: %s 수신" % code, flush=True)

        if code == "t8436":
            MyObjects.code_list = []
            occurs_count = self.GetBlockCount("t8436OutBlock")
            for i in range(occurs_count):
                shcode = self.GetFieldData("t8436OutBlock", "shcode", i)
                MyObjects.code_list.append(shcode)

            print(occurs_count, "주식 종목 리스트: %s" % MyObjects.code_list, flush=True)
            MyObjects.tr_ok = True

        elif code == "t8401":  # 주식선물 종목코드
            occurs_count = self.GetBlockCount("t8401OutBlock")
            # print("주식선물 종목 갯수: %s" % occurs_count, flush=True)

            for i in range(occurs_count):
                shcode = self.GetFieldData("t8401OutBlock", "shcode", i)
                basecode = self.GetFieldData("t8401OutBlock", "basecode", i)
                MyObjects.stock_futures_code_list.append(shcode)

                # make dictionary
                MyObjects.stock_futures_basecode_dict[shcode] = basecode[1:]  # basecode 앞의 "A" 제거
                MyObjects.stock_futures_basecode_pickle[shcode[1:3]] = basecode[1:]

            ## stock_futures_basecode_pickle(as Dict) 업데이트
            with open('./strategies/stock_futures_basecode_idx.pickle', 'wb') as f:
                pickle.dump(MyObjects.stock_futures_basecode_pickle, f)
                print("stock_futures_basecode_pickle Saved..!")

            ### 최근월물/ 차근월물만 뽑아내는 종목리스트로 바꾸기 (추후 보완 ㄱ) ###
            fu_code_ls = list(set(map(lambda x: x[1:3], MyObjects.stock_futures_code_list)))

            total_fu_code = []
            for fu_code in fu_code_ls:
                fut_tmp = []
                for i in range(len(MyObjects.stock_futures_code_list)):
                    fu_code_i = MyObjects.stock_futures_code_list[i][1:3]
                    if fu_code_i == fu_code:
                        if MyObjects.stock_futures_code_list[i][0] == "1":  # 선물이면 종목코드의 첫자리가 1 이여야 함.
                            fut_tmp.append(MyObjects.stock_futures_code_list[i])
                    else:
                        pass
                total_fu_code.append(fut_tmp)

            total_fu_code = list(map(lambda x: x[:1], total_fu_code))  # 더 원월물까지 포함하고 싶으면 1을 바꾸면됨

            flatten_fu_code = []
            for fu_code in total_fu_code:
                flatten_fu_code = flatten_fu_code + fu_code

            MyObjects.stock_futures_code_list = flatten_fu_code  # 주식선물(근월물)만으로 filter된 stock_futures_code_list 생성

            basecode_by_dict = []
            for fu_code in MyObjects.stock_futures_code_list:
                basecode_by_dict.append(MyObjects.stock_futures_basecode_dict[fu_code])

            MyObjects.stock_futures_basecode_list = list(set(basecode_by_dict))  # 주식선물에 대한 base code list

            print(len(MyObjects.stock_futures_code_list), "주식선물 종목 리스트: %s" % MyObjects.stock_futures_code_list,
                  flush=True)
            print(len(MyObjects.stock_futures_basecode_list),
                  "주식선물 basecode: %s" % MyObjects.stock_futures_basecode_list)

            MyObjects.tr_ok = True

    def OnReceiveMessage(self, systemError, messageCode, message):
        print("systemError: %s, messageCode: %s, message: %s" % (systemError, messageCode, message))


# 서버접속 및 로그인 요청 이후 수신결과 데이터를 다루는 구간
class XS_event_handler:

    def OnLogin(self, szCode, szMsg):
        print("EbestAPI Data: %s %s" % (szCode, szMsg), flush=True)
        if szCode == "0000":
            MyObjects.login_ok = True
        else:
            MyObjects.login_ok = False


# 실행용 클래스
class Main:
    def __init__(self, api_queue, port_queue, order_queue, monitor_stocks):
        print("EbestAPI Data started")

        MyObjects.monitor_stocks = monitor_stocks
        MyObjects.api_queue = api_queue

        session = win32com.client.DispatchWithEvents("XA_Session.XASession", XS_event_handler)
        session.ConnectServer(MyObjects.server + ".ebestsec.co.kr", 20001)  # 서버 연결
        session.Login(MyObjects.credentials["ID"], MyObjects.credentials["PW"], MyObjects.credentials["gonin_PW"], 0,
                      False)  # 서버 연결

        while MyObjects.login_ok is False:
            pythoncom.PumpWaitingMessages()

        # TR: 주식 종목코드 가져오기
        for i in range(0, 3):
            MyObjects.tr_event = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", XQ_event_handler)
            MyObjects.tr_event.ResFileName = "C:/eBEST/xingAPI/Res/t8436.res"
            MyObjects.tr_event.SetFieldData("t8436InBlock", "gubun", 0, str(i))
            MyObjects.tr_event.Request(False)

            MyObjects.tr_ok = False
            while MyObjects.tr_ok is False:
                pythoncom.PumpWaitingMessages()

            if i == 0:
                MyObjects.stock_total_code_list = MyObjects.code_list
                time.sleep(1)
            elif i == 1:
                MyObjects.stock_KOSPI_code_list = MyObjects.code_list
                time.sleep(1)
            elif i == 2:
                MyObjects.stock_KOSDAQ_code_list = MyObjects.code_list
                time.sleep(1)

        # TR: 주식선물 종목코드 가져오기
        MyObjects.tr_event = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", XQ_event_handler)

        MyObjects.tr_event.ResFileName = "C:/eBEST/xingAPI/Res/t8401.res"
        MyObjects.tr_event.SetFieldData("t8401InBlock", "dummy", 0, "")
        MyObjects.tr_event.Request(False)

        MyObjects.tr_ok = False
        while MyObjects.tr_ok is False:
            pythoncom.PumpWaitingMessages()

        # ############For Test################
        # MyObjects.stock_code_list = ["005930", "096530"]
        # MyObjects.stock_futures_code_list = ["111R2000", "1CLR2000"]
        # MyObjects.stock_futures_basecode_list = ["005930", "096530"]
        # MyObjects.whole_universe_code_list = MyObjects.stock_futures_code_list + MyObjects.stock_futures_basecode_list
        # ####################################

        print(MyObjects.monitor_stocks)

        # 장운영정보
        MyObjects.real_event_market = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", XR_event_handler)
        MyObjects.real_event_market.ResFileName = "C:/eBEST/xingAPI/Res/JIF.res"
        MyObjects.real_event_market.SetFieldData("InBlock", "jangubun", '0')
        MyObjects.real_event_market.AdviseRealData()

        # KOSPI
        MyObjects.real_event_KOSPI = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", XR_event_handler)
        MyObjects.real_event_KOSPI.ResFileName = "C:/eBEST/xingAPI/Res/S3_.res"
        for shcode in MyObjects.monitor_stocks:  # 주식선물의 기초자산 종목만 등록!
            if shcode in MyObjects.stock_KOSPI_code_list:
                print("KOSPI 주식 체결 종목 등록 %s" % shcode)
                MyObjects.real_event_KOSPI.SetFieldData("InBlock", "shcode", shcode)
                MyObjects.real_event_KOSPI.AdviseRealData()

        MyObjects.real_event_KOSPI_hoga = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", XR_event_handler)
        MyObjects.real_event_KOSPI_hoga.ResFileName = "C:/eBEST/xingAPI/Res/H1_.res"
        for shcode in MyObjects.monitor_stocks:  # 주식선물의 기초자산 종목만 등록!
            if shcode in MyObjects.stock_KOSPI_code_list:
                print("KOSPI 주식 호가잔량 종목 등록 %s" % shcode)
                MyObjects.real_event_KOSPI_hoga.SetFieldData("InBlock", "shcode", shcode)
                MyObjects.real_event_KOSPI_hoga.AdviseRealData()

        # KOSDAQ
        MyObjects.real_event_KOSDAQ = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", XR_event_handler)
        MyObjects.real_event_KOSDAQ.ResFileName = "C:/eBEST/xingAPI/Res/K3_.res"
        for shcode in MyObjects.monitor_stocks:  # 주식선물의 기초자산 종목만 등록!
            if shcode in MyObjects.stock_KOSDAQ_code_list:
                print("KOSDAQ 주식 체결 종목 등록 %s" % shcode)
                MyObjects.real_event_KOSDAQ.SetFieldData("InBlock", "shcode", shcode)
                MyObjects.real_event_KOSDAQ.AdviseRealData()

        MyObjects.real_event_KOSDAQ_hoga = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", XR_event_handler)
        MyObjects.real_event_KOSDAQ_hoga.ResFileName = "C:/eBEST/xingAPI/Res/HA_.res"
        for shcode in MyObjects.monitor_stocks:  # 주식선물의 기초자산 종목만 등록!
            if shcode in MyObjects.stock_KOSDAQ_code_list:
                print("KOSDAQ 주식 호가잔량 종목 등록 %s" % shcode)
                MyObjects.real_event_KOSDAQ_hoga.SetFieldData("InBlock", "shcode", shcode)
                MyObjects.real_event_KOSDAQ_hoga.AdviseRealData()

        # 주식선물
        MyObjects.real_event_fu = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", XR_event_handler)
        MyObjects.real_event_fu.ResFileName = "C:/eBEST/xingAPI/Res/JC0.res"
        for futcode in MyObjects.monitor_stocks:
            if futcode in MyObjects.stock_futures_code_list:
                print("주식선물 체결 종목 등록 %s" % futcode)
                MyObjects.real_event_fu.SetFieldData("InBlock", "futcode", futcode)
                MyObjects.real_event_fu.AdviseRealData()

        MyObjects.real_event_fu_hoga = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", XR_event_handler)
        MyObjects.real_event_fu_hoga.ResFileName = "C:/eBEST/xingAPI/Res/JH0.res"
        for futcode in MyObjects.monitor_stocks:
            if futcode in MyObjects.stock_futures_code_list:
                print("주식선물 호가잔량 종목 등록 %s" % futcode)
                MyObjects.real_event_fu_hoga.SetFieldData("InBlock", "futcode", futcode)
                MyObjects.real_event_fu_hoga.AdviseRealData()

        while MyObjects.real_ok is False:
            pythoncom.PumpWaitingMessages()


if __name__ == "__main__":
    Main()
