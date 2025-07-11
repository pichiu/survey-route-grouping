"""
動線數據處理器
處理已分組的動線Excel數據，進行地址標準化和Supabase匹配
基於VillageProcessor，專門處理動線格式的數據
"""
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from survey_grouping.processors.village_processor import VillageProcessor

logger = logging.getLogger(__name__)


class RouteProcessor(VillageProcessor):
    """動線數據處理器 - 繼承自VillageProcessor"""

    def __init__(self, district: str, village: str):
        """初始化動線處理器
        
        Args:
            district: 區域名稱（如"七股區"）
            village: 村里名稱（如"篤加里"）
        """
        super().__init__(district, village, include_cross_village=False)
        self.village_name_only = village.replace("里", "")  # 提取村里名稱（去除"里"）

    def read_route_excel_data(self, excel_path: str) -> List[Dict]:
        """讀取動線Excel文件中的所有動線數據
        
        Args:
            excel_path: Excel文件路徑
            
        Returns:
            處理後的動線數據列表
        """
        all_data = []
        invalid_addresses = []
        
        try:
            # 讀取Excel文件，獲取所有工作表名稱
            xl = pd.ExcelFile(excel_path)
            sheet_names = xl.sheet_names
            
            # 過濾掉核定名冊工作表
            route_sheets = [sheet for sheet in sheet_names if sheet != "核定名冊"]
            
            logger.info(f"發現 {len(route_sheets)} 個動線工作表: {route_sheets}")
            
            for sheet_index, sheet_name in enumerate(route_sheets, 1):
                route_name = f"{self.village_name_only}{sheet_index:02d}"
                logger.info(f"處理動線 {route_name} (工作表: {sheet_name})")
                
                # 讀取工作表數據，跳過標題行
                df = pd.read_excel(excel_path, sheet_name=sheet_name, skiprows=2)
                
                # 動態處理欄位名稱（適應不同欄位數量）
                if len(df.columns) >= 4:
                    # 取前4個欄位，忽略額外的空欄位
                    df = df.iloc[:, :4]
                    df.columns = ['編號', '鄉鎮市區_村里', '姓名', '通訊地址']
                else:
                    logger.warning(f"工作表 {sheet_name} 欄位數量不足: {len(df.columns)}")
                    continue
                
                # 處理每一行數據
                for index, row in df.iterrows():
                    if pd.isna(row['編號']) or pd.isna(row['姓名']) or pd.isna(row['通訊地址']):
                        continue
                    
                    serial_number = str(int(row['編號']))
                    name = str(row['姓名']).strip()
                    raw_address = str(row['通訊地址']).strip()
                    
                    # 處理地址
                    processed_data = self._process_route_address(
                        serial_number, name, raw_address, route_name
                    )
                    
                    if processed_data:
                        if processed_data.get('is_invalid'):
                            invalid_addresses.append({
                                'serial_number': serial_number,
                                'name': name,
                                'raw_address': raw_address,
                                'route_name': route_name,
                                'reason': processed_data['reason']
                            })
                        else:
                            all_data.append(processed_data)
                    
            logger.info(f"動線資料處理完成：有效地址 {len(all_data)} 筆，無效地址 {len(invalid_addresses)} 筆")
            
            # 保存無效地址報告
            if invalid_addresses:
                self._save_route_invalid_addresses(invalid_addresses)
            
        except Exception as e:
            logger.error(f"讀取動線Excel文件時發生錯誤: {e}")
            raise
        
        return all_data

    def _process_route_address(self, serial_number: str, name: str, raw_address: str, route_name: str) -> Optional[Dict]:
        """處理單個動線地址
        
        Args:
            serial_number: 序號
            name: 姓名
            raw_address: 原始地址
            route_name: 動線名稱
            
        Returns:
            處理後的地址數據或None
        """
        # 轉換全形數字
        address = convert_fullwidth_to_halfwidth(raw_address)
        
        # 移除台南市郵遞區號（如果存在）
        postal_code_pattern = r'^7\d{2,5}(?=臺南市|台南市)'
        if re.match(postal_code_pattern, address):
            address = re.sub(postal_code_pattern, '', address)
            logger.debug(f"移除台南市郵遞區號: {raw_address} -> {address}")
        
        # 檢查地址類型並處理
        if self._is_target_village_address(address):
            # 目標村里地址
            return self._process_target_village_address(serial_number, name, raw_address, address, route_name)
        elif self._is_simple_village_address(address):
            # 簡單村里地址（例如：1鄰西寮２號、西寮29號）
            return self._process_simple_village_address(serial_number, name, raw_address, address, route_name)
        elif self._is_different_village_address(address):
            # 不同村里的地址（例如：塩埕里的地址出現在七股里名單中）
            logger.warning(f"動線 {route_name} - 無效地址（非目標村里）: {address}")
            return {
                'is_invalid': True,
                'reason': f"非{self.district}{self.village}地址"
            }
        else:
            # 無效地址（非目標區域）
            logger.warning(f"動線 {route_name} - 無效地址（非目標區域或村里）: {address}")
            return {
                'is_invalid': True,
                'reason': f"非{self.district}{self.village}地址"
            }

    def _is_target_village_address(self, address: str) -> bool:
        """檢查是否為目標村里的完整地址"""
        return f"{self.district}" in address and f"{self.village}" in address

    def _is_simple_village_address(self, address: str) -> bool:
        """檢查是否為簡單村里地址（含鄰別或村里名稱）"""
        import re
        village_name_only = self.village.replace("里", "")
        
        # 如果地址中包含完整的村里名稱，則為簡單村里地址
        if f"{village_name_only}" in address:
            # 但要確保不是其他村里（例如：七股區塩埕里中的"七股"來自區名）
            # 檢查是否包含其他村里名稱
            village_pattern = r'[\u4e00-\u9fff]+里'
            villages_in_address = re.findall(village_pattern, address)
            
            # 如果找到其他村里名稱，且不是目標村里，則不是簡單村里地址
            if villages_in_address and self.village not in villages_in_address:
                return False
            
            return True
        
        # 檢查是否包含鄰別信息和村里名稱
        if re.search(r'\d+鄰', address) and village_name_only in address:
            return True
        
        # 檢查是否為純鄰別+門牌格式（如：1鄰2-7號）
        # 這種格式通常出現在單一村里的Excel檔案中
        if re.search(r'^\d+鄰\d+', address):
            return True
        
        return False
    
    def _is_different_village_address(self, address: str) -> bool:
        """檢查是否為不同村里的地址（包含區名但不是目標村里）"""
        # 檢查是否包含目標區域
        if f"{self.district}" not in address:
            return False
        
        # 檢查是否包含其他村里名稱（以"里"結尾）
        import re
        # 使用更寬泛的Unicode中文字符範圍
        village_pattern = r'[\u4e00-\u9fff]+里'
        villages_in_address = re.findall(village_pattern, address)
        
        # 如果找到村里名稱，但不是目標村里，則為不同村里地址
        if villages_in_address and self.village not in villages_in_address:
            return True
        
        return False

    def _process_target_village_address(self, serial_number: str, name: str, raw_address: str, address: str, route_name: str) -> Dict:
        """處理目標村里的完整地址"""
        # 提取鄰別信息
        neighborhood = self._extract_neighborhood_from_address(address)
        
        # 標準化地址
        standardized_addr = self._standardize_roster_address(address)
        
        # 如果沒有鄰別信息，嘗試從資料庫查詢
        if neighborhood is None or neighborhood == 0:
            logger.info(f"動線 {route_name} - 完整地址缺少鄰別資訊，嘗試從資料庫查詢: {address}")
            neighborhood = self.query_neighborhood_by_address(standardized_addr)
            
            if neighborhood is None:
                logger.warning(f"動線 {route_name} - 無法從資料庫查詢鄰別資訊: {address}")
                neighborhood = 0
            else:
                logger.info(f"動線 {route_name} - 成功從資料庫查詢到鄰別: {neighborhood}")
        
        return {
            'route_name': route_name,
            'district': self.district,
            'village': self.village,
            'neighborhood': neighborhood,
            'name': name,
            'serial_number': serial_number,
            'original_address': raw_address,
            'standardized_address': standardized_addr,
            'is_invalid': False
        }

    def _process_simple_village_address(self, serial_number: str, name: str, raw_address: str, address: str, route_name: str) -> Dict:
        """處理簡單村里地址"""
        # 提取鄰別信息
        neighborhood = self._extract_neighborhood_from_address(address)
        
        # 標準化地址
        standardized_addr = self._standardize_simple_village_address(address)
        
        # 如果沒有鄰別信息，嘗試從資料庫查詢
        if neighborhood is None or neighborhood == 0:
            logger.info(f"動線 {route_name} - 簡單地址缺少鄰別資訊，嘗試從資料庫查詢: {address}")
            neighborhood = self.query_neighborhood_by_address(standardized_addr)
            
            if neighborhood is None:
                logger.warning(f"動線 {route_name} - 無法從資料庫查詢鄰別資訊: {address}")
                neighborhood = 0
            else:
                logger.info(f"動線 {route_name} - 成功從資料庫查詢到鄰別: {neighborhood}")
        
        return {
            'route_name': route_name,
            'district': self.district,
            'village': self.village,
            'neighborhood': neighborhood,
            'name': name,
            'serial_number': serial_number,
            'original_address': raw_address,
            'standardized_address': standardized_addr,
            'is_invalid': False
        }

    def _standardize_simple_village_address(self, address: str) -> str:
        """標準化簡單村里地址"""
        # 移除鄰別信息，只保留地址部分
        # 例如：1鄰西寮２號 -> 西寮2號
        #      003鄰西寮16號 -> 西寮16號
        #      西寮29號 -> 西寮29號
        #      1鄰2-7號 -> 龍山2號之7（需要添加村里名稱）
        
        village_name_only = self.village.replace("里", "")
        
        # 移除鄰別前綴
        address = re.sub(r'^\d+鄰', '', address)
        
        # 如果地址不包含村里名稱，則添加村里名稱
        if village_name_only not in address and not re.search(r'[\u4e00-\u9fff]', address):
            # 純數字地址，添加村里名稱
            address = f"{village_name_only}{address}"
        
        # 標準化門牌號碼格式
        address = self._standardize_house_number(address)
        
        return address.strip()

    def _standardize_house_number(self, address: str) -> str:
        """標準化門牌號碼格式"""
        # 處理 - 轉換為 之
        address = re.sub(r'(\d+)-(\d+)號?', r'\1號之\2', address)
        
        # 確保主要號碼有"號"（但不要重複）
        if not re.search(r'\d+號', address):
            address = re.sub(r'(\d+)$', r'\1號', address)
        
        return address

    def _extract_neighborhood_from_address(self, address: str) -> Optional[int]:
        """從地址中提取鄰別編號（支援001鄰、010鄰等格式）
        
        Args:
            address: 完整地址
            
        Returns:
            鄰別編號或None
        """
        if not address:
            return None
        
        # 尋找鄰別模式：數字+鄰（支援001鄰、010鄰等格式）
        match = re.search(r'(\d+)鄰', address)
        if match:
            return int(match.group(1))
        
        return None

    def _save_route_invalid_addresses(self, invalid_addresses: List[Dict]) -> None:
        """儲存動線無效地址報告
        
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
            'route_name': '動線',
            'reason': '無效原因'
        })
        
        # 選擇需要的欄位
        columns_to_export = ['動線', '序號', '姓名', '原始地址', '無效原因']
        invalid_df = invalid_df[columns_to_export]
        
        # 產生輸出檔案名稱
        output_file = Path("output") / f"{self.district}{self.village}動線處理結果_無效地址.csv"
        output_file.parent.mkdir(exist_ok=True)
        
        # 儲存到 CSV 檔案
        invalid_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"無效地址報告已儲存至: {output_file}")

    async def process_route_data(self, excel_path: str, output_dir: str = "output") -> None:
        """處理動線數據並輸出結果
        
        Args:
            excel_path: Excel文件路徑
            output_dir: 輸出目錄
        """
        logger.info(f"開始處理動線數據: {excel_path}")
        
        # 讀取動線數據
        all_data = self.read_route_excel_data(excel_path)
        
        if not all_data:
            logger.warning("沒有找到有效的動線數據")
            return
        
        # 創建輸出目錄
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 準備輸出數據
        output_data = []
        unmatched_data = []
        
        for item in all_data:
            # 查詢座標
            coordinates = await self._query_coordinates(item['standardized_address'])
            
            base_record = {
                '動線': item['route_name'],
                '行政區': item['district'],
                '里': item['village'],
                '鄰': item['neighborhood'],
                '完整地址': item['standardized_address'],
                '姓名': item['name'],
                '經度': coordinates['longitude'] if coordinates else '',
                '緯度': coordinates['latitude'] if coordinates else '',
                '編號': item['serial_number']
            }
            
            # 所有有效地址都加入主要結果（包含未匹配到座標的）
            output_data.append(base_record)
            
            # 只有未匹配到座標的才加入未匹配清單
            if not coordinates:
                unmatched_record = {
                    '動線': item['route_name'],
                    '序號': item['serial_number'],
                    '姓名': item['name'],
                    '鄰別': item['neighborhood'],
                    '原始地址': item['original_address'],
                    '標準化地址': item['standardized_address']
                }
                unmatched_data.append(unmatched_record)
        
        # 儲存主要結果（包含所有有效地址）
        if output_data:
            output_df = pd.DataFrame(output_data)
            output_file = output_path / f"{self.district}{self.village}動線處理結果.csv"
            output_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            logger.info(f"動線處理結果已儲存至: {output_file}")
        
        # 儲存未匹配地址清單（僅用於參考，找不到座標的地址）
        if unmatched_data:
            unmatched_df = pd.DataFrame(unmatched_data)
            unmatched_file = output_path / f"{self.district}{self.village}動線處理結果_未匹配地址.csv"
            unmatched_df.to_csv(unmatched_file, index=False, encoding='utf-8-sig')
            logger.info(f"未匹配地址已儲存至: {unmatched_file}")
        
        # 統計輸出
        matched_count = len(output_data) - len(unmatched_data)
        logger.info(f"動線處理完成 - 總計: {len(output_data)} 筆，座標匹配: {matched_count} 筆，座標未匹配: {len(unmatched_data)} 筆")

    async def _query_coordinates(self, address: str) -> Optional[Dict]:
        """查詢地址座標
        
        Args:
            address: 標準化地址
            
        Returns:
            包含經度和緯度的字典，或None
        """
        try:
            response = (
                self.supabase.table("addresses")
                .select("x_coord, y_coord")
                .eq("district", self.district)
                .eq("village", self.village)
                .eq("full_address", address)
                .execute()
            )
            
            if response.data:
                data = response.data[0]
                return {
                    'longitude': data.get('x_coord'),
                    'latitude': data.get('y_coord')
                }
            return None
        except Exception as e:
            logger.error(f"查詢座標時發生錯誤: {e}")
            return None


def convert_fullwidth_to_halfwidth(text: str) -> str:
    """轉換全形數字為半形數字"""
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