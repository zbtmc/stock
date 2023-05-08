#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os.path
import datetime
import numpy as np
import pandas as pd
import akshare as ak
import talib as tl
import instock.core.tablestructure as tbs
import instock.lib.trade_time as trd
import instock.core.crawling.stock_hist_em_my as akm

__author__ = 'myh '
__date__ = '2023/3/10 '

# 设置基础目录，每次加载使用。
cpath_current = os.path.dirname(os.path.dirname(__file__))
stock_hist_cache_path = os.path.join(cpath_current, 'cache', 'hist')
if not os.path.exists(stock_hist_cache_path):
    os.makedirs(stock_hist_cache_path)  # 创建多个文件夹结构。


# 600 601 603 605开头的股票是上证A股
# 600开头的股票是上证A股，属于大盘股，其中6006开头的股票是最早上市的股票，
# 6016开头的股票为大盘蓝筹股；900开头的股票是上证B股；
# 688开头的是上证科创板股票；
# 000开头的股票是深证A股，001、002开头的股票也都属于深证A股，
# 其中002开头的股票是深证A股中小企业股票；
# 200开头的股票是深证B股；
# 300、301开头的股票是创业板股票；400开头的股票是三板市场股票。
# 430、83、87开头的股票是北证A股
def is_a_stock(code):
    # 上证A股  # 深证A股
    return code.startswith(('600', '601', '603', '605', '000', '001', '002', '300', '301'))


# 过滤掉 st 股票。
def is_not_st(name):
    return not name.startswith(('*ST', 'ST'))


# 过滤价格，如果没有基本上是退市了。
def is_open(latest_price):
    return not np.isnan(latest_price)


# 读取股票交易日历数据
def fetch_stocks_trade_date():
    try:
        data = ak.tool_trade_date_hist_sina()
        if data is None or len(data.index) == 0:
            return None
        data_date = set(data['trade_date'].values.tolist())
        return data_date
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks_trade_date处理异常：{e}")
    return None


# 读取当天股票数据
def fetch_etfs(date):
    try:
        data = ak.fund_etf_spot_em()
        if data is None or len(data.index) == 0:
            return None
        columns = list(tbs.TABLE_CN_ETF_SPOT['columns'])
        columns.pop(0)
        data.columns = columns
        data = data.loc[data['latest_price'].apply(is_open)]
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))

        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_etfs处理异常：{e}")
    return None


# 读取当天股票数据
def fetch_stocks(date):
    try:
        data = ak.stock_zh_a_spot_em()
        if data is None or len(data.index) == 0:
            return None
        columns = list(tbs.TABLE_CN_STOCK_SPOT['columns'])
        columns[0] = 'index'
        data.columns = columns
        data = data.loc[data['code'].apply(is_a_stock)].loc[data['latest_price'].apply(is_open)]
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))

        # 删除index
        data.drop('index', axis=1, inplace=True)
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks处理异常：{e}")
    return None


# 读取股票交易日历数据
def fetch_stocks_fundamentals(date):
    try:
        data = akm.stock_zh_a_spot_em()
        if data is None or len(data.index) == 0:
            return None
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        data.columns = list(tbs.TABLE_CN_STOCK_FUNDAMENTALS['columns'])
        data = data.loc[data['code'].apply(is_a_stock)].loc[data['latest_price'].apply(is_open)]
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks_fundamentals：{e}")
    return None


# 股票近三月上龙虎榜且必须有2次以上机构参与的
def fetch_stock_top_entity_data(date):
    run_date = date + datetime.timedelta(days=-90)
    start_date = run_date.strftime("%Y%m%d")
    end_date = date.strftime("%Y%m%d")
    code_name = '代码'
    entity_amount_name = '买方机构数'
    try:
        data = ak.stock_lhb_jgmmtj_em(start_date, end_date)
        if data is None or len(data.index) == 0:
            return None

        # 机构买入次数大于1计算方法，首先：每次要有买方机构数(>0),然后：这段时间买方机构数求和大于1
        mask = (data[entity_amount_name] > 0)  # 首先：每次要有买方机构数(>0)
        data = data.loc[mask]

        if len(data.index) == 0:
            return None

        grouped = data.groupby(by=data[code_name])
        data_series = grouped[entity_amount_name].sum()
        data_code = set(data_series[data_series > 1].index.values)  # 然后：这段时间买方机构数求和大于1

        if not data_code:
            return None

        return data_code
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_top_entity_data处理异常：{e}")
    return None


