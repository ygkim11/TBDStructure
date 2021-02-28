import datetime
import numpy as np
import pandas as pd
import time

from roboticks.strategy import Strategy
from roboticks.event import PairSignalEvent


class StockFuturesArbitrage(Strategy):
    """
    Carries out Arbitrage trading on korean stock futures
    """

    def __init__(self, data_queue, port_queue, order_queue, strategy_name, strategy_universe, monitor_stocks,
                 sec_mem_name, sec_mem_shape, sec_mem_dtype, source):
        print('StockFuturesArbitrage started')
        super().__init__(data_queue, port_queue, order_queue, strategy_universe, monitor_stocks,
                         sec_mem_name, sec_mem_shape, sec_mem_dtype, source)

        self.strategy_name = strategy_name
        self.stock_futures_dict = pd.read_pickle("./strategies/stock_futures_basecode_idx.pickle")
        self.bought = self._initial_bought_dict()
        self.expiration_datetime = self.calc_expiration_dateime()
        self.pair_dict = self._init_pairs_dict()
        self.today_str = datetime.datetime.now().strftime("%Y-%m-%d")

        # 최대 보유 Pair 개수 (Hard Coded)
        self.slot_cnt = 1

    def _initial_bought_dict(self):
        """
        Adds keys to the bought dict for all symbols and initially set them to "OUT"
        :return:
        """
        bought = {}
        while True:
            time.sleep(1)
            try:
                init_pos = pd.read_csv("./strategies/sf_arbit_2021-03-01_initial_position.csv", index_col=0)["sf_arbit"]
                print(init_pos)
            except:
                print("Initial Position 생성중.. @ stock_fut_arbit")
                continue

            for i in range(len(init_pos)):
                val = init_pos.iloc[i]
                if val == 0:
                    init_pos.iloc[i] = "OUT"
                elif val > 0:
                    init_pos.iloc[i] = "LONG"
                elif val < 0:
                    init_pos.iloc[i] = "SHORT"
                else:
                    raise Exception("Init Pos @ stock_fut_arbit")

            bought = init_pos.to_dict()
            print("Bought_Dict: ", bought)
            break

        return bought

    def _init_pairs_dict(self):
        pair_dict = {}
        for i in self.strategy_universe:
            if len(i) == 8:
                pair_dict[i] = self.stock_futures_dict[i[1:3]]
        return pair_dict

    # 만기일 수동 관리가 제일 나을듯 (대체휴무일 지정시 만기일 밀림)
    def calc_expiration_dateime(self):  # format: "%Y-%m-%d"
        fut_ex_dates = pd.read_csv("./strategies/futures_expirations.csv", header=None).values.reshape(-1)
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        ex_date = fut_ex_dates[fut_ex_dates >= today][0]
        print("주식선물 만기일: ", ex_date)
        return ex_date

    def calc_signal_for_pairs(self):
        """
        generates signal based on pct_basis of stock futures
        :return:
        """
        bought_ls = list(self.bought.values())

        long_cnt = sum([x == 'LONG' for x in bought_ls])
        short_cnt = sum([x == 'SHORT' for x in bought_ls])

        # Slot 한도 정하기(최대로 보유할 Pair 개수)
        if long_cnt == short_cnt: # 현재 Bought_Dict 정합성 검증
            if long_cnt < self.slot_cnt:
                pass
            else:
                print("SLOT FULL!! @ sf_arbit")
                return
        else:
            raise Exception("LONG SHORT Count 다름! @ sf_arbit")

        # Signal_calc
        for k, v in self.pair_dict.items():
            s_code = v
            sf_code = k
            bar_date = self.get_latest_bar_datetime(self.sec_mem_array, s_code, self.SYMBOL_TABLE)

            if self.bought[s_code] == "OUT" and self.bought[sf_code] == "OUT":
                s_ask = self.get_latest_bar_value(self.sec_mem_array, s_code, self.SYMBOL_TABLE, "sell_hoga1")  # 주식
                sf_bid = self.get_latest_bar_value(self.sec_mem_array, sf_code, self.SYMBOL_TABLE, "buy_hoga1")  # 주식선물
                entry_spread = (sf_bid / s_ask) - 1

                if entry_spread >= 0.001:
                    print("ENTRY LONG: %s and SHORT: %s at %2f at %s" % (s_code, sf_code, entry_spread, bar_date))
                    signal = PairSignalEvent("sf_arbit", s_code, sf_code, bar_date, "ENTRY", 1.0, s_ask, sf_bid)
                    self.port_queue.put(signal)
                    self.bought[s_code] = "LONG"
                    self.bought[sf_code] = "SHORT"
                else:
                    pass

            elif self.bought[s_code] != "OUT" and self.bought[sf_code] != "OUT":
                s_bid = self.get_latest_bar_value(self.sec_mem_array, s_code, self.SYMBOL_TABLE, "buy_hoga1")  # 주식
                sf_ask = self.get_latest_bar_value(self.sec_mem_array, sf_code, self.SYMBOL_TABLE, "sell_hoga1")  # 주식선물
                exit_spread = (sf_ask / s_bid) - 1

                if self.today_str == self.expiration_datetime:  # 만기일 3시까지 Backwardation 미발생시 강제청산/ 실제 트레이딩시에는 그냥 놔두면 현금정산 될듯.
                    if int(datetime.datetime.now().strftime("%H%M")) > int("0300"):  # 만기일 3시 지나면 청산
                        print("만기일 EXIT SHORT: %s and LONG: %s at %2f at %s" % (s_code, sf_code, exit_spread, bar_date))
                        signal = PairSignalEvent("sf_arbit", sf_code, s_code, bar_date, "EXIT", 1.0, sf_ask, s_bid)
                        self.port_queue.put(signal)
                        self.bought[s_code] = "OUT"
                        self.bought[sf_code] = "OUT"
                    else:
                        if exit_spread <= -0.011:
                            print("EXIT SHORT: %s and LONG: %s at %2f at %s" % (s_code, sf_code, exit_spread, bar_date))
                            signal = PairSignalEvent("sf_arbit", sf_code, s_code, bar_date, "EXIT", 1.0, sf_ask, s_bid)
                            self.port_queue.put(signal)
                            self.bought[s_code] = "OUT"
                            self.bought[sf_code] = "OUT"

                else:
                    if exit_spread <= -0.011:
                        print("EXIT SHORT: %s and LONG: %s at %2f at %s" % (s_code, sf_code, exit_spread, bar_date))
                        signal = PairSignalEvent("sf_arbit", sf_code, s_code, bar_date, "EXIT", 1.0, sf_ask, s_bid)
                        self.port_queue.put(signal)
                        self.bought[s_code] = "OUT"
                        self.bought[sf_code] = "OUT"

            else:
                print("Bought dict LONG/SHORT status error: Both pairs should have same Bought position")

    def calc_signals(self):
        """
        generates signal based on pct_basis of stock futures
        """
        while True:
            market = self.data_queue.get()
            self.calc_signal_for_pairs()