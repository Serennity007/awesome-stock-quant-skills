from typing import List, Optional, Dict, Any

import define
import requests
from define import AppVersion,TokenCheckResult
import config
class PatchItem:
    def __init__(self):
        self.patch_date:str = ""
        self.patch_name:str = ""
        self.version:int = int

def request_patch_list() -> List[PatchItem]:
    """
    获取所有表的patch列表
    返回json说明：
        key: 表名
        value: 所有可用patch列表
    """
    ret: List[PatchItem] = []
    response = requests.get(f"{define.BASE_URL}/api/patch_list/all")
    if response.status_code == 200:
        rsp = response.json()
        datas_json = rsp["data"]
        for data_json in datas_json:
            item: PatchItem = PatchItem()
            item.patch_name = data_json["patch_name"]
            item.patch_date = data_json["patch_date"]
            item.version = int(float(data_json["version"]) * 10)
            ret.append(item)
    return ret


def request_decrypt_key(file_name:str, token_key:str) -> str:
    url = f"{define.BASE_URL}/api/get_decryption_key"
    params = {
        "file_name": file_name,
        "token_key": token_key
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            key = data.get("key")
            return key
        else:
            return ""
    except Exception as e:
        return ""

def request_download_url(file_name: str, token_key: str) -> str:
    """
    获取文件的下载链接。

    参数:
        file_name:  文件名（如 data_1.0.bin）
        token_key: API 访问令牌

    返回:
        str: 下载链接，失败返回空字符串
    """
    url = f"{define.BASE_URL}/api/download_file"
    params = {
        "file_name": file_name,
        "token_key": token_key
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            download_url = data.get("download_url", "")
            return download_url
        else:
            return ""
    except Exception as e:
        print(f"request_download_url error: {e}")
        return ""

def request_version() -> AppVersion:
    url = f"{define.BASE_URL}/api/get_latest_version"
    try:
        params = {
            "token": config.get_token()
        }
        response = requests.post(url, json=params)
        if response.status_code == 200:
            data = response.json()
            ver = AppVersion.from_dict(data)
            return ver
        else:
            return None
    except Exception as e:
        print(e)
        return None

def request_check_token(token:str) -> TokenCheckResult:
    url = f"{define.BASE_URL}/api/check_token"
    params = {
            "token": token
        }
    try:
        response = requests.post(url, json=params)
        data = response.json()
        return TokenCheckResult.from_dict(data)
    except Exception as e:
        print(e)
        return TokenCheckResult.from_dict({"status": "failure", "message": str(e)})


def request_get_benchmark(token: str) -> Optional[Dict[str, float]]:
    """
    获取服务器配置的基准线阈值。
    返回 dict，包含 total_yield / annualized_yield / max_drawdown / sharpe_ratio；
    失败（token无效、网络错误）返回 None。
    """
    url = f"{define.BASE_URL}/api/get_benchmark"
    try:
        response = requests.post(url, json={"token": token}, timeout=define.HTTP_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"get_benchmark failed: {response.status_code} {response.text}")
            return None
    except Exception as e:
        print(f"get_benchmark error: {e}")
        return None


class SubmitYieldResult:
    """提交收益数据的结果"""

    def __init__(self, success: bool, message: str, details: Optional[List[str]] = None):
        self.success = success
        self.message = message
        self.details = details or []

    def __repr__(self) -> str:
        return f"SubmitYieldResult(success={self.success!r}, message={self.message!r}, details={self.details!r})"


def request_submit_yield(
    token: str,
    total_yield: float,
    annualized_yield: float,
    max_drawdown: float,
    sharpe_ratio: float,
    positions: Any = None,
) -> SubmitYieldResult:
    """
    提交收益数据到排行榜。
    服务器仅强制校验 total_yield 是否超过配置基准线，其余指标不做强制要求。

    成功返回 SubmitYieldResult(success=True)；
    失败返回 SubmitYieldResult(success=False, message=..., details=...)。
    """
    url = f"{define.BASE_URL}/api/submit_yield"
    yield_data = {
        "total_yield": total_yield,
        "annualized_yield": annualized_yield,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "positions": positions if positions is not None else [],
    }
    body = {
        "token": token,
        "data": yield_data,
    }
    try:
        response = requests.post(url, json=body, timeout=define.HTTP_TIMEOUT)
        data = response.json()
        if response.status_code == 200 and data.get("status") == "ok":
            return SubmitYieldResult(success=True, message="提交成功")
        else:
            msg = data.get("message", f"HTTP {response.status_code}")
            details = data.get("details", [])
            return SubmitYieldResult(success=False, message=msg, details=details)
    except Exception as e:
        return SubmitYieldResult(success=False, message=str(e))


if __name__ == "__main__":
    _token = "8ACw626fHId31d3OWwVE62yzGkA7p9vCyg1kIV9AKSiU"

    print("=== check_token ===")
    check_result = request_check_token(_token)
    print(check_result)

    print("\n=== get_benchmark ===")
    bm = request_get_benchmark(_token)
    print(bm)

    print("\n=== submit_yield (应该被基准线拒绝) ===")
    r1 = request_submit_yield(_token, total_yield=0.01, annualized_yield=0.05,
                               max_drawdown=-0.10, sharpe_ratio=0.8)
    print(r1)

    print("\n=== submit_yield (超过基准线，应该成功) ===")
    r2 = request_submit_yield(_token, total_yield=0.50, annualized_yield=0.35,
                               max_drawdown=-0.08, sharpe_ratio=2.1,
                               positions=[{"code": "000001.SZ", "weight": 1.0}])
    print(r2)
