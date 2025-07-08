import typer
from rich.console import Console
from rich.table import Table

from .algorithms.grouping_engine import GroupingEngine
from .database.connection import get_supabase_client, test_supabase_connection
from .database.queries import AddressQueries
from .exporters.csv_exporter import CSVExporter
from .exporters.excel_exporter import ExcelExporter
from .models.address import RouteGroup

app = typer.Typer(help="台南市志工普查路線分組系統")
console = Console()


@app.command()
def test_connection():
    """測試 Supabase 資料庫連接"""

    console.print("🔗 測試 Supabase 連接...")

    try:
        from .database.connection import get_supabase_client, test_supabase_connection
        from .database.queries import AddressQueries

        # 基本連接測試
        if not test_supabase_connection():
            console.print("❌ 基本連接測試失敗")
            return

        console.print("✅ 基本連接測試成功")

        # 詳細功能測試
        client = get_supabase_client()
        queries = AddressQueries(client)

        # 測試統計查詢
        console.print("📊 測試統計查詢...")
        response = client.table("address_stats").select("*").limit(5).execute()
        console.print(f"   找到 {len(response.data)} 筆統計資料")

        # 測試地址查詢
        console.print("🏠 測試地址查詢...")
        response = client.table("addresses").select("district").limit(10).execute()

        if response.data:
            districts = list(set(addr["district"] for addr in response.data))
            console.print(f"   找到行政區: {', '.join(districts[:3])}...")

        console.print("🎉 所有連接測試通過！")

    except Exception as e:
        console.print(f"❌ 連接測試失敗: {e}")
        console.print("\n💡 請檢查:")
        console.print("1. .env 檔案是否存在且設定正確")
        console.print("2. SUPABASE_URL 和 SUPABASE_KEY 是否有效")
        console.print("3. 網路連接是否正常")


@app.command()
def setup_env():
    """設置環境變數的互動式指南"""

    import os
    from pathlib import Path

    console.print("🔧 Supabase 環境設置指南")
    console.print()

    # 檢查是否已有 .env 檔案
    env_file = Path(".env")
    if env_file.exists():
        console.print("⚠️ .env 檔案已存在")
        overwrite = typer.confirm("是否要覆寫現有設定？")
        if not overwrite:
            return

    console.print("請從 Supabase Dashboard 取得以下資訊:")
    console.print("1. 前往 https://supabase.com/dashboard")
    console.print("2. 選擇您的專案")
    console.print("3. 前往 Settings > API")
    console.print()

    # 互動式輸入
    url = typer.prompt("請輸入 Project URL")
    if not url.startswith("https://"):
        url = f"https://{url}"

    anon_key = typer.prompt("請輸入 anon/public Key")

    service_key = typer.prompt(
        "請輸入 service_role Key (可選，按 Enter 跳過)",
        default="",
        show_default=False,
    )

    # 寫入 .env 檔案
    env_content = f"""# Supabase 設定
SUPABASE_URL={url}
SUPABASE_KEY={anon_key}
"""

    if service_key:
        env_content += f"SUPABASE_SERVICE_KEY={service_key}\n"

    env_content += """
# 分組參數
DEFAULT_GROUP_SIZE=35
MIN_GROUP_SIZE=25
MAX_GROUP_SIZE=45

# 地理參數
MAX_DISTANCE_THRESHOLD=500.0
CLUSTERING_ALGORITHM=kmeans

# 系統設定
DEBUG=false
LOG_LEVEL=INFO
"""

    try:
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_content)

        console.print("✅ .env 檔案建立成功！")
        console.print("🔗 正在測試連接...")

        # 重新載入設定並測試
        os.environ.clear()
        from .config.settings import Settings

        settings = Settings()

        if test_supabase_connection():
            console.print("🎉 設定完成且連接正常！")
        else:
            console.print("❌ 連接測試失敗，請檢查設定")

    except Exception as e:
        console.print(f"❌ 建立 .env 檔案失敗: {e}")


@app.command()
def analyze_density(
    district: str = typer.Argument(..., help="行政區名稱"),
    village: str | None = typer.Option(None, help="村里名稱（可選）"),
):
    """分析指定區域的地址密度"""

    try:
        supabase = get_supabase_client()
        queries = AddressQueries(supabase)

        stats = queries.get_address_density_stats(district, village)

        area_info = f"{district}"
        if village:
            area_info += f" {village}"

        console.print(f"📊 {area_info} 地址密度分析")
        console.print(f"總地址數: {stats['total_addresses']:,}")
        console.print(f"覆蓋面積: {stats['area_km2']} 平方公里")
        console.print(f"密度: {stats['density_per_km2']} 地址/平方公里")

        if "coordinate_bounds" in stats:
            bounds = stats["coordinate_bounds"]
            console.print(
                f"經度範圍: {bounds['min_lon']:.6f} ~ {bounds['max_lon']:.6f}",
            )
            console.print(
                f"緯度範圍: {bounds['min_lat']:.6f} ~ {bounds['max_lat']:.6f}",
            )

    except Exception as e:
        console.print(f"❌ 分析失敗: {e}")


@app.command()
def validate_coordinates(
    district: str = typer.Argument(..., help="行政區名稱"),
    village: str = typer.Argument(..., help="村里名稱"),
):
    """驗證座標資料品質"""

    try:
        supabase = get_supabase_client()
        queries = AddressQueries(supabase)

        addresses = queries.get_addresses_by_village(district, village)

        total = len(addresses)
        valid_coords = sum(1 for addr in addresses if addr.has_valid_coordinates)
        invalid_coords = total - valid_coords

        console.print(f"🔍 {district} {village} 座標驗證結果")
        console.print(f"總地址數: {total}")
        console.print(f"有效座標: {valid_coords} ({valid_coords/total*100:.1f}%)")
        console.print(f"無效座標: {invalid_coords} ({invalid_coords/total*100:.1f}%)")

        if invalid_coords > 0:
            console.print("\n❌ 無效座標的地址範例:")
            invalid_addrs = [
                addr for addr in addresses if not addr.has_valid_coordinates
            ]
            for addr in invalid_addrs[:5]:
                console.print(f"  - ID {addr.id}: {addr.full_address}")

    except Exception as e:
        console.print(f"❌ 驗證失敗: {e}")


@app.command()
def batch_process(
    district: str = typer.Argument(..., help="行政區名稱"),
    target_size: int | None = typer.Option(35, help="每組目標人數"),
    output_dir: str = typer.Option("./output", help="輸出目錄"),
):
    """批次處理整個行政區的所有村里"""

    import os
    from pathlib import Path

    try:
        # 建立輸出目錄
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        supabase = get_supabase_client()
        queries = AddressQueries(supabase)

        # 取得該區所有村里
        response = (
            supabase.table("addresses")
            .select("village")
            .eq("district", district)
            .execute()
        )

        villages = list(set(addr["village"] for addr in response.data))

        console.print(f"🏘️ 開始批次處理 {district} 的 {len(villages)} 個村里...")

        for village in villages:
            console.print(f"\n處理 {village}...")

            try:
                addresses = queries.get_addresses_by_village(district, village)

                if not addresses:
                    console.print(f"  ⚠️ {village} 無地址資料")
                    continue

                engine = GroupingEngine(target_size=target_size)
                groups = engine.create_groups(addresses, district, village)

                # 輸出檔案
                output_file = os.path.join(
                    output_dir,
                    f"{district}_{village}_分組.xlsx",
                )
                export_groups(groups, "excel", output_file)

                console.print(
                    f"  ✅ {village}: {len(groups)} 組, {len(addresses)} 門牌",
                )

            except Exception as e:
                console.print(f"  ❌ {village} 處理失敗: {e}")

        console.print(f"\n🎉 批次處理完成！結果儲存在 {output_dir}")

    except Exception as e:
        console.print(f"❌ 批次處理失敗: {e}")


@app.command()
def create_groups(
    district: str = typer.Argument(..., help="行政區名稱，如：新營區"),
    village: str = typer.Argument(..., help="村里名稱，如：三仙里"),
    target_size: int | None = typer.Option(35, help="每組目標人數"),
    output_format: str = typer.Option("csv", help="輸出格式: csv, excel, json"),
    output_file: str | None = typer.Option(None, help="輸出檔案名稱"),
):
    """為指定村里建立志工普查路線分組"""

    console.print(f"🏠 開始處理 {district} {village} 的普查路線分組...")

    try:
        # 1. 連接資料庫
        supabase = get_supabase_client()
        queries = AddressQueries(supabase)

        # 2. 查詢地址資料
        addresses = queries.get_addresses_by_village(district, village)
        console.print(f"📍 找到 {len(addresses)} 筆地址")

        if not addresses:
            console.print("❌ 找不到符合條件的地址資料")
            return

        # 3. 執行分組
        engine = GroupingEngine(target_size=target_size)
        groups = engine.create_groups(addresses, district, village)

        # 4. 顯示結果
        display_groups_summary(groups)

        # 5. 輸出檔案
        if output_file:
            export_groups(groups, output_format, output_file)
            console.print(f"✅ 結果已輸出至 {output_file}")

    except Exception as e:
        console.print(f"❌ 處理失敗: {e}")


def display_groups_summary(groups: list[RouteGroup]):
    """顯示分組摘要"""
    table = Table(title="普查路線分組結果")
    table.add_column("組別", style="cyan")
    table.add_column("門牌數", justify="right")
    table.add_column("預估距離", justify="right")
    table.add_column("地址範例", style="dim")

    for group in groups:
        example_addr = group.addresses[0].full_address if group.addresses else "無"
        distance = (
            f"{group.estimated_distance:.0f}m" if group.estimated_distance else "未計算"
        )

        table.add_row(
            group.group_id,
            str(group.size),
            distance,
            example_addr[:30] + "..." if len(example_addr) > 30 else example_addr,
        )

    console.print(table)
    console.print(f"\n📊 總計: {len(groups)} 組, {sum(g.size for g in groups)} 個門牌")


def export_groups(groups: list[RouteGroup], format_type: str, output_file: str):
    """輸出分組結果"""
    if format_type.lower() == "excel":
        exporter = ExcelExporter()
        exporter.export(groups, output_file)
    elif format_type.lower() == "csv":
        exporter = CSVExporter()
        exporter.export(groups, output_file)
    else:
        raise ValueError(f"不支援的輸出格式: {format_type}")


if __name__ == "__main__":
    app()