# 描述: 获取新浪财经-龙虎榜-个股上榜统计
def fetch_stock_top_data(date):
    try:
        data = ak.stock_lhb_ggtj_sina(recent_day="5")
        if data is None or len(data.index) == 0:
            return None
        _columns = list(tbs.TABLE_CN_STOCK_TOP['columns'])
        _columns.pop(0)
        data.columns = _columns
        data = data.loc[data['code'].apply(is_a_stock)]
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_top_data处理异常：{e}")
    return None


# 描述: 获取东方财富网-数据中心-大宗交易-每日统计
def fetch_stock_blocktrade_data(date):
    date_str = date.strftime("%Y%m%d")
    try:
        data = ak.stock_dzjy_mrtj(start_date=date_str, end_date=date_str)
        if data is None or len(data.index) == 0:
            return None

        columns = list(tbs.TABLE_CN_STOCK_BLOCKTRADE['columns'])
        columns.insert(0, 'index')
        data.columns = columns
        data = data.loc[data['code'].apply(is_a_stock)]
        data.drop('index', axis=1, inplace=True)
        return data
    except TypeError:
        logging.error("处理异常：目前还没有大宗交易数据，请17:00点后再获取！")
        return None
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_blocktrade_data处理异常：{e}")
    return None


# 读取股票历史数据
def fetch_etf_hist(data_base, date_start=None, date_end=None, adjust='qfq'):
    date = data_base[0]
    code = data_base[1]

    if date_start is None:
        date_start, is_cache = trd.get_trade_hist_interval(date)  # 提高运行效率，只运行一次
    try:
        if date_end is not None:
            data = ak.fund_etf_hist_em(symbol=code, period="daily", start_date=date_start, end_date=date_end,
                                       adjust=adjust)
        else:
            data = ak.fund_etf_hist_em(symbol=code, period="daily", start_date=date_start, adjust=adjust)

        if data is None or len(data.index) == 0:
            return None
        data.columns = tuple(tbs.CN_STOCK_HIST_DATA['columns'])
        data = data.sort_index()  # 将数据按照日期排序下。
        if data is not None:
            data.loc[:, 'p_change'] = tl.ROC(data['close'].values, 1)
            data["volume"] = data['volume'].values.astype('double') * 100  # 成交量单位从手变成股。
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_etf_hist处理异常：{e}")
    return None


# 读取股票历史数据
def fetch_stock_hist(data_base, date_start=None, is_cache=True):
    date = data_base[0]
    code = data_base[1]

    if date_start is None:
        date_start, is_cache = trd.get_trade_hist_interval(date)  # 提高运行效率，只运行一次
        # date_end = date_end.strftime("%Y%m%d")
    try:
        data = stock_hist_cache(code, date_start, None, is_cache, 'qfq')
        if data is not None:
            data.loc[:, 'p_change'] = tl.ROC(data['close'].values, 1)
            data["volume"] = data['volume'].values.astype('double') * 100  # 成交量单位从手变成股。
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_hist处理异常：{e}")
    return None


# 增加读取股票缓存方法。加快处理速度。多线程解决效率
def stock_hist_cache(code, date_start, date_end=None, is_cache=True, adjust=''):
    cache_dir = os.path.join(stock_hist_cache_path, date_start[0:6], date_start)
    # 如果没有文件夹创建一个。月文件夹和日文件夹。方便删除。
    try:
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    except Exception:
        pass
    cache_file = os.path.join(cache_dir, "%s%s.gzip.pickle" % (code, adjust))
    # 如果缓存存在就直接返回缓存数据。压缩方式。
    try:
        if os.path.isfile(cache_file):
            return pd.read_pickle(cache_file, compression="gzip")
        else:
            if date_end is not None:
                stock = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=date_start, end_date=date_end,
                                           adjust=adjust)
            else:
                stock = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=date_start, adjust=adjust)

            if stock is None or len(stock.index) == 0:
                return None
            stock.columns = tuple(tbs.CN_STOCK_HIST_DATA['columns'])
            stock = stock.sort_index()  # 将数据按照日期排序下。
            try:
                if is_cache:
                    stock.to_pickle(cache_file, compression="gzip")
            except Exception:
                pass
            # time.sleep(1)
            return stock
    except Exception as e:
        logging.error(f"stockfetch.stock_hist_cache处理异常：{code}代码{e}")
    return None
