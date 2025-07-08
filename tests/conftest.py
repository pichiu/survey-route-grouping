"""pytest 配置檔案

提供測試用的 fixtures 和配置。
"""

import pytest
import csv
from datetime import datetime
from typing import List
from pathlib import Path
from pyproj import CRS, Transformer
from survey_grouping.models.address import Address, AddressType
from survey_grouping.models.group import RouteGroup, GroupingResult


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


def load_representative_sample_data() -> List[Address]:
    """載入代表性的 sample.csv 資料"""
    sample_file = Path("sample.csv")
    if not sample_file.exists():
        return get_default_test_addresses()

    # 設定座標轉換器
    twd97 = CRS.from_epsg(3826)  # TWD97 TM2
    wgs84 = CRS.from_epsg(4326)  # WGS84
    transformer = Transformer.from_crs(twd97, wgs84, always_xy=True)

    addresses = []
    try:
        with open(sample_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # 選擇代表性資料的索引
            representative_indices = [
                0,  # 基本地址：新營區三仙里17鄰三民路97之3號
                5,  # 有完整門牌：新營區三仙里17鄰三民路99號之7
                56,  # 有巷：新營區三仙里1鄰三民路138號之6
                150,  # 有巷弄：新營區三仙里16鄰三興街32巷1號
                170,  # 完整巷弄：新營區三仙里15鄰三興街144巷1弄1號
                300,  # 地區型：官田區渡拔里1鄰渡子頭1號之11
                320,  # 複雜地址：官田區渡拔里2鄰渡子頭25號之1
                200,  # 樓層地址：新營區三仙里4鄰三興街52之2號二樓之1
                400,  # 不同區域：官田區渡拔里3鄰渡子頭44號之1
                100,  # 中華路：新營區三仙里11鄰中華路33號
                250,  # 健康路：新營區三仙里3鄰健康路1號
                450,  # 八田路：官田區烏山頭里12鄰八田路三段水廠巷2號
                500,  # 嘉南：官田區烏山頭里11鄰嘉南1號之61
                350,  # 隆林路：官田區渡拔里24鄰隆林路760號
                15,  # 不同鄰別：新營區三仙里17鄰三民路101之15號
            ]

            for i, row in enumerate(reader):
                if i in representative_indices and len(addresses) < 15:
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
                            id=len(addresses) + 1,
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
        return get_default_test_addresses()

    return addresses if addresses else get_default_test_addresses()


def get_default_test_addresses() -> List[Address]:
    """提供預設測試資料（當 sample.csv 不可用時）"""
    return [
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
    ]


@pytest.fixture
def sample_addresses() -> List[Address]:
    """提供測試用的地址資料（使用真實 sample.csv 資料）"""
    return load_representative_sample_data()


@pytest.fixture
def sample_route_group(sample_addresses) -> RouteGroup:
    """提供測試用的路線分組"""
    return RouteGroup(
        group_id="G001",
        addresses=sample_addresses[:3],
        estimated_distance=500.0,
        estimated_time=30,
        route_order=[1, 2, 3],
        target_size=3,
    )


@pytest.fixture
def sample_grouping_result(sample_addresses) -> GroupingResult:
    """提供測試用的分組結果"""
    group1 = RouteGroup(
        group_id="G001",
        addresses=sample_addresses[:3],
        estimated_distance=500.0,
        estimated_time=30,
        route_order=[1, 2, 3],
        target_size=3,
    )

    group2 = RouteGroup(
        group_id="G002",
        addresses=sample_addresses[3:],
        estimated_distance=300.0,
        estimated_time=20,
        route_order=[4, 5],
        target_size=3,
    )

    return GroupingResult(
        district="安南區",
        village="安慶里",
        target_size=3,
        total_addresses=5,
        total_groups=2,
        groups=[group1, group2],
        created_at=datetime.now(),
    )


@pytest.fixture
def invalid_addresses() -> List[Address]:
    """提供測試用的無效地址資料"""
    return [
        Address(
            id=100,
            district="",  # 空的區域
            village="測試里",
            neighborhood=1,
            x_coord=None,  # 無座標
            y_coord=None,
            full_address="",  # 空的完整地址
        ),
        Address(
            id=101,
            district="測試區",
            village="",  # 空的村里
            neighborhood=0,  # 無效的鄰別
            x_coord=200.0,  # 超出台灣範圍的座標
            y_coord=50.0,
            full_address="無效地址",
        ),
    ]


@pytest.fixture
def mock_supabase_client():
    """模擬 Supabase 客戶端"""

    class MockSupabaseClient:
        def __init__(self):
            self.data = []

        def table(self, table_name):
            return MockTable(self.data)

        def rpc(self, function_name, params=None):
            return MockRPC()

    class MockTable:
        def __init__(self, data):
            self.data = data
            self._filters = {}

        def select(self, columns="*"):
            return self

        def eq(self, column, value):
            self._filters[column] = value
            return self

        def order(self, column, desc=False):
            return self

        def execute(self):
            return MockResponse(self.data)

    class MockRPC:
        def execute(self):
            return MockResponse([])

    class MockResponse:
        def __init__(self, data):
            self.data = data

    return MockSupabaseClient()


@pytest.fixture
def temp_output_dir(tmp_path):
    """提供臨時輸出目錄"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
