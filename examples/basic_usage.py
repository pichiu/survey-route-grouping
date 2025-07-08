#!/usr/bin/env python3
"""基本使用範例

展示如何使用 survey-route-grouping 進行基本的地址分組。
"""

import asyncio
from datetime import datetime
from survey_grouping.models.address import Address
from survey_grouping.models.group import GroupingResult
from survey_grouping.algorithms.grouping_engine import GroupingEngine
from survey_grouping.algorithms.route_optimizer import RouteOptimizer
from survey_grouping.exporters.csv_exporter import CSVExporter


def create_sample_addresses():
    """建立範例地址資料（使用真實 sample.csv 資料）"""
    import csv
    from pathlib import Path
    from pyproj import CRS, Transformer

    def normalize_numbers(text: str) -> str:
        """將全形數字轉換為半形數字"""
        if not text:
            return text
        full_to_half_numbers = str.maketrans("０１２３４５６７８９", "0123456789")
        return text.translate(full_to_half_numbers)

    def generate_full_address(
        district: str,
        village: str,
        neighborhood: int,
        street: str = "",
        area: str = "",
        lane: str = "",
        alley: str = "",
        number: str = "",
    ) -> str:
        """生成完整地址"""
        parts = ["台南市", district, village, f"{neighborhood}鄰"]

        if street:
            parts.append(street)
        if area:
            parts.append(area)
        if lane:
            parts.append(f"{lane}巷")
        if alley:
            parts.append(f"{alley}弄")
        if number:
            parts.append(number)

        return "".join(parts)

    sample_file = Path("sample.csv")
    if not sample_file.exists():
        # 如果沒有 sample.csv，返回預設資料
        return [
            Address(
                id=1,
                district="新營區",
                village="三仙里",
                neighborhood=17,
                street="三民路",
                number="97之3號",
                x_coord=120.2436,
                y_coord=23.0478,
                full_address="台南市新營區三仙里17鄰三民路97之3號",
            ),
        ]

    # 設定座標轉換器
    twd97 = CRS.from_epsg(3826)  # TWD97 TM2
    wgs84 = CRS.from_epsg(4326)  # WGS84
    transformer = Transformer.from_crs(twd97, wgs84, always_xy=True)

    addresses = []
    try:
        with open(sample_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # 選擇前 10 筆作為範例
            for i, row in enumerate(reader):
                if i >= 10:
                    break

                try:
                    # 轉換 TWD97 座標為 WGS84
                    twd97_x = float(row["橫座標"])
                    twd97_y = float(row["縱座標"])
                    wgs84_lon, wgs84_lat = transformer.transform(twd97_x, twd97_y)

                    # 正規化文字（全形數字轉半形）
                    district = normalize_numbers(row["區"])
                    village = normalize_numbers(row["村里"])
                    neighborhood = int(normalize_numbers(row["鄰"]))
                    street = normalize_numbers(row["街、路段"])
                    area = normalize_numbers(row["地區"])
                    lane = normalize_numbers(row["巷"])
                    alley = normalize_numbers(row["弄"])
                    number = normalize_numbers(row["號"])

                    # 生成完整地址
                    full_address = generate_full_address(
                        district,
                        village,
                        neighborhood,
                        street,
                        area,
                        lane,
                        alley,
                        number,
                    )

                    address = Address(
                        id=i + 1,
                        district=district,
                        village=village,
                        neighborhood=neighborhood,
                        street=street or None,
                        area=area or None,
                        lane=lane or None,
                        alley=alley or None,
                        number=number or None,
                        x_coord=wgs84_lon,
                        y_coord=wgs84_lat,
                        full_address=full_address,
                    )
                    addresses.append(address)

                except (ValueError, KeyError) as e:
                    print(f"跳過無效資料行 {i}: {e}")
                    continue

    except Exception as e:
        print(f"載入 sample.csv 失敗: {e}")
        # 返回預設資料
        return [
            Address(
                id=1,
                district="新營區",
                village="三仙里",
                neighborhood=17,
                street="三民路",
                number="97之3號",
                x_coord=120.2436,
                y_coord=23.0478,
                full_address="台南市新營區三仙里17鄰三民路97之3號",
            ),
        ]

    return addresses


def main():
    """主要執行函數"""
    print("=== 台南市志工普查路線分組系統 - 基本使用範例 ===\n")

    # 1. 建立範例地址資料
    print("1. 建立範例地址資料...")
    addresses = create_sample_addresses()
    print(f"   建立了 {len(addresses)} 個地址")

    # 2. 設定分組參數
    target_size = 3  # 每組目標 3 個地址
    print(f"   目標分組大小: {target_size}")

    # 3. 執行地址分組
    print("\n2. 執行地址分組...")
    engine = GroupingEngine(target_size=target_size)
    
    # 取得第一個地址的區域和村里資訊
    if addresses:
        district = addresses[0].district
        village = addresses[0].village
    else:
        district = "新營區"
        village = "三仙里"
    
    groups = engine.create_groups(addresses, district, village)
    print(f"   分組完成，共產生 {len(groups)} 個分組")

    # 4. 路線優化
    print("\n3. 執行路線優化...")
    optimizer = RouteOptimizer(algorithm="nearest_neighbor")

    for i, group in enumerate(groups, 1):
        print(f"   優化第 {i} 組路線...")

        # 優化路線順序
        route_order = optimizer.optimize_route(group.addresses)
        group.route_order = route_order

        # 計算路線指標
        metrics = optimizer.calculate_route_metrics(group.addresses, route_order)
        group.estimated_distance = metrics["total_distance"]
        group.estimated_time = metrics["estimated_time"]

        print(f"     - 地址數量: {len(group.addresses)}")
        print(f"     - 預估距離: {group.estimated_distance:.1f} 公尺")
        print(f"     - 預估時間: {group.estimated_time} 分鐘")

    # 5. 建立分組結果
    print("\n4. 建立分組結果...")
    result = GroupingResult(
        district="安南區",
        village="安慶里",
        target_size=target_size,
        total_addresses=len(addresses),
        total_groups=len(groups),
        groups=groups,
        created_at=datetime.now(),
    )

    # 計算統計資訊
    result.calculate_statistics()

    print(f"   平均分組大小: {result.avg_group_size:.1f}")
    print(f"   最小分組: {result.min_group_size}")
    print(f"   最大分組: {result.max_group_size}")
    if result.total_estimated_distance:
        print(f"   總預估距離: {result.total_estimated_distance:.1f} 公尺")
    if result.total_estimated_time:
        print(f"   總預估時間: {result.total_estimated_time} 分鐘")

    # 6. 匯出結果
    print("\n5. 匯出結果...")

    # 匯出到 CSV
    csv_success = CSVExporter.export_grouping_result(
        result, "output/basic_usage_result.csv"
    )
    if csv_success:
        print("   ✓ CSV 匯出成功: output/basic_usage_result.csv")
    else:
        print("   ✗ CSV 匯出失敗")

    # 匯出摘要
    summary_success = CSVExporter.export_summary(
        result, "output/basic_usage_summary.csv"
    )
    if summary_success:
        print("   ✓ 摘要匯出成功: output/basic_usage_summary.csv")
    else:
        print("   ✗ 摘要匯出失敗")

    # 7. 顯示詳細結果
    print("\n6. 分組詳細結果:")
    for i, group in enumerate(groups, 1):
        print(f"\n   第 {i} 組 (ID: {group.group_id}):")
        print(f"   - 地址數量: {len(group.addresses)}")
        print(f"   - 預估距離: {group.estimated_distance:.1f} 公尺")
        print(f"   - 預估時間: {group.estimated_time} 分鐘")

        print("   - 包含地址:")
        for j, addr_id in enumerate(group.route_order, 1):
            addr = next(addr for addr in group.addresses if addr.id == addr_id)
            print(f"     {j}. {addr.full_address}")

    print("\n=== 基本使用範例完成 ===")


if __name__ == "__main__":
    main()
