#!/usr/bin/env python3
"""地址重複檢查器

檢查同一地址的重複情況：
1. 同一地址，姓名相同（可能重複登記）
2. 同一地址，姓名不同（可能家庭成員或地址衝突）
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class AddressValidator:
    """地址重複檢查器"""
    
    def __init__(self):
        self.duplicate_same_name = []  # 同地址同姓名
        self.duplicate_different_name = []  # 同地址不同姓名
        
    def analyze_csv_file(self, csv_path: str) -> Tuple[List[Dict], List[Dict]]:
        """分析單個CSV檔案的地址重複情況
        
        Args:
            csv_path: CSV檔案路徑
            
        Returns:
            (同地址同姓名列表, 同地址不同姓名列表)
        """
        try:
            # 讀取CSV檔案
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            
            # 檢查必要欄位
            required_columns = ['完整地址', '姓名', '動線', '鄰']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"缺少必要欄位: {missing_columns}")
            
            logger.info(f"分析檔案: {csv_path}")
            logger.info(f"總計 {len(df)} 筆資料")
            
            # 按地址分組
            address_groups = df.groupby('完整地址')
            
            same_name_duplicates = []
            different_name_duplicates = []
            
            for address, group in address_groups:
                if len(group) > 1:  # 有重複地址
                    # 按姓名分組
                    name_groups = group.groupby('姓名')
                    
                    # 檢查同姓名重複
                    for name, name_group in name_groups:
                        if len(name_group) > 1:
                            # 同地址同姓名
                            for _, row in name_group.iterrows():
                                same_name_duplicates.append({
                                    '地址': address,
                                    '姓名': name,
                                    '動線': row['動線'],
                                    '鄰': row['鄰'],
                                    '編號': row.get('編號', ''),
                                    '經度': row.get('經度', ''),
                                    '緯度': row.get('緯度', ''),
                                    '重複次數': len(name_group)
                                })
                    
                    # 檢查不同姓名的同地址情況
                    if len(name_groups) > 1:
                        # 同地址不同姓名
                        for _, row in group.iterrows():
                            different_name_duplicates.append({
                                '地址': address,
                                '姓名': row['姓名'],
                                '動線': row['動線'],
                                '鄰': row['鄰'],
                                '編號': row.get('編號', ''),
                                '經度': row.get('經度', ''),
                                '緯度': row.get('緯度', ''),
                                '該地址總人數': len(group),
                                '該地址不同姓名數': len(name_groups)
                            })
            
            logger.info(f"發現同地址同姓名重複: {len(same_name_duplicates)} 筆")
            logger.info(f"發現同地址不同姓名: {len(different_name_duplicates)} 筆")
            
            return same_name_duplicates, different_name_duplicates
            
        except Exception as e:
            logger.error(f"分析檔案 {csv_path} 時發生錯誤: {e}")
            raise
    
    def generate_reports(self, village_name: str, same_name_data: List[Dict], 
                        different_name_data: List[Dict], output_dir: str = "output") -> Tuple[str, str]:
        """生成重複地址報告
        
        Args:
            village_name: 村里名稱
            same_name_data: 同地址同姓名資料
            different_name_data: 同地址不同姓名資料
            output_dir: 輸出目錄
            
        Returns:
            (同姓名報告路徑, 不同姓名報告路徑)
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 同地址同姓名報告
        same_name_file = output_path / f"{village_name}_同地址同姓名重複.csv"
        if same_name_data:
            same_name_df = pd.DataFrame(same_name_data)
            same_name_df.to_csv(same_name_file, index=False, encoding='utf-8-sig')
            logger.info(f"同地址同姓名報告已儲存: {same_name_file}")
        else:
            # 創建空報告
            pd.DataFrame(columns=['地址', '姓名', '動線', '鄰', '編號', '經度', '緯度', '重複次數']).to_csv(
                same_name_file, index=False, encoding='utf-8-sig')
            logger.info(f"無同地址同姓名重複，已建立空報告: {same_name_file}")
        
        # 同地址不同姓名報告
        different_name_file = output_path / f"{village_name}_同地址不同姓名.csv"
        if different_name_data:
            different_name_df = pd.DataFrame(different_name_data)
            different_name_df.to_csv(different_name_file, index=False, encoding='utf-8-sig')
            logger.info(f"同地址不同姓名報告已儲存: {different_name_file}")
        else:
            # 創建空報告
            pd.DataFrame(columns=['地址', '姓名', '動線', '鄰', '編號', '經度', '緯度', '該地址總人數', '該地址不同姓名數']).to_csv(
                different_name_file, index=False, encoding='utf-8-sig')
            logger.info(f"無同地址不同姓名情況，已建立空報告: {different_name_file}")
        
        return str(same_name_file), str(different_name_file)
    
    def validate_village(self, csv_path: str, village_name: str = None) -> Dict:
        """驗證單個村里的地址重複情況
        
        Args:
            csv_path: CSV檔案路徑
            village_name: 村里名稱（如果為None則從檔案名提取）
            
        Returns:
            驗證結果摘要
        """
        if village_name is None:
            # 從檔案名提取村里名稱
            filename = Path(csv_path).stem
            if '動線處理結果' in filename:
                village_name = filename.replace('動線處理結果', '').replace('七股區', '')
            else:
                village_name = filename
        
        # 分析檔案
        same_name_data, different_name_data = self.analyze_csv_file(csv_path)
        
        # 生成報告
        same_name_file, different_name_file = self.generate_reports(
            village_name, same_name_data, different_name_data
        )
        
        # 返回摘要
        return {
            'village_name': village_name,
            'total_same_name_duplicates': len(same_name_data),
            'total_different_name_addresses': len(set(item['地址'] for item in different_name_data)),
            'total_different_name_records': len(different_name_data),
            'same_name_report': same_name_file,
            'different_name_report': different_name_file
        }
    
    def batch_validate_villages(self, csv_files: List[str]) -> List[Dict]:
        """批次驗證多個村里
        
        Args:
            csv_files: CSV檔案路徑列表
            
        Returns:
            所有村里的驗證結果列表
        """
        results = []
        
        for csv_file in csv_files:
            try:
                result = self.validate_village(csv_file)
                results.append(result)
                logger.info(f"完成 {result['village_name']} 驗證")
            except Exception as e:
                logger.error(f"驗證 {csv_file} 時發生錯誤: {e}")
                continue
        
        return results
    
    def print_summary(self, results: List[Dict]):
        """列印驗證結果摘要
        
        Args:
            results: 驗證結果列表
        """
        print("\n" + "="*80)
        print("地址重複檢查結果摘要")
        print("="*80)
        
        total_same_name = 0
        total_different_name_addresses = 0
        total_different_name_records = 0
        
        for result in results:
            village = result['village_name']
            same_name = result['total_same_name_duplicates']
            diff_name_addr = result['total_different_name_addresses']
            diff_name_records = result['total_different_name_records']
            
            total_same_name += same_name
            total_different_name_addresses += diff_name_addr
            total_different_name_records += diff_name_records
            
            status_same = "✅ 無重複" if same_name == 0 else f"⚠️  {same_name} 筆重複"
            status_diff = "✅ 無衝突" if diff_name_records == 0 else f"⚠️  {diff_name_addr} 個地址有 {diff_name_records} 筆記錄"
            
            print(f"{village:12} | 同姓名重複: {status_same:15} | 不同姓名: {status_diff}")
        
        print("-" * 80)
        print(f"總計           | 同姓名重複: {total_same_name:3} 筆             | 不同姓名: {total_different_name_addresses} 個地址, {total_different_name_records} 筆記錄")
        print("="*80)


def main():
    """主程式：測試西寮里地址重複檢查"""
    logging.basicConfig(level=logging.INFO)
    
    validator = AddressValidator()
    
    # 測試西寮里
    csv_path = "output/七股區西寮里動線處理結果.csv"
    
    print("開始測試西寮里地址重複檢查...")
    result = validator.validate_village(csv_path)
    
    print(f"\n西寮里驗證完成:")
    print(f"- 同地址同姓名重複: {result['total_same_name_duplicates']} 筆")
    print(f"- 同地址不同姓名: {result['total_different_name_addresses']} 個地址，{result['total_different_name_records']} 筆記錄")
    print(f"- 報告檔案: {result['same_name_report']}, {result['different_name_report']}")


if __name__ == "__main__":
    main()