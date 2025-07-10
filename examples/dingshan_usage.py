#!/usr/bin/env python3
"""
頂山里數據處理使用範例
展示如何使用DingshanProcessor處理頂山里200戶Excel數據
"""

import sys
from pathlib import Path

# 添加src路徑以便導入模組
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from survey_grouping.processors.dingshan_processor import DingshanProcessor


def main():
    """主函數"""
    print("=== 頂山里數據處理範例 ===")
    
    processor = DingshanProcessor()
    excel_path = "data/頂山里200戶.xlsx"
    
    # 處理數據
    print("正在處理Excel數據...")
    processed_data, unmatched = processor.process_data(excel_path)
    
    print(f"處理完成！成功處理 {len(processed_data)} 筆地址")
    if unmatched:
        print(f"未匹配 {len(unmatched)} 筆地址")
    
    # 範例1: 保留重複地址（預設，適合鄉下多戶同門牌情況）
    print("\n--- 範例1: 保留重複地址 ---")
    output_path1 = "output/頂山里_完整版.csv"
    processor.export_to_csv(processed_data, output_path1, remove_duplicates=False)
    
    # 範例2: 去除重複地址（適合需要唯一地址的情況）
    print("\n--- 範例2: 去除重複地址 ---")
    output_path2 = "output/頂山里_去重版.csv"
    processor.export_to_csv(processed_data, output_path2, remove_duplicates=True)
    
    print("\n=== 處理完成 ===")
    print("輸出文件:")
    print(f"  完整版: {output_path1}")
    print(f"  去重版: {output_path2}")


if __name__ == "__main__":
    main()
