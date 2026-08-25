import tempfile
import zipfile
import os
import shutil
import requests

def get_skill_work_dir():
    """获取/创建skill专属的自定义临时目录"""
    # 1. 获取系统临时目录路径（原生方法，跨平台）
    system_temp_dir = tempfile.gettempdir()
    # 2. 创建skill专属子目录（命名如：BitSoulStockSkill）
    skill_temp_dir = os.path.join(system_temp_dir, "BitSoulStockSkill")
    
    # 目录不存在则创建
    if not os.path.exists(skill_temp_dir):
        os.makedirs(skill_temp_dir, exist_ok=True)
    return skill_temp_dir

def get_skill_dir():
    current_file_path = os.path.abspath(__file__)
    dir = os.path.dirname(os.path.dirname(current_file_path))
    return dir

def get_skill_assets_dir():
    return os.path.join(get_skill_dir(), "assets")

def scan_files_in_dir(dir:str):
    file_list = []
    # scandir 返回可迭代的 DirEntry 对象，包含文件信息
    with os.scandir(dir) as entries:
        for entry in entries:
            # is_file(follow_symlinks=False)：排除符号链接，仅判断真实文件
            if entry.is_file(follow_symlinks=False):
                file_list.append(entry.path)  # entry.path 直接返回完整路径
    return file_list

def unzip_file(zip_file_path, target_dir):
    """
    将zip文件解压到指定目录
    
    Args:
        zip_file_path (str): zip压缩文件的路径
        target_dir (str): 解压目标目录
    
    Returns:
        bool: 解压成功返回True，失败返回False
    """
    # 确保目标目录存在，如果不存在则创建
    os.makedirs(target_dir, exist_ok=True)
    
    try:
        # 以只读模式打开zip文件
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # 解压所有文件到指定目录
            zip_ref.extractall(target_dir)
            return True
    except zipfile.BadZipFile:
        return False
    except FileNotFoundError:
        return False
    except PermissionError:
        return False
    except Exception as e:
        return False
    
def compare_version(v1: str, v2: str) -> int:
    """
    比较两个版本号的大小。

    支持任意段数的版本号，如 1.0、1.0.1、1.19.0 等。
    每段均按整数比较，不做字符串排序。

    Args:
        v1 (str): 版本号A
        v2 (str): 版本号B

    Returns:
        int:  1 表示 v1 > v2
              0 表示 v1 == v2
             -1 表示 v1 < v2
    """
    parts1 = [int(x) for x in v1.split(".")]
    parts2 = [int(x) for x in v2.split(".")]
    # 补齐短版本号，末尾补 0
    length = max(len(parts1), len(parts2))
    parts1 += [0] * (length - len(parts1))
    parts2 += [0] * (length - len(parts2))
    for a, b in zip(parts1, parts2):
        if a > b:
            return 1
        if a < b:
            return -1
    return 0


def download_file(url: str, dest_path: str) -> bool:
    """
    从指定URL下载文件到目标路径

    Args:
        url (str): 文件下载链接
        dest_path (str): 保存文件的完整路径（含文件名）

    Returns:
        bool: 下载成功返回True，失败返回False
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    try:
        with requests.get(url, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception:
        return False
    
if __name__ == "__main__":
    print(get_skill_work_dir())