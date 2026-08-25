import requests
import time
import json
import random
import re
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass


@dataclass
class RealtimeStockQuote:
    """
    实时股票报价信息
    """
    ts_code: str             # 股票代码（如 000001.SZ）
    name: str                # 股票名称
    open: float              # 今日开盘价
    pre_close: float         # 昨日收盘价
    price: float             # 当前最新价
    high: float              # 今日最高价
    low: float               # 今日最低价
    bid: float               # 买一价
    ask: float               # 卖一价
    volume: int              # 成交量（股）
    amount: float            # 成交额（元）
    date: str                # 交易日期（YYYY-MM-DD）
    time: str                # 最新报价时间（HH:MM:SS）
    amplitude: float         # 振幅（%）
    turnover_rate: Optional[float]  # 换手率（%），可能为空
    total_cap: Optional[float]      # 总市值（元），可能为空
    circ_cap: Optional[float]       # 流通市值（元），可能为空
    pb: Optional[float]             # 市净率，可能为空
    pe_ttm: Optional[float]         # 市盈率（TTM），可能为空
    total_shares: Optional[float]   # 总股本（股），可能为空
    circ_shares: Optional[float]    # 流通股本（股），可能为空
    status: str              # 请求状态（success / error）

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RealtimeStockQuote":
        return cls(**data)

