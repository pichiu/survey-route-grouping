"""pytest 配置檔案

提供測試用的 fixtures 和配置。
"""

import pytest
from datetime import datetime
from typing import List
from survey_grouping.models.address import Address, AddressType
from survey_grouping.models.group import RouteGroup, GroupingResult


@pytest.fixture
def sample_addresses() -> List[Address]:
    """提供測試用的地址資料"""
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
