"""
通用村里數據處理器
支援處理不同村里的Excel數據，進行地址標準化和Supabase匹配
"""
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from survey_grouping.database.connection import get_supabase_client
from survey_grouping.utils.address_utils import (
    create_group_id,
    extract_address_number,
    get_neighborhood_mapping,
    standardize_village_address,
    validate_address_format,
)

logger = logging.getLogger(__name__)


class VillageProcessor:
    """通用村里數據處理器"""

    def __init__(self, district: str, village: str):
        """初始化處理器
        
        Args:
            district: 區域名稱（如"七股區"）
            village: 村里名稱（如"頂山里"）
        """
        self.district = district
        self.village = village
        self.supabase = get_supabase_client()

    def read_excel_data(
        self, 
        excel_path: str, 
        neighborhood_mapping: Dict[str, int]
    ) -> List[Dict]:
        """讀取Excel文件中的所有鄰別數據
        
        Args:
            excel_path: Excel文件路徑
            neighborhood_mapping: 鄰別名稱到編號的對應字典
            
        Returns:
            處理後的數據列表
        """
        all_data = []

        try:
            sheet_names = list(neighborhood_mapping.keys())
            
            for sheet_name in sheet_names:
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
                                address = str(row["地址"]).strip()
                                
                                # 驗證地址格式
                                if validate_address_format(address):
                                    all_data.append(
                                        {
                                            "neighborhood": neighborhood_num,
                                            "name": name,
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

    def query_address_coordinates(
        self, standardized_address: str
    ) -> Optional[Tuple[float, float]]:
        """查詢地址的經緯度
        
        Args:
            standardized_address: 標準化後的地址
            
        Returns:
            經緯度座標元組，如果未找到則返回None
        """
        try:
            # 精確匹配
            response = (
                self.supabase.table("addresses")
                .select("x_coord, y_coord")
                .eq("district", self.district)
                .eq("village", self.village)
                .eq("full_address", standardized_address)
                .execute()
            )

            if response.data:
                addr = response.data[0]
                return (float(addr["x_coord"]), float(addr["y_coord"]))

            # 如果精確匹配失敗, 嘗試模糊匹配
            search_term = extract_address_number(standardized_address)
            response = (
                self.supabase.table("addresses")
                .select("x_coord, y_coord, full_address")
                .eq("district", self.district)
                .eq("village", self.village)
                .ilike("full_address", f"%{search_term}%")
                .execute()
            )

            if response.data:
                # 選擇最相似的地址
                best_match = response.data[0]
                logger.info(
                    "模糊匹配: %s -> %s",
                    standardized_address,
                    best_match["full_address"]
                )
                return (float(best_match["x_coord"]), float(best_match["y_coord"]))

            return None

        except Exception:
            logger.exception("查詢地址 %s 失敗", standardized_address)
            return None

    def process_data(
        self, 
        excel_path: str, 
        neighborhood_mapping: Optional[Dict[str, int]] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """處理完整的數據流程
        
        Args:
            excel_path: Excel文件路徑
            neighborhood_mapping: 鄰別對應表，如果為None則使用預設
            
        Returns:
            (處理成功的數據, 未匹配的地址)
        """
        if neighborhood_mapping is None:
            neighborhood_mapping = get_neighborhood_mapping("standard")

        # 讀取Excel數據
        raw_data = self.read_excel_data(excel_path, neighborhood_mapping)

        processed_data = []
        unmatched_addresses = []

        for item in raw_data:
            # 標準化地址
            standardized_addr = standardize_village_address(
                item["original_address"], self.village
            )

            # 查詢經緯度
            coordinates = self.query_address_coordinates(standardized_addr)

            if coordinates:
                processed_data.append(
                    {
                        "group_id": create_group_id(
                            self.district, self.village, item["neighborhood"]
                        ),
                        "full_address": standardized_addr,
                        "district": self.district,
                        "village": self.village,
                        "neighborhood": item["neighborhood"],
                        "longitude": coordinates[0],
                        "latitude": coordinates[1],
                        "original_address": item["original_address"],
                        "name": item["name"],
                    },
                )
            else:
                unmatched_addresses.append(
                    {
                        "original_address": item["original_address"],
                        "standardized_address": standardized_addr,
                        "neighborhood": item["neighborhood"],
                    },
                )

        # 記錄處理結果
        logger.info("成功處理 %d 筆地址", len(processed_data))
        if unmatched_addresses:
            logger.warning("未匹配到 %d 筆地址:", len(unmatched_addresses))
            for addr in unmatched_addresses:
                logger.warning(
                    "  鄰別%d: %s -> %s",
                    addr["neighborhood"],
                    addr["original_address"],
                    addr["standardized_address"]
                )

        return processed_data, unmatched_addresses

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

        # 重新排序欄位以符合test.csv格式
        columns = [
            "group_id",
            "full_address",
            "district",
            "village",
            "neighborhood",
            "longitude",
            "latitude",
        ]
        df = df[columns]
        df.columns = ["分組編號", "完整地址", "區域", "村里", "鄰別", "經度", "緯度"]

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

    args = parser.parse_args()

    # 設置日誌
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 創建處理器
    processor = VillageProcessor(args.district, args.village)

    # 處理數據
    neighborhood_mapping = get_neighborhood_mapping(args.village_type)
    processed_data, unmatched = processor.process_data(
        args.excel_path, neighborhood_mapping
    )

    # 生成輸出路徑
    if args.output_path is None:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        args.output_path = str(
            output_dir / f"{args.district}{args.village}分組結果.csv"
        )

    # 導出CSV
    processor.export_to_csv(processed_data, args.output_path, args.remove_duplicates)

    # 輸出統計資訊
    logger.info("處理完成!")
    logger.info("成功處理: %d 筆地址", len(processed_data))
    logger.info("未匹配: %d 筆地址", len(unmatched))

    if unmatched:
        logger.info("未匹配的地址:")
        for addr in unmatched:
            logger.info(
                "  鄰別%d: %s -> %s",
                addr["neighborhood"],
                addr["original_address"],
                addr["standardized_address"],
            )


if __name__ == "__main__":
    main()
