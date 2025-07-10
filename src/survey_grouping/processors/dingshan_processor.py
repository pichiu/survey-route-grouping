"""
頂山里數據處理器
處理頂山里200戶Excel數據, 進行地址標準化和Supabase匹配
"""
import logging
import re

import pandas as pd

from survey_grouping.database.connection import get_supabase_client

logger = logging.getLogger(__name__)


class DingshanProcessor:
    """頂山里數據處理器"""

    def __init__(self):
        self.supabase = get_supabase_client()
        self.neighborhood_mapping = {
            "第一鄰": 1,
            "第二鄰": 2,
            "第三鄰 ": 3,
            "第四鄰": 4,
            "第五鄰": 5,
            "第六鄰": 6,
            "第七鄰": 7,
            "第八鄰": 8,
        }

    def read_excel_data(self, excel_path: str) -> list[dict]:
        """讀取Excel文件中的所有鄰別數據"""
        all_data = []

        try:
            # 讀取所有工作表(除了空白)
            sheet_names = [
                "第一鄰",
                "第二鄰",
                "第三鄰 ",
                "第四鄰",
                "第五鄰",
                "第六鄰",
                "第七鄰",
                "第八鄰",
            ]
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
                        neighborhood_num = self.neighborhood_mapping[sheet_name]

                        for _, row in df.iterrows():
                            if (pd.notna(row["地址"]) and 
                                str(row["地址"]).strip()):
                                name = (
                                    str(row["姓名"]).strip()
                                    if pd.notna(row["姓名"])
                                    else ""
                                )
                                all_data.append(
                                    {
                                        "neighborhood": neighborhood_num,
                                        "name": name,
                                        "original_address": str(
                                            row["地址"]
                                        ).strip(),
                                        "sheet_name": sheet_name,
                                    },
                                )

                except Exception as e:
                    logger.warning("讀取工作表 %s 失敗: %s", sheet_name, e)
                    continue

            logger.info("成功讀取 %d 筆地址數據", len(all_data))
            return all_data

        except Exception:
            logger.exception("讀取Excel文件失敗")
            raise

    def standardize_address(self, original_address: str) -> str:
        """標準化地址格式

        轉換規則:
        - 頂山里1號 -> 頂山1號
        - 頂山里2-1號 -> 頂山2號之1
        """
        address = original_address.strip()

        # 移除'里'字
        address = address.replace("頂山里", "頂山")

        # 轉換門牌號格式: 2-1號 -> 2號之1
        pattern = r"(\d+)-(\d+)號"
        match = re.search(pattern, address)
        if match:
            main_num = match.group(1)
            sub_num = match.group(2)
            address = re.sub(
                pattern, f"{main_num}號之{sub_num}", address
            )

        return address

    def query_address_coordinates(
        self, standardized_address: str,
    ) -> tuple[float, float] | None:
        """查詢地址的經緯度"""
        try:
            # 精確匹配
            response = (
                self.supabase.table("addresses")
                .select("x_coord, y_coord")
                .eq("district", "七股區")
                .eq("village", "頂山里")
                .eq("full_address", standardized_address)
                .execute()
            )

            if response.data:
                addr = response.data[0]
                return (float(addr["x_coord"]), float(addr["y_coord"]))

            # 如果精確匹配失敗, 嘗試模糊匹配
            search_term = standardized_address.replace("號", "").replace("之", "")
            response = (
                self.supabase.table("addresses")
                .select("x_coord, y_coord, full_address")
                .eq("district", "七股區")
                .eq("village", "頂山里")
                .ilike("full_address", f"%{search_term}%")
                .execute()
            )

            if response.data:
                # 選擇最相似的地址
                best_match = response.data[0]
                msg = (
                    f"模糊匹配: {standardized_address} -> "
                    f"{best_match['full_address']}"
                )
                logger.info(msg)
                return (float(best_match["x_coord"]), float(best_match["y_coord"]))

            return None

        except Exception:
            logger.exception("查詢地址 %s 失敗", standardized_address)
            return None

    def process_data(self, excel_path: str) -> list[dict]:
        """處理完整的數據流程"""
        # 讀取Excel數據
        raw_data = self.read_excel_data(excel_path)

        processed_data = []
        unmatched_addresses = []

        for item in raw_data:
            # 標準化地址
            standardized_addr = self.standardize_address(item["original_address"])

            # 查詢經緯度
            coordinates = self.query_address_coordinates(standardized_addr)

            if coordinates:
                processed_data.append(
                    {
                        "group_id": (
                            f"七股區頂山里-{item['neighborhood']:02d}"
                        ),
                        "full_address": standardized_addr,
                        "district": "七股區",
                        "village": "頂山里",
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
                msg = (
                    f"  鄰別{addr['neighborhood']}: "
                    f"{addr['original_address']} -> "
                    f"{addr['standardized_address']}"
                )
                logger.warning(msg)

        return processed_data, unmatched_addresses

    def export_to_csv(
        self, 
        processed_data: list[dict], 
        output_path: str, 
        remove_duplicates: bool = False
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


def main(remove_duplicates: bool = False):
    """主函數
    
    Args:
        remove_duplicates: 是否去除重複地址（預設False）
    """
    processor = DingshanProcessor()

    # 處理數據
    excel_path = "data/頂山里200戶.xlsx"
    processed_data, unmatched = processor.process_data(excel_path)

    # 導出CSV
    output_path = "output/七股區頂山里分組結果.csv"
    processor.export_to_csv(processed_data, output_path, remove_duplicates)

    # 輸出統計資訊
    logger.info("處理完成!")
    logger.info("成功處理: %d 筆地址", len(processed_data))
    logger.info("未匹配: %d 筆地址", len(unmatched))

    if unmatched:
        logger.info("未匹配的地址:")
        for addr in unmatched:
            logger.info(
                "  鄰別%d: %s -> %s",
                addr['neighborhood'],
                addr['original_address'],
                addr['standardized_address']
            )


if __name__ == "__main__":
    main()
