"""
地址處理工具函數
提供地址標準化和格式轉換功能
"""
import re
from typing import Dict


def standardize_village_address(
    address: str, 
    village_name: str,
    remove_village_suffix: bool = True,
    convert_dash_to_zhi: bool = True
) -> str:
    """標準化村里地址格式
    
    Args:
        address: 原始地址
        village_name: 村里名稱（如"頂山里"）
        remove_village_suffix: 是否移除村里後綴（如"里"字）
        convert_dash_to_zhi: 是否轉換門牌號格式（2-1號 -> 2號之1）
    
    Returns:
        標準化後的地址
        
    Examples:
        >>> standardize_village_address("頂山里1號", "頂山里")
        "頂山1號"
        >>> standardize_village_address("頂山里2-1號", "頂山里")
        "頂山2號之1"
    """
    address = address.strip()
    
    # 移除村里後綴
    if remove_village_suffix and village_name in address:
        # 提取村里名稱的主體部分（去掉"里"字）
        village_base = village_name.replace("里", "")
        address = address.replace(village_name, village_base)
    
    # 轉換門牌號格式：2-1號 -> 2號之1
    if convert_dash_to_zhi:
        pattern = r"(\d+)-(\d+)號"
        match = re.search(pattern, address)
        if match:
            main_num = match.group(1)
            sub_num = match.group(2)
            address = re.sub(pattern, f"{main_num}號之{sub_num}", address)
    
    return address


def create_group_id(district: str, village: str, neighborhood: int) -> str:
    """創建分組編號
    
    Args:
        district: 區域名稱
        village: 村里名稱
        neighborhood: 鄰別編號
        
    Returns:
        分組編號（如"七股區頂山里-01"）
    """
    return f"{district}{village}-{neighborhood:02d}"


def get_neighborhood_mapping(village_type: str = "standard") -> Dict[str, int]:
    """取得鄰別對應表
    
    Args:
        village_type: 村里類型，支援不同的鄰別命名規則
        
    Returns:
        鄰別名稱到編號的對應字典
    """
    if village_type == "standard":
        return {
            "第一鄰": 1, "第二鄰": 2, "第三鄰 ": 3, "第四鄰": 4,
            "第五鄰": 5, "第六鄰": 6, "第七鄰": 7, "第八鄰": 8,
        }
    elif village_type == "numeric":
        return {f"{i}鄰": i for i in range(1, 21)}  # 支援1-20鄰
    else:
        raise ValueError(f"不支援的村里類型: {village_type}")


def validate_address_format(address: str) -> bool:
    """驗證地址格式是否正確
    
    Args:
        address: 地址字串
        
    Returns:
        是否為有效地址格式
    """
    if not address or not address.strip():
        return False
    
    # 基本格式檢查：應該包含數字和"號"字
    pattern = r".*\d+.*號"
    return bool(re.search(pattern, address))


def extract_address_number(address: str) -> str:
    """提取地址中的門牌號碼部分
    
    Args:
        address: 完整地址
        
    Returns:
        門牌號碼部分（用於模糊匹配）
    """
    # 移除"號"和"之"字，保留數字和連接符
    return address.replace("號", "").replace("之", "")
