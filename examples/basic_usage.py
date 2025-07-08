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
    """建立範例地址資料"""
    addresses = [
        Address(
            id=1,
            district="安南區",
            village="安慶里",
            neighborhood=1,
            street="安中路",
            area="一段",
            number="100號",
            x_coord=120.2436,
            y_coord=23.0478,
            full_address="台南市安南區安慶里1鄰安中路一段100號",
        ),
        Address(
            id=2,
            district="安南區",
            village="安慶里",
            neighborhood=1,
            street="安中路",
            area="一段",
            number="102號",
            x_coord=120.2438,
            y_coord=23.0480,
            full_address="台南市安南區安慶里1鄰安中路一段102號",
        ),
        Address(
            id=3,
            district="安南區",
            village="安慶里",
            neighborhood=2,
            street="安中路",
            area="一段",
            number="200號",
            x_coord=120.2440,
            y_coord=23.0485,
            full_address="台南市安南區安慶里2鄰安中路一段200號",
        ),
        Address(
            id=4,
            district="安南區",
            village="安慶里",
            neighborhood=2,
            street="安中路",
            area="一段",
            number="202號",
            x_coord=120.2442,
            y_coord=23.0487,
            full_address="台南市安南區安慶里2鄰安中路一段202號",
        ),
        Address(
            id=5,
            district="安南區",
            village="安慶里",
            neighborhood=3,
            street="安中路",
            area="一段",
            number="300號",
            x_coord=120.2445,
            y_coord=23.0490,
            full_address="台南市安南區安慶里3鄰安中路一段300號",
        ),
        Address(
            id=6,
            district="安南區",
            village="安慶里",
            neighborhood=3,
            street="安中路",
            area="一段",
            number="302號",
            x_coord=120.2447,
            y_coord=23.0492,
            full_address="台南市安南區安慶里3鄰安中路一段302號",
        ),
        Address(
            id=7,
            district="安南區",
            village="安慶里",
            neighborhood=4,
            street="安中路",
            area="一段",
            number="400號",
            x_coord=120.2450,
            y_coord=23.0495,
            full_address="台南市安南區安慶里4鄰安中路一段400號",
        ),
        Address(
            id=8,
            district="安南區",
            village="安慶里",
            neighborhood=4,
            street="安中路",
            area="一段",
            number="402號",
            x_coord=120.2452,
            y_coord=23.0497,
            full_address="台南市安南區安慶里4鄰安中路一段402號",
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
    groups = engine.group_addresses(addresses)
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