class StockCrawler:
    """
    StockCrawler provides interfaces to fetch real-time stock data from multiple sources:
    - Sina Finance (新浪财经)
    - East Money (东方财富)
    - Tonghuashun (同花顺)
    
    It handles rate limiting to avoid IP bans and standardizes the output format.
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.last_request_time = {}
        self.min_interval = 1.0  # Minimum interval between requests in seconds per source

    def _wait_for_rate_limit(self, source: str):
        current_time = time.time()
        last_time = self.last_request_time.get(source, 0)
        elapsed = current_time - last_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time[source] = time.time()

    def _convert_to_sina_symbol(self, ts_code: str) -> str:
        # 000001.SZ -> sz000001
        # 600519.SH -> sh600519
        code, market = ts_code.split('.')
        return f"{market.lower()}{code}"

    def _convert_to_eastmoney_secid(self, ts_code: str) -> str:
        # 000001.SZ -> 0.000001
        # 600519.SH -> 1.600519
        code, market = ts_code.split('.')
        if market == 'SH':
            return f"1.{code}"
        else:
            return f"0.{code}"

    def _convert_to_tonghuashun_code(self, ts_code: str) -> str:
        # 000001.SZ -> 000001
        # 600519.SH -> 600519
        return ts_code.split('.')[0]

    def fetch_sina(self, ts_code: str) -> Optional[RealtimeStockQuote]:
        """
        Fetch real-time data from Sina Finance.
        URL: http://hq.sinajs.cn/list={symbol}
        """
        self._wait_for_rate_limit('sina')
        symbol = self._convert_to_sina_symbol(ts_code)
        url = f"http://hq.sinajs.cn/list={symbol}"
        headers = self.headers.copy()
        headers['Referer'] = 'https://finance.sina.com.cn/'
        try:
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            # Format: var hq_str_sh601006="大秦铁路, 27.55, 27.25, 26.91, 27.55, 26.20, 26.91, 26.92, ...";
            content = response.text
            print(content)
            match = re.search(r'="(.*)";', content)
            if match:
                data_str = match.group(1)
                parts = data_str.split(',')
                if len(parts) > 30:
                    pre_close = float(parts[2])
                    high = float(parts[4])
                    low = float(parts[5])
                    amplitude = 0.0
                    if pre_close > 0:
                        amplitude = (high - low) / pre_close * 100

                    return RealtimeStockQuote(
                        ts_code=ts_code,
                        name=parts[0],
                        open=float(parts[1]),
                        pre_close=pre_close,
                        price=float(parts[3]),
                        high=high,
                        low=low,
                        bid=float(parts[6]),
                        ask=float(parts[7]),
                        volume=int(parts[8]),  # Sina returns shares
                        amount=float(parts[9]),
                        date=parts[30],
                        time=parts[31],
                        amplitude=round(amplitude, 2),
                        turnover_rate=None,
                        total_cap=None,
                        circ_cap=None,
                        pb=None,
                        pe_ttm=None,
                        total_shares=None,
                        circ_shares=None,
                        status="success"
                    )
            return None
        except Exception:
            return None

    def fetch_eastmoney(self, ts_code: str) -> Dict[str, Any]:
        """
        Fetch real-time data from East Money.
        """
        self._wait_for_rate_limit('eastmoney')
        secid = self._convert_to_eastmoney_secid(ts_code)
        url = "http://push2.eastmoney.com/api/qt/stock/get"
        # f43:price, f44:high, f45:low, f46:open, f47:volume, f48:amount, f57:code, f58:name, f60:pre_close, f168:turnover, f170:change_pct
        params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f60,f116,f117,f162,f167,f168,f169,f170,f7,f84,f85",
            "invt": "2",
            "fltt": "2",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b"
        }
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data and data.get("data"):
                d = data["data"]
                # EastMoney volume is in 'shou' (100 shares), convert to shares
                volume = d.get("f47")
                if volume is not None:
                    volume = float(volume) * 100
                
                # Calculate amplitude if not provided
                amplitude = d.get("f7")
                if amplitude is None:
                    try:
                        high = float(d.get("f44"))
                        low = float(d.get("f45"))
                        pre_close = float(d.get("f60"))
                        if pre_close > 0:
                            amplitude = (high - low) / pre_close * 100
                            amplitude = round(amplitude, 2)
                    except (TypeError, ValueError):
                        amplitude = None

                return {
                    "source": "eastmoney",
                    "ts_code": ts_code,
                    "name": d.get("f58"),
                    "price": d.get("f43"),
                    "high": d.get("f44"),
                    "low": d.get("f45"),
                    "open": d.get("f46"),
                    "pre_close": d.get("f60"),
                    "volume": volume,
                    "amount": d.get("f48"),
                    "turnover_rate": d.get("f168"),
                    "change_pct": d.get("f170"),
                    "change_amount": d.get("f169"),
                    "pe_ttm": d.get("f162"),
                    "pb": d.get("f167"),
                    "total_cap": d.get("f116"),
                    "circ_cap": d.get("f117"),
                    "amplitude": amplitude,
                    "total_shares": d.get("f84"),
                    "circ_shares": d.get("f85"),
                    "status": "success"
                }
            return {"source": "eastmoney", "ts_code": ts_code, "status": "failed", "message": "No data"}
        except Exception as e:
            return {"source": "eastmoney", "ts_code": ts_code, "status": "failed", "message": str(e)}

    def fetch_tonghuashun(self, ts_code: str) -> Dict[str, Any]:
        """
        Fetch data from Tonghuashun (10jqka).
        Using the 'last.js' endpoint which provides the latest kline data.
        Note: This returns daily K-line data, which might be the latest available trading day.
        """
        self._wait_for_rate_limit('tonghuashun')
        code = self._convert_to_tonghuashun_code(ts_code)
        
        url = f"http://d.10jqka.com.cn/v6/line/hs_{code}/01/last.js"
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            content = response.text
            # content format: quotebridge_v6_line_hs_000001_01_last({"rt":"...","data":"date,open,high,low,close,vol,amt,..."})
            match = re.search(r'\((.*)\)', content)
            if match:
                json_str = match.group(1)
                d = json.loads(json_str)
                data_str = d.get("data", "")
                if data_str:
                    lines = data_str.split(';')
                    if lines:
                        latest = lines[-1].split(',')
                        if len(latest) >= 7:
                            # Format: Date, Open, High, Low, Close, Volume, Amount, Turnover...
                            return {
                                "source": "tonghuashun",
                                "ts_code": ts_code,
                                "date": latest[0],
                                "open": float(latest[1]),
                                "high": float(latest[2]),
                                "low": float(latest[3]),
                                "price": float(latest[4]),
                                "volume": float(latest[5]), # Volume is likely in shares for kline data
                                "amount": float(latest[6]),
                                "turnover_rate": float(latest[7]) if len(latest) > 7 and latest[7] else None,
                                "pre_close": None, # Needs calculation from previous day or another source
                                "amplitude": None, # Needs pre_close
                                "total_cap": None,
                                "circ_cap": None,
                                "pb": None,
                                "pe_ttm": None,
                                "total_shares": None,
                                "circ_shares": None,
                                "status": "success"
                            }
            return {"source": "tonghuashun", "ts_code": ts_code, "status": "failed", "message": "Parse error or no data"}
        except Exception as e:
            return {"source": "tonghuashun", "ts_code": ts_code, "status": "failed", "message": str(e)}

    def fetch(self, ts_code: str, source: str = 'sina') -> Dict[str, Any]:
        """
        Fetch stock data from specified source.
        
        Args:
            ts_code (str): Stock code (e.g., '000001.SZ')
            source (str): Source name ('sina', 'eastmoney', 'tonghuashun')
            
        Returns:
            Dict: Stock data
        """
        if source == 'sina':
            return self.fetch_sina(ts_code)
        elif source == 'eastmoney':
            return self.fetch_eastmoney(ts_code)
        elif source == 'tonghuashun':
            return self.fetch_tonghuashun(ts_code)
        else:
            # Default to sina if unknown
            return self.fetch_sina(ts_code)

if __name__ == "__main__":
    crawler = StockCrawler()
    # Test examples
    print(crawler.fetch("000001.SZ", "sina"))
    # print(crawler.fetch("600519.SH", "eastmoney"))
    # print(crawler.fetch("000001.SZ", "tonghuashun"))
