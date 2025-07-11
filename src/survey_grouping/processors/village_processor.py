"""
通用村里數據處理器
支援處理不同村里的Excel數據，進行地址標準化和Supabase匹配
"""
import argparse
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from survey_grouping.database.connection import get_supabase_client
from survey_grouping.utils.address_utils import (
    extract_address_number,
    get_neighborhood_mapping,
    standardize_village_address,
    validate_address_format,
)

logger = logging.getLogger(__name__)


def convert_fullwidth_to_halfwidth(text: str) -> str:
    """轉換全形數字為半形數字
    
    Args:
        text: 包含全形數字的文字
        
    Returns:
        轉換後的文字
    """
    if not text:
        return text
        
    # 全形數字到半形數字的對應
    fullwidth_map = {
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9'
    }
    
    result = str(text)
    for full, half in fullwidth_map.items():
        result = result.replace(full, half)
    
    return result


def extract_neighborhood_from_address(address: str, allow_database_lookup: bool = False) -> Optional[int]:
    """從完整地址中提取鄰別編號
    
    Args:
        address: 完整地址，如"臺南市七股區七股里13鄰七股123-12號"
        allow_database_lookup: 是否允許在找不到鄰別時標記為需要資料庫查詢
        
    Returns:
        鄰別編號，如果找不到則返回None，如果allow_database_lookup=True則返回-1表示需要查詢
    """
    if not address:
        return None
        
    # 尋找鄰別模式：數字+鄰
    match = re.search(r'(\d+)鄰', address)
    if match:
        return int(match.group(1))
    
    # 如果允許資料庫查詢且沒有鄰別資訊，返回特殊值
    if allow_database_lookup:
        return -1  # 特殊標記，表示需要資料庫查詢
    
    return None


class VillageProcessor:
    """通用村里數據處理器"""

    def __init__(self, district: str, village: str, include_cross_village: bool = False):
        """初始化處理器
        
        Args:
            district: 區域名稱（如"七股區"）
            village: 村里名稱（如"頂山里"）
            include_cross_village: 是否包含同區其他村里的地址處理
        """
        self.district = district
        self.village = village
        self.include_cross_village = include_cross_village
        self.supabase = get_supabase_client()

    def read_excel_data(
        self, 
        excel_path: str, 
        neighborhood_mapping: Optional[Dict[str, int]] = None
    ) -> List[Dict]:
        """讀取Excel文件中的所有鄰別數據
        
        支援兩種格式：
        1. 多工作表格式：每個工作表代表一個鄰別，需要 neighborhood_mapping
        2. 單工作表格式：所有資料在一個工作表中，包含鄰別欄位
        
        Args:
            excel_path: Excel文件路徑
            neighborhood_mapping: 鄰別名稱到編號的對應字典（多工作表格式時需要）
            
        Returns:
            處理後的數據列表
        """
        all_data = []

        try:
            # 檢查 Excel 文件結構，決定使用哪種格式
            xl_file = pd.ExcelFile(excel_path)
            sheet_names = xl_file.sheet_names
            
            # 嘗試讀取第一個工作表來判斷格式
            first_sheet_df = pd.read_excel(excel_path, sheet_name=sheet_names[0])
            
            # 判斷是否為單工作表格式（包含 '鄰' 欄位）
            if '鄰' in first_sheet_df.columns:
                logger.info("檢測到單工作表格式，直接從工作表讀取資料")
                return self._read_single_sheet_format(excel_path, sheet_names[0])
            
            # 判斷是否為名冊格式（包含 '通訊地址' 欄位或第二行有 '通訊地址'）
            if ('通訊地址' in first_sheet_df.columns or 
                (len(first_sheet_df) > 1 and '通訊地址' in str(first_sheet_df.iloc[1].values))):
                logger.info("檢測到名冊格式，使用名冊處理方式")
                return self._read_roster_format(excel_path, sheet_names[0])
            
            # 判斷是否為簡單列表格式（檢查第一行是否包含 '慰問地點' 或類似地址欄位）
            if (len(first_sheet_df) > 0 and 
                ('慰問地點' in str(first_sheet_df.iloc[0].values) or 
                 '地址' in str(first_sheet_df.iloc[0].values) or
                 '慰問地點' in first_sheet_df.columns or 
                 '地址' in first_sheet_df.columns)):
                logger.info("檢測到簡單列表格式（支援混合地址格式），使用混合格式處理方式")
                return self._read_mixed_format(excel_path, sheet_names[0])
            
            # 多工作表格式，需要 neighborhood_mapping
            if neighborhood_mapping is None:
                raise ValueError("多工作表格式需要提供 neighborhood_mapping")
                
            logger.info("檢測到多工作表格式，使用 neighborhood_mapping")
            
            target_sheet_names = list(neighborhood_mapping.keys())
            
            for sheet_name in target_sheet_names:
                try:
                    df = pd.read_excel(excel_path, sheet_name=sheet_name)

                    # 跳過標題行, 從第二行開始讀取
                    if len(df) > 1:
                        # 重新命名欄位
                        df.columns = ["序號", "姓名", "地址"]

                        # 移除標題行
                        df = df.iloc[1:].reset_index(drop=True)

                        # 過濾掉空白行
                        df = df.dropna(subset=["地址"])

                        # 添加鄰別資訊
                        neighborhood_num = neighborhood_mapping[sheet_name]

                        for _, row in df.iterrows():
                            if (pd.notna(row["地址"]) and 
                                str(row["地址"]).strip()):
                                name = (
                                    str(row["姓名"]).strip()
                                    if pd.notna(row["姓名"])
                                    else ""
                                )
                                serial_number = (
                                    str(row["序號"]).strip()
                                    if pd.notna(row["序號"])
                                    else ""
                                )
                                address = str(row["地址"]).strip()
                                
                                # 驗證地址格式
                                if validate_address_format(address):
                                    all_data.append(
                                        {
                                            "neighborhood": neighborhood_num,
                                            "name": name,
                                            "serial_number": serial_number,
                                            "original_address": address,
                                            "sheet_name": sheet_name,
                                        },
                                    )
                                else:
                                    logger.warning(
                                        "跳過無效地址格式: %s", address
                                    )

                except Exception as e:
                    logger.warning("讀取工作表 %s 失敗: %s", sheet_name, e)
                    continue

            logger.info("成功讀取 %d 筆地址數據", len(all_data))
            return all_data

        except Exception:
            logger.exception("讀取Excel文件失敗")
            raise

    def _read_mixed_format(self, excel_path: str, sheet_name: str) -> List[Dict]:
        """讀取混合格式的 Excel 資料，智能處理簡單和完整地址
        
        期望格式：
        Row 0: 標題行（編號, 里別, 名字, 慰問地點, 備註）
        Row 1+: 實際資料
        
        支援混合地址格式：
        - 簡單地址：如 "大埕137號"
        - 完整地址：如 "臺南市七股區大埕里1鄰大埕137號"
        
        Args:
            excel_path: Excel 文件路徑
            sheet_name: 工作表名稱
            
        Returns:
            處理後的數據列表
        """
        all_data = []
        cross_village_data = []  # 記錄跨村里地址
        invalid_addresses = []  # 記錄無效地址
        
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            
            # 使用第一行作為標題
            df.columns = df.iloc[0].values
            df = df.iloc[1:].reset_index(drop=True)
            
            # 檢查是否有必要的欄位
            if '編號' not in df.columns:
                raise ValueError("混合格式必須包含 '編號' 欄位")
            if '慰問地點' not in df.columns and '地址' not in df.columns:
                raise ValueError("混合格式必須包含 '慰問地點' 或 '地址' 欄位")
            
            # 統一地址欄位名稱
            if '慰問地點' in df.columns:
                address_column = '慰問地點'
            else:
                address_column = '地址'
            
            # 移除空行
            df = df.dropna(subset=['編號']).reset_index(drop=True)
            
            logger.info(f"混合格式：找到 {len(df)} 筆原始資料")
            
            # 處理每一行資料
            for _, row in df.iterrows():
                if pd.notna(row[address_column]) and str(row[address_column]).strip():
                    name = str(row['名字']).strip() if pd.notna(row['名字']) and '名字' in df.columns else ""
                    serial_number = str(row['編號']).strip() if pd.notna(row['編號']) else ""
                    raw_address = str(row[address_column]).strip()
                    
                    # 轉換全形數字
                    address = convert_fullwidth_to_halfwidth(raw_address)
                    
                    # 智能判斷並處理地址格式
                    self._process_mixed_address(address, name, serial_number, raw_address, sheet_name,
                                              all_data, cross_village_data, invalid_addresses)
                        
            logger.info(f"混合格式處理完成：主要村里 {len(all_data)} 筆，跨村里 {len(cross_village_data)} 筆，無效地址 {len(invalid_addresses)} 筆")
            
            # 合併所有資料
            all_data.extend(cross_village_data)
            
            # 儲存無效地址報告
            if invalid_addresses:
                self._save_invalid_addresses(invalid_addresses)
            
            return all_data
            
        except Exception as e:
            logger.error(f"讀取混合格式失敗: {e}")
            raise
    
    def _process_mixed_address(self, address: str, name: str, serial_number: str, 
                             raw_address: str, sheet_name: str,
                             all_data: List[Dict], cross_village_data: List[Dict], 
                             invalid_addresses: List[Dict]) -> None:
        """智能處理混合格式地址
        
        Args:
            address: 轉換全形數字後的地址
            name: 姓名
            serial_number: 編號
            raw_address: 原始地址
            sheet_name: 工作表名稱
            all_data: 主要村里數據列表
            cross_village_data: 跨村里數據列表
            invalid_addresses: 無效地址列表
        """
        # 判斷是否為完整地址
        is_complete_address = ("臺南市" in address or "台南市" in address) and self.district in address
        
        if is_complete_address:
            # 完整地址處理 - 使用名冊格式的標準化方法
            logger.debug(f"處理完整地址: {address}")
            
            # 檢查地址是否為目標區域和村里
            if f"{self.district}" in address and f"{self.village}" in address:
                # 主要村里地址處理
                neighborhood = extract_neighborhood_from_address(address, allow_database_lookup=True)
                
                if neighborhood == -1:
                    # 需要資料庫查詢鄰別資訊
                    logger.info(f"完整地址缺少鄰別資訊，嘗試從資料庫查詢: {address}")
                    standardized_addr = self._standardize_roster_address(address)
                    neighborhood = self.query_neighborhood_by_address(standardized_addr)
                    
                    if neighborhood is None:
                        logger.warning(f"無法從資料庫查詢鄰別資訊: {address}")
                        neighborhood = 0
                    else:
                        logger.info(f"成功從資料庫查詢到鄰別: {neighborhood}")
                elif neighborhood is None:
                    logger.warning(f"無法提取鄰別資訊: {address}")
                    neighborhood = 0
                
                # 標準化地址格式（使用名冊格式標準化）
                standardized_addr = self._standardize_roster_address(address)
                
                # 驗證地址格式
                if validate_address_format(standardized_addr):
                    all_data.append({
                        "neighborhood": neighborhood,
                        "name": name,
                        "serial_number": serial_number,
                        "original_address": raw_address,
                        "standardized_address": standardized_addr,
                        "sheet_name": sheet_name,
                    })
                else:
                    logger.warning("跳過無效地址格式: %s", standardized_addr)
                    invalid_addresses.append({
                        "serial_number": serial_number,
                        "name": name,
                        "raw_address": raw_address,
                        "reason": "地址格式無效"
                    })
            elif self.include_cross_village and f"{self.district}" in address:
                # 跨村里地址處理
                logger.info(f"跨村里完整地址: {address}")
                neighborhood = extract_neighborhood_from_address(address, allow_database_lookup=True)
                
                if neighborhood == -1:
                    # 需要資料庫查詢鄰別資訊
                    logger.info(f"跨村里完整地址缺少鄰別資訊，嘗試從資料庫查詢: {address}")
                    standardized_addr = self._standardize_cross_village_address(address)
                    # 提取村里名稱用於查詢
                    village_name = self._extract_village_name(address)
                    # 使用提取的村里名稱進行查詢
                    neighborhood = self.query_neighborhood_by_address(standardized_addr, village_name)
                    
                    if neighborhood is None:
                        logger.warning(f"無法從資料庫查詢跨村里地址鄰別資訊: {address}")
                        neighborhood = 0
                    else:
                        logger.info(f"成功從資料庫查詢到跨村里地址鄰別: {neighborhood}")
                elif neighborhood is None:
                    logger.warning(f"跨村里地址無法提取鄰別資訊: {address}")
                    neighborhood = 0
                
                # 標準化地址格式（使用跨村里標準化）
                standardized_addr = self._standardize_cross_village_address(address)
                
                # 驗證地址格式
                if validate_address_format(standardized_addr):
                    cross_village_data.append({
                        "neighborhood": neighborhood,
                        "name": name,
                        "serial_number": serial_number,
                        "original_address": raw_address,
                        "standardized_address": standardized_addr,
                        "sheet_name": sheet_name,
                    })
                else:
                    logger.warning("跳過無效跨村里地址格式: %s", standardized_addr)
                    invalid_addresses.append({
                        "serial_number": serial_number,
                        "name": name,
                        "raw_address": raw_address,
                        "reason": "跨村里地址格式無效"
                    })
            else:
                # 無效地址
                logger.warning(f"無效地址（非目標區域或村里）: {address}")
                invalid_addresses.append({
                    "serial_number": serial_number,
                    "name": name,
                    "raw_address": raw_address,
                    "reason": f"非{self.district}地址" if f"{self.district}" not in address else f"非{self.village}地址"
                })
        else:
            # 簡單地址處理 - 使用原有的簡單地址標準化方法
            logger.debug(f"處理簡單地址: {address}")
            
            # 構造完整地址用於檢查
            full_address = f"臺南市{self.district}{self.village}{address}"
            
            # 檢查地址是否為目標區域和村里（簡單地址默認為目標村里）
            neighborhood = extract_neighborhood_from_address(full_address, allow_database_lookup=True)
            
            if neighborhood == -1:
                # 需要資料庫查詢鄰別資訊
                logger.info(f"簡單地址缺少鄰別資訊，嘗試從資料庫查詢: {address}")
                standardized_addr = standardize_village_address(address, self.village)
                neighborhood = self.query_neighborhood_by_address(standardized_addr)
                
                if neighborhood is None:
                    logger.warning(f"無法從資料庫查詢鄰別資訊: {address}")
                    neighborhood = 0
                else:
                    logger.info(f"成功從資料庫查詢到鄰別: {neighborhood}")
            elif neighborhood is None:
                logger.warning(f"無法提取鄰別資訊: {address}")
                neighborhood = 0
            
            # 標準化地址格式（使用簡單地址標準化）
            standardized_addr = standardize_village_address(address, self.village)
            
            # 驗證地址格式
            if validate_address_format(standardized_addr):
                all_data.append({
                    "neighborhood": neighborhood,
                    "name": name,
                    "serial_number": serial_number,
                    "original_address": raw_address,
                    "standardized_address": standardized_addr,
                    "sheet_name": sheet_name,
                })
            else:
                logger.warning("跳過無效地址格式: %s", standardized_addr)
                invalid_addresses.append({
                    "serial_number": serial_number,
                    "name": name,
                    "raw_address": raw_address,
                    "reason": "地址格式無效"
                })

    def _save_invalid_addresses(self, invalid_addresses: List[Dict]) -> None:
        """儲存無效地址報告
        
        Args:
            invalid_addresses: 無效地址列表
        """
        if not invalid_addresses:
            return
            
        logger.info(f"發現 {len(invalid_addresses)} 個無效地址")
        
        # 創建無效地址報告 DataFrame
        invalid_df = pd.DataFrame(invalid_addresses)
        
        # 重新排序和重命名欄位
        invalid_df = invalid_df.rename(columns={
            'serial_number': '序號',
            'name': '姓名',
            'raw_address': '原始地址',
            'reason': '無效原因'
        })
        
        # 選擇需要的欄位
        columns_to_export = ['序號', '姓名', '原始地址', '無效原因']
        invalid_df = invalid_df[columns_to_export]
        
        # 產生輸出檔案名稱
        output_file = Path("output") / f"{self.district}{self.village}地址處理結果_無效地址.csv"
        output_file.parent.mkdir(exist_ok=True)
        
        # 儲存到 CSV 檔案
        invalid_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"無效地址報告已儲存至: {output_file}")
        
        # 記錄詳細資訊
        for addr in invalid_addresses:
            logger.warning(f"無效地址: {addr['serial_number']} - {addr['raw_address']} ({addr['reason']})")

    def _read_single_sheet_format(self, excel_path: str, sheet_name: str) -> List[Dict]:
        """讀取單工作表格式的 Excel 資料
        
        期望欄位：編號, 行政區, 里, 鄰, 地址, 姓名
        
        Args:
            excel_path: Excel 文件路徑
            sheet_name: 工作表名稱
            
        Returns:
            處理後的數據列表
        """
        all_data = []
        
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            
            # 檢查必要欄位
            required_columns = ['編號', '行政區', '里', '鄰', '地址', '姓名']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"缺少必要欄位: {missing_columns}")
            
            # 過濾出符合當前處理器設定的資料
            # 篩選符合區域和村里的資料
            filtered_df = df[
                (df['行政區'] == self.district) & 
                (df['里'] == self.village)
            ]
            
            if len(filtered_df) == 0:
                logger.warning(f"在工作表 {sheet_name} 中找不到 {self.district} {self.village} 的資料")
                return all_data
            
            logger.info(f"找到 {len(filtered_df)} 筆 {self.district} {self.village} 的資料")
            
            # 處理每一行資料
            for _, row in filtered_df.iterrows():
                if pd.notna(row['地址']) and str(row['地址']).strip():
                    name = str(row['姓名']).strip() if pd.notna(row['姓名']) else ""
                    serial_number = str(row['編號']).strip() if pd.notna(row['編號']) else ""
                    address = str(row['地址']).strip()
                    neighborhood = int(row['鄰']) if pd.notna(row['鄰']) else 0
                    
                    # 驗證地址格式
                    if validate_address_format(address):
                        all_data.append({
                            "neighborhood": neighborhood,
                            "name": name,
                            "serial_number": serial_number,
                            "original_address": address,
                            "sheet_name": sheet_name,
                        })
                    else:
                        logger.warning("跳過無效地址格式: %s", address)
            
            logger.info("成功讀取 %d 筆地址數據", len(all_data))
            return all_data
            
        except Exception as e:
            logger.error(f"讀取單工作表格式失敗: {e}")
            raise

    def _read_roster_format(self, excel_path: str, sheet_name: str) -> List[Dict]:
        """讀取名冊格式的 Excel 資料
        
        期望格式：
        Row 0: 標題（如"臺南市七股區七股里 名冊"）
        Row 1: 欄位標題（編號, 鄉鎮市區村里, 姓名, 通訊地址）
        Row 2: 空行
        Row 3+: 實際資料
        
        Args:
            excel_path: Excel 文件路徑
            sheet_name: 工作表名稱
            
        Returns:
            處理後的數據列表
        """
        all_data = []
        cross_village_data = []  # 記錄跨村里地址
        invalid_addresses = []  # 記錄無效地址
        
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            
            # 找到資料起始行（通常是第3行，index=3）
            data_start_row = 3
            
            # 檢查是否有正確的標題行
            if len(df) > 1:
                header_row = df.iloc[1]
                if '通訊地址' not in str(header_row.values):
                    raise ValueError("找不到標準的名冊格式標題行")
            
            # 從資料起始行開始讀取
            data_df = df.iloc[data_start_row:].copy()
            
            # 靈活處理不同數量的欄位，只使用前4個有用的欄位
            if data_df.shape[1] >= 4:
                # 只保留前4個欄位
                data_df = data_df.iloc[:, :4].copy()
                data_df.columns = ['編號', '鄉鎮市區村里', '姓名', '通訊地址']
            else:
                raise ValueError(f"名冊格式至少需要4個欄位，但只找到 {data_df.shape[1]} 個欄位")
            
            # 移除空行
            data_df = data_df.dropna(subset=['編號']).reset_index(drop=True)
            
            logger.info(f"名冊格式：找到 {len(data_df)} 筆原始資料")
            
            # 處理每一行資料
            for _, row in data_df.iterrows():
                if pd.notna(row['通訊地址']) and str(row['通訊地址']).strip():
                    name = str(row['姓名']).strip() if pd.notna(row['姓名']) else ""
                    serial_number = str(int(row['編號'])) if pd.notna(row['編號']) else ""
                    raw_address = str(row['通訊地址']).strip()
                    
                    # 轉換全形數字
                    address = convert_fullwidth_to_halfwidth(raw_address)
                    
                    # 檢查地址是否為目標區域和村里
                    if f"{self.district}" in address and f"{self.village}" in address:
                        # 主要村里地址處理
                        neighborhood = extract_neighborhood_from_address(address, allow_database_lookup=True)
                        
                        if neighborhood == -1:
                            # 需要資料庫查詢鄰別資訊
                            logger.info(f"地址缺少鄰別資訊，嘗試從資料庫查詢: {address}")
                            standardized_addr = self._standardize_roster_address(address)
                            neighborhood = self.query_neighborhood_by_address(standardized_addr)
                            
                            if neighborhood is None:
                                logger.warning(f"無法從資料庫查詢鄰別資訊: {address}")
                                neighborhood = 0
                            else:
                                logger.info(f"成功從資料庫查詢到鄰別: {neighborhood}")
                        elif neighborhood is None:
                            logger.warning(f"無法提取鄰別資訊: {address}")
                            neighborhood = 0
                        
                        # 標準化地址格式（移除臺南市、區、里、鄰等前綴）
                        standardized_addr = self._standardize_roster_address(address)
                        
                        # 驗證地址格式
                        if validate_address_format(standardized_addr):
                            all_data.append({
                                "neighborhood": neighborhood,
                                "name": name,
                                "serial_number": serial_number,
                                "original_address": raw_address,
                                "standardized_address": standardized_addr,
                                "sheet_name": sheet_name,
                            })
                        else:
                            logger.warning("跳過無效地址格式: %s", standardized_addr)
                            invalid_addresses.append({
                                "serial_number": serial_number,
                                "name": name,
                                "raw_address": raw_address,
                                "reason": "地址格式無效"
                            })
                    elif self.include_cross_village and f"{self.district}" in address:
                        # 同區其他村里地址處理
                        logger.info(f"跨村里地址: {address}")
                        neighborhood = extract_neighborhood_from_address(address, allow_database_lookup=True)
                        
                        if neighborhood == -1:
                            # 需要資料庫查詢鄰別資訊
                            logger.info(f"跨村里地址缺少鄰別資訊，嘗試從資料庫查詢: {address}")
                            standardized_addr = self._standardize_cross_village_address(address)
                            # 提取村里名稱用於查詢
                            village_name = self._extract_village_name(address)
                            # 使用提取的村里名稱進行查詢
                            neighborhood = self.query_neighborhood_by_address(standardized_addr, village_name)
                            
                            if neighborhood is None:
                                logger.warning(f"無法從資料庫查詢跨村里地址鄰別資訊: {address}")
                                neighborhood = 0
                            else:
                                logger.info(f"成功從資料庫查詢到跨村里地址鄰別: {neighborhood}")
                        elif neighborhood is None:
                            logger.warning(f"跨村里地址無法提取鄰別資訊: {address}")
                            neighborhood = 0
                        
                        # 標準化地址格式
                        standardized_addr = self._standardize_cross_village_address(address)
                        
                        # 驗證地址格式
                        if validate_address_format(standardized_addr):
                            cross_village_data.append({
                                "neighborhood": neighborhood,
                                "name": name,
                                "serial_number": serial_number,
                                "original_address": raw_address,
                                "standardized_address": standardized_addr,
                                "sheet_name": sheet_name,
                            })
                        else:
                            logger.warning("跳過無效跨村里地址格式: %s", standardized_addr)
                            invalid_addresses.append({
                                "serial_number": serial_number,
                                "name": name,
                                "raw_address": raw_address,
                                "reason": "跨村里地址格式無效"
                            })
                    else:
                        # 跨區或跨里地址
                        logger.warning(f"跨區域地址: {address}")
                        invalid_addresses.append({
                            "serial_number": serial_number,
                            "name": name,
                            "raw_address": raw_address,
                            "reason": f"非{self.district}地址"
                        })
            
            logger.info("成功讀取 %d 筆有效地址數據", len(all_data))
            if cross_village_data:
                logger.info("發現 %d 筆跨村里地址", len(cross_village_data))
                # 將跨村里地址存為實例變數，供後續導出
                self.cross_village_data = cross_village_data
            if invalid_addresses:
                logger.warning("發現 %d 筆無效或跨區域地址", len(invalid_addresses))
                # 將無效地址存為實例變數，供後續導出
                self.invalid_addresses = invalid_addresses
            
            return all_data
            
        except Exception as e:
            logger.error(f"讀取名冊格式失敗: {e}")
            raise

    def _read_simple_list_format(self, excel_path: str, sheet_name: str) -> List[Dict]:
        """讀取簡單列表格式的 Excel 資料
        
        期望格式：
        Row 0: 標題（編號, 里別, 名字, 慰問地點, 備註）
        Row 1+: 實際資料
        
        Args:
            excel_path: Excel 文件路徑
            sheet_name: 工作表名稱
            
        Returns:
            處理後的數據列表
        """
        all_data = []
        cross_village_data = []  # 記錄跨村里地址
        invalid_addresses = []  # 記錄無效地址
        
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            
            # 使用第一行作為標題
            df.columns = df.iloc[0].values
            df = df.iloc[1:].reset_index(drop=True)
            
            # 檢查是否有必要的欄位
            if '編號' not in df.columns:
                raise ValueError("簡單列表格式必須包含 '編號' 欄位")
            if '慰問地點' not in df.columns and '地址' not in df.columns:
                raise ValueError("簡單列表格式必須包含 '慰問地點' 或 '地址' 欄位")
            
            # 統一地址欄位名稱
            if '慰問地點' in df.columns:
                address_column = '慰問地點'
            else:
                address_column = '地址'
            
            # 移除空行
            df = df.dropna(subset=['編號']).reset_index(drop=True)
            
            logger.info(f"簡單列表格式：找到 {len(df)} 筆原始資料")
            
            # 處理每一行資料
            for _, row in df.iterrows():
                if pd.notna(row[address_column]) and str(row[address_column]).strip():
                    name = str(row['名字']).strip() if pd.notna(row['名字']) and '名字' in df.columns else ""
                    serial_number = str(row['編號']).strip() if pd.notna(row['編號']) else ""
                    raw_address = str(row[address_column]).strip()
                    
                    # 轉換全形數字
                    address = convert_fullwidth_to_halfwidth(raw_address)
                    
                    # 構造完整地址用於檢查
                    full_address = f"臺南市{self.district}{self.village}{address}"
                    
                    # 檢查地址是否為目標區域和村里
                    if f"{self.district}" in full_address and f"{self.village}" in full_address:
                        # 主要村里地址處理
                        neighborhood = extract_neighborhood_from_address(full_address, allow_database_lookup=True)
                        
                        if neighborhood == -1:
                            # 需要資料庫查詢鄰別資訊
                            logger.info(f"地址缺少鄰別資訊，嘗試從資料庫查詢: {address}")
                            # 判斷是否為完整地址
                            if "臺南市" in address or "台南市" in address:
                                # 完整地址，直接使用原始地址查詢
                                standardized_addr = address
                            else:
                                # 簡單地址，需要標準化
                                standardized_addr = standardize_village_address(address, self.village)
                            neighborhood = self.query_neighborhood_by_address(standardized_addr)
                            
                            if neighborhood is None:
                                logger.warning(f"無法從資料庫查詢鄰別資訊: {address}")
                                neighborhood = 0
                            else:
                                logger.info(f"成功從資料庫查詢到鄰別: {neighborhood}")
                        elif neighborhood is None:
                            logger.warning(f"無法提取鄰別資訊: {address}")
                            neighborhood = 0
                        
                        # 標準化地址格式（包含 dash-to-zhi 轉換）
                        if "臺南市" in address or "台南市" in address:
                            # 完整地址，直接使用原始地址
                            standardized_addr = address
                        else:
                            # 簡單地址，需要標準化
                            standardized_addr = standardize_village_address(address, self.village)
                        
                        # 驗證地址格式
                        if validate_address_format(standardized_addr):
                            all_data.append({
                                "neighborhood": neighborhood,
                                "name": name,
                                "serial_number": serial_number,
                                "original_address": raw_address,
                                "standardized_address": standardized_addr,
                                "sheet_name": sheet_name,
                            })
                        else:
                            logger.warning("跳過無效地址格式: %s", standardized_addr)
                            invalid_addresses.append({
                                "serial_number": serial_number,
                                "name": name,
                                "raw_address": raw_address,
                                "reason": "地址格式無效"
                            })
                    elif self.include_cross_village and f"{self.district}" in full_address:
                        # 同區其他村里地址處理
                        logger.info(f"跨村里地址: {full_address}")
                        neighborhood = extract_neighborhood_from_address(full_address, allow_database_lookup=True)
                        
                        if neighborhood == -1:
                            # 需要資料庫查詢鄰別資訊
                            logger.info(f"跨村里地址缺少鄰別資訊，嘗試從資料庫查詢: {full_address}")
                            # 提取村里名稱用於查詢
                            village_name = self._extract_village_name(full_address)
                            # 判斷是否為完整地址
                            if "臺南市" in address or "台南市" in address:
                                # 完整地址，直接使用原始地址查詢
                                standardized_addr = address
                            else:
                                # 簡單地址，需要標準化
                                standardized_addr = standardize_village_address(address, village_name)
                            # 使用提取的村里名稱進行查詢
                            neighborhood = self.query_neighborhood_by_address(standardized_addr, village_name)
                            
                            if neighborhood is None:
                                logger.warning(f"無法從資料庫查詢跨村里地址鄰別資訊: {full_address}")
                                neighborhood = 0
                            else:
                                logger.info(f"成功從資料庫查詢到跨村里地址鄰別: {neighborhood}")
                        elif neighborhood is None:
                            logger.warning(f"跨村里地址無法提取鄰別資訊: {full_address}")
                            neighborhood = 0
                        
                        # 標準化地址格式（包含 dash-to-zhi 轉換）
                        if "臺南市" in address or "台南市" in address:
                            # 完整地址，直接使用原始地址
                            standardized_addr = address
                        else:
                            # 簡單地址，需要標準化
                            village_name = self._extract_village_name(full_address)
                            standardized_addr = standardize_village_address(address, village_name)
                        
                        # 驗證地址格式
                        if validate_address_format(standardized_addr):
                            cross_village_data.append({
                                "neighborhood": neighborhood,
                                "name": name,
                                "serial_number": serial_number,
                                "original_address": raw_address,
                                "standardized_address": standardized_addr,
                                "sheet_name": sheet_name,
                            })
                        else:
                            logger.warning("跳過無效跨村里地址格式: %s", standardized_addr)
                            invalid_addresses.append({
                                "serial_number": serial_number,
                                "name": name,
                                "raw_address": raw_address,
                                "reason": "跨村里地址格式無效"
                            })
                    else:
                        # 跨區或跨里地址
                        logger.warning(f"跨區域地址: {full_address}")
                        invalid_addresses.append({
                            "serial_number": serial_number,
                            "name": name,
                            "raw_address": raw_address,
                            "reason": f"非{self.district}地址"
                        })
            
            logger.info("成功讀取 %d 筆有效地址數據", len(all_data))
            if cross_village_data:
                logger.info("發現 %d 筆跨村里地址", len(cross_village_data))
                # 將跨村里地址存為實例變數，供後續導出
                self.cross_village_data = cross_village_data
            if invalid_addresses:
                logger.warning("發現 %d 筆無效或跨區域地址", len(invalid_addresses))
                # 將無效地址存為實例變數，供後續導出
                self.invalid_addresses = invalid_addresses
            
            return all_data
            
        except Exception as e:
            logger.error(f"讀取簡單列表格式失敗: {e}")
            raise

    def _standardize_roster_address(self, full_address: str) -> str:
        """標準化名冊格式的完整地址
        
        將 "臺南市七股區七股里13鄰七股123-12號" 轉換為 "七股123號之12"
        支援移除台南市郵遞區號，如：
        - "724臺南市七股區大埕里大埕350-6號" -> "大埕350號之6"
        - "70101臺南市中西區..." -> "..."
        - "700456台南市中西區..." -> "..."
        
        Args:
            full_address: 完整地址
            
        Returns:
            標準化後的地址
        """
        address = full_address
        
        # 移除台南市郵遞區號（如果存在）
        # 郵遞區號模式：7開頭，3-6位數字，後面跟著"臺南市"或"台南市"
        postal_code_pattern = r'^7\d{2,5}(?=臺南市|台南市)'
        if re.match(postal_code_pattern, address):
            address = re.sub(postal_code_pattern, '', address)
            logger.debug(f"移除台南市郵遞區號: {full_address} -> {address}")
        
        # 移除前綴部分
        prefixes_to_remove = [
            "臺南市", "台南市",
            f"{self.district}",
            f"{self.village}",
        ]
        
        for prefix in prefixes_to_remove:
            address = address.replace(prefix, "")
        
        # 移除鄰別資訊 (如 "13鄰")
        address = re.sub(r'\d+鄰', '', address)
        
        # 清理多餘的空白和標點
        address = address.strip()
        
        # 使用既有的標準化邏輯進行進一步轉換 (如 74-1號 -> 74號之1)
        address = standardize_village_address(address, self.village, 
                                            remove_village_suffix=False,  # 已經移除過了
                                            convert_dash_to_zhi=True)     # 進行格式轉換
        
        return address

    def _standardize_cross_village_address(self, full_address: str) -> str:
        """標準化跨村里地址格式
        
        將跨村里地址轉換為標準格式，保留村里資訊用於座標查詢
        例如：將 "臺南市七股區塩埕里6鄰鹽埕237號之3" 轉換為 "鹽埕237號之3"
        
        Args:
            full_address: 完整地址
            
        Returns:
            標準化後的地址
        """
        address = full_address
        
        # 移除前綴部分
        prefixes_to_remove = [
            "臺南市", "台南市",
            f"{self.district}",
        ]
        
        for prefix in prefixes_to_remove:
            address = address.replace(prefix, "")
        
        # 移除鄰別資訊 (如 "6鄰")
        address = re.sub(r'\d+鄰', '', address)
        
        # 清理多餘的空白和標點
        address = address.strip()
        
        # 使用既有的標準化邏輯進行進一步轉換
        address = standardize_village_address(address, "", 
                                            remove_village_suffix=False,
                                            convert_dash_to_zhi=True)
        
        return address

    def _extract_village_name(self, full_address: str) -> str:
        """從完整地址中提取村里名稱
        
        Args:
            full_address: 完整地址，如"臺南市七股區塩埕里6鄰鹽埕237號之3"
            
        Returns:
            村里名稱，如"塩埕里"
        """
        # 尋找村里名稱模式
        import re
        
        # 匹配村里名稱（漢字 + 里/村）
        match = re.search(r'([^市區]*[里村])', full_address)
        if match:
            return match.group(1)
        
        # 如果找不到，返回預設村里
        return self.village

    def export_invalid_addresses(self, output_path: str):
        """導出無效或跨區域地址報告
        
        Args:
            output_path: 輸出路徑
        """
        if not hasattr(self, 'invalid_addresses') or not self.invalid_addresses:
            logger.info("沒有無效地址需要導出")
            return
            
        df = pd.DataFrame(self.invalid_addresses)
        
        # 排序欄位
        columns = ["serial_number", "name", "raw_address", "reason"]
        df = df[columns]
        df.columns = ["序號", "姓名", "原始地址", "問題原因"]
        
        # 按序號排序
        df['序號_數字'] = pd.to_numeric(df['序號'], errors='coerce')
        df = df.sort_values('序號_數字').drop('序號_數字', axis=1)
        
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("無效地址報告已導出至: %s", output_path)
        logger.info("無效地址數: %d 筆", len(df))

    def export_cross_village_addresses(self, cross_village_data: List[Dict], output_path: str):
        """導出跨村里地址報告
        
        Args:
            cross_village_data: 跨村里地址列表
            output_path: 輸出路徑
        """
        if not cross_village_data:
            logger.info("沒有跨村里地址需要導出")
            return
            
        df = pd.DataFrame(cross_village_data)
        
        # 重新排序欄位
        columns = [
            "serial_number",
            "name",
            "full_address",
            "district",
            "village",
            "neighborhood",
            "longitude",
            "latitude",
        ]
        df = df[columns]
        df.columns = ["序號", "姓名", "完整地址", "區域", "村里", "鄰別", "經度", "緯度"]
        
        # 按村里和鄰別排序
        df = df.sort_values(["村里", "鄰別", "序號"])
        
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("跨村里地址報告已導出至: %s", output_path)
        logger.info("跨村里地址數: %d 筆", len(df))

    def query_address_coordinates(
        self, standardized_address: str, target_village: str = None
    ) -> Optional[Tuple[float, float]]:
        """查詢地址的經緯度（僅精確匹配）
        
        Args:
            standardized_address: 標準化後的地址
            target_village: 目標村里名稱，如果為None則使用預設村里
            
        Returns:
            經緯度座標元組，如果未找到則返回None
        """
        try:
            # 使用指定的村里或預設村里
            village = target_village if target_village else self.village
            
            # 僅進行精確匹配，不使用模糊匹配避免錯誤配對
            response = (
                self.supabase.table("addresses")
                .select("x_coord, y_coord")
                .eq("district", self.district)
                .eq("village", village)
                .eq("full_address", standardized_address)
                .execute()
            )

            if response.data:
                addr = response.data[0]
                return (float(addr["x_coord"]), float(addr["y_coord"]))

            # 找不到就返回None，不進行模糊匹配
            return None

        except Exception:
            logger.exception("查詢地址 %s 失敗", standardized_address)
            return None

    def query_neighborhood_by_address(self, standardized_address: str, target_village: str = None) -> Optional[int]:
        """通過地址查詢鄰別資訊
        
        Args:
            standardized_address: 標準化後的地址
            target_village: 目標村里名稱，如果為None則使用預設村里
            
        Returns:
            鄰別編號，如果未找到則返回None
        """
        try:
            # 使用指定的村里或預設村里
            village = target_village if target_village else self.village
            
            # 查詢資料庫中的鄰別資訊
            response = (
                self.supabase.table("addresses")
                .select("neighborhood")
                .eq("district", self.district)
                .eq("village", village)
                .eq("full_address", standardized_address)
                .execute()
            )

            if response.data:
                # 返回找到的鄰別
                return response.data[0]["neighborhood"]

            # 找不到就返回None
            return None

        except Exception:
            logger.exception("查詢地址 %s 的鄰別失敗", standardized_address)
            return None

    def process_data(
        self, 
        excel_path: str, 
        neighborhood_mapping: Optional[Dict[str, int]] = None
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """處理完整的數據流程
        
        Args:
            excel_path: Excel文件路徑
            neighborhood_mapping: 鄰別對應表，如果為None則使用預設
            
        Returns:
            (處理成功的數據, 未匹配的地址, 跨村里地址)
        """
        if neighborhood_mapping is None:
            neighborhood_mapping = get_neighborhood_mapping("standard")

        # 讀取Excel數據
        raw_data = self.read_excel_data(excel_path, neighborhood_mapping)

        processed_data = []
        unmatched_addresses = []
        cross_village_processed = []

        for item in raw_data:
            # 標準化地址
            if "standardized_address" in item:
                # 名冊格式已經標準化過了
                standardized_addr = item["standardized_address"]
            else:
                # 其他格式需要標準化
                standardized_addr = standardize_village_address(
                    item["original_address"], self.village
                )

            # 查詢經緯度
            coordinates = self.query_address_coordinates(standardized_addr)

            # 無論是否找到座標都加入 processed_data，座標留空則為 None
            processed_data.append(
                {
                    "serial_number": item["serial_number"],
                    "name": item["name"],
                    "full_address": standardized_addr,
                    "district": self.district,
                    "village": self.village,
                    "neighborhood": item["neighborhood"],
                    "longitude": coordinates[0] if coordinates else None,
                    "latitude": coordinates[1] if coordinates else None,
                },
            )
            
            # 如果沒有座標，記錄到未匹配列表
            if not coordinates:
                unmatched_addresses.append(
                    {
                        "serial_number": item["serial_number"],
                        "name": item["name"],
                        "original_address": item["original_address"],
                        "standardized_address": standardized_addr,
                        "neighborhood": item["neighborhood"],
                    },
                )

        # 處理跨村里地址（如果有的話）
        if hasattr(self, 'cross_village_data') and self.cross_village_data:
            for item in self.cross_village_data:
                # 從原始地址中提取村里名稱
                village_name = self._extract_village_name(item["original_address"])
                
                # 查詢跨村里地址的經緯度
                coordinates = self.query_address_coordinates(
                    item["standardized_address"], village_name
                )

                cross_village_processed.append(
                    {
                        "serial_number": item["serial_number"],
                        "name": item["name"],
                        "full_address": item["standardized_address"],
                        "district": self.district,
                        "village": village_name,
                        "neighborhood": item["neighborhood"],
                        "longitude": coordinates[0] if coordinates else None,
                        "latitude": coordinates[1] if coordinates else None,
                    },
                )

        # 記錄處理結果
        total_addresses = len(processed_data)
        matched_count = total_addresses - len(unmatched_addresses)
        logger.info("成功處理 %d 筆地址（匹配: %d, 未匹配: %d）", 
                   total_addresses, matched_count, len(unmatched_addresses))
        
        if cross_village_processed:
            logger.info("成功處理 %d 筆跨村里地址", len(cross_village_processed))
        
        if unmatched_addresses:
            logger.warning("未匹配到 %d 筆地址:", len(unmatched_addresses))
            for addr in unmatched_addresses:
                logger.warning(
                    "  鄰別%d: %s -> %s",
                    addr["neighborhood"],
                    addr["original_address"],
                    addr["standardized_address"]
                )

        return processed_data, unmatched_addresses, cross_village_processed

    def export_to_csv(
        self,
        processed_data: List[Dict],
        output_path: str,
        remove_duplicates: bool = False,
    ):
        """導出為CSV格式

        Args:
            processed_data: 處理後的數據
            output_path: 輸出路徑
            remove_duplicates: 是否去除重複地址（預設False，保留同門牌多戶）
        """
        df = pd.DataFrame(processed_data)

        # 重新排序欄位，包含序號和姓名
        columns = [
            "serial_number",
            "name",
            "full_address",
            "district",
            "village",
            "neighborhood",
            "longitude",
            "latitude",
        ]
        df = df[columns]
        df.columns = ["序號", "姓名", "完整地址", "區域", "村里", "鄰別", "經度", "緯度"]

        # 去重處理（如果需要）
        if remove_duplicates:
            original_count = len(df)
            df = df.drop_duplicates(["完整地址"], keep="first")
            removed_count = original_count - len(df)
            logger.info("去除重複地址: %d 筆", removed_count)

            # 修改輸出檔名
            if not output_path.endswith("_去重.csv"):
                output_path = output_path.replace(".csv", "_去重.csv")

        # 按鄰別和地址排序
        df = df.sort_values(["鄰別", "完整地址"])

        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("CSV文件已導出至: %s", output_path)
        logger.info("最終記錄數: %d 筆", len(df))

    def export_unmatched_report(
        self,
        unmatched_addresses: List[Dict],
        output_path: str,
    ):
        """導出未匹配地址報告
        
        Args:
            unmatched_addresses: 未匹配的地址列表
            output_path: 輸出路徑
        """
        if not unmatched_addresses:
            logger.info("沒有未匹配的地址，跳過報告生成")
            return
            
        df = pd.DataFrame(unmatched_addresses)
        
        # 排序欄位
        columns = [
            "serial_number",
            "name", 
            "neighborhood",
            "original_address",
            "standardized_address"
        ]
        df = df[columns]
        df.columns = ["序號", "姓名", "鄰別", "原始地址", "標準化地址"]
        
        # 按鄰別和序號排序
        df = df.sort_values(["鄰別", "序號"])
        
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("未匹配地址報告已導出至: %s", output_path)
        logger.info("未匹配地址數: %d 筆", len(df))


def main():
    """主函數，支援命令行參數"""
    parser = argparse.ArgumentParser(description="村里數據處理器")
    parser.add_argument("--district", default="七股區", help="區域名稱")
    parser.add_argument("--village", default="頂山里", help="村里名稱")
    parser.add_argument(
        "--excel-path", 
        default="data/頂山里200戶.xlsx", 
        help="Excel文件路徑"
    )
    parser.add_argument(
        "--output-path",
        help="輸出CSV文件路徑（自動生成如果未指定）"
    )
    parser.add_argument(
        "--remove-duplicates",
        action="store_true",
        help="去除重複地址（預設保留同門牌多戶）"
    )
    parser.add_argument(
        "--village-type",
        default="standard",
        choices=["standard", "numeric"],
        help="村里類型（影響鄰別對應表）"
    )
    parser.add_argument(
        "--include-cross-village",
        action="store_true",
        help="包含同區其他村里的地址處理並匹配座標"
    )

    args = parser.parse_args()

    # 設置日誌
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 創建處理器
    processor = VillageProcessor(args.district, args.village, args.include_cross_village)

    # 處理數據
    neighborhood_mapping = get_neighborhood_mapping(args.village_type)
    processed_data, unmatched, cross_village = processor.process_data(
        args.excel_path, neighborhood_mapping
    )

    # 生成輸出路徑
    if args.output_path is None:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        args.output_path = str(
            output_dir / f"{args.district}{args.village}地址處理結果.csv"
        )

    # 導出CSV
    processor.export_to_csv(processed_data, args.output_path, args.remove_duplicates)

    # 導出未匹配地址報告
    if unmatched:
        unmatched_report_path = args.output_path.replace(".csv", "_未匹配地址.csv")
        processor.export_unmatched_report(unmatched, unmatched_report_path)

    # 導出跨村里地址報告
    if cross_village:
        cross_village_path = args.output_path.replace(".csv", "_跨村里地址.csv")
        processor.export_cross_village_addresses(cross_village, cross_village_path)

    # 導出無效地址報告（如果有的話）
    if hasattr(processor, 'invalid_addresses') and processor.invalid_addresses:
        invalid_addresses_path = args.output_path.replace(".csv", "_無效地址.csv")
        processor.export_invalid_addresses(invalid_addresses_path)

    # 輸出統計資訊
    logger.info("處理完成!")
    total_count = len(processed_data)
    matched_count = total_count - len(unmatched)
    logger.info("總地址數: %d 筆", total_count)
    logger.info("匹配成功: %d 筆 (%.1f%%)", matched_count, matched_count/total_count*100 if total_count > 0 else 0)
    logger.info("未匹配: %d 筆 (%.1f%%)", len(unmatched), len(unmatched)/total_count*100 if total_count > 0 else 0)
    if cross_village:
        logger.info("跨村里地址: %d 筆", len(cross_village))
    if hasattr(processor, 'invalid_addresses') and processor.invalid_addresses:
        logger.info("無效地址: %d 筆", len(processor.invalid_addresses))

    if unmatched:
        logger.info("未匹配地址報告已生成: %s", unmatched_report_path)
    if cross_village:
        logger.info("跨村里地址報告已生成: %s", cross_village_path)
    if hasattr(processor, 'invalid_addresses') and processor.invalid_addresses:
        logger.info("無效地址報告已生成: %s", invalid_addresses_path)


if __name__ == "__main__":
    main()
