"""模型測試

測試 Address、RouteGroup、GroupingResult 等模型。
"""

import pytest
from datetime import datetime
from survey_grouping.models.address import Address, AddressType
from survey_grouping.models.group import RouteGroup, GroupingResult


class TestAddress:
    """地址模型測試"""

    def test_address_creation(self):
        """測試地址建立"""
        address = Address(
            id=1,
            district="安南區",
            village="安慶里",
            neighborhood=1,
            street="安中路",
            x_coord=120.2436,
            y_coord=23.0478,
            full_address="台南市安南區安慶里1鄰安中路100號",
        )

        assert address.id == 1
        assert address.district == "安南區"
        assert address.village == "安慶里"
        assert address.neighborhood == 1
        assert address.has_valid_coordinates is True

    def test_coordinates_property(self):
        """測試座標屬性"""
        address = Address(
            id=1,
            district="安南區",
            village="安慶里",
            neighborhood=1,
            x_coord=120.2436,
            y_coord=23.0478,
            full_address="台南市安南區安慶里1鄰測試地址",
        )

        coords = address.coordinates
        assert coords == (120.2436, 23.0478)

    def test_invalid_coordinates(self):
        """測試無效座標"""
        address = Address(
            id=1,
            district="安南區",
            village="安慶里",
            neighborhood=1,
            x_coord=None,
            y_coord=None,
            full_address="台南市安南區安慶里1鄰測試地址",
        )

        assert address.has_valid_coordinates is False
        assert address.coordinates is None

    def test_distance_calculation(self):
        """測試距離計算"""
        addr1 = Address(
            id=1,
            district="安南區",
            village="安慶里",
            neighborhood=1,
            x_coord=120.2436,
            y_coord=23.0478,
            full_address="台南市安南區安慶里1鄰測試地址1",
        )

        addr2 = Address(
            id=2,
            district="安南區",
            village="安慶里",
            neighborhood=1,
            x_coord=120.2440,
            y_coord=23.0485,
            full_address="台南市安南區安慶里1鄰測試地址2",
        )

        distance = addr1.distance_to(addr2)
        assert distance is not None
        assert distance > 0
        assert distance < 1000  # 應該在 1 公里內

    def test_wgs84_point(self):
        """測試 WGS84 點座標"""
        address = Address(
            id=1,
            district="安南區",
            village="安慶里",
            neighborhood=1,
            x_coord=120.2436,
            y_coord=23.0478,
            full_address="台南市安南區安慶里1鄰測試地址",
        )

        point = address.wgs84_point
        assert point is not None
        assert point.x == 120.2436
        assert point.y == 23.0478


class TestRouteGroup:
    """路線分組測試"""

    def test_route_group_creation(self, sample_addresses):
        """測試路線分組建立"""
        group = RouteGroup(
            group_id="G001",
            addresses=sample_addresses[:3],
            estimated_distance=500.0,
            estimated_time=30,
        )

        assert group.group_id == "G001"
        assert group.size == 3
        assert group.estimated_distance == 500.0
        assert group.estimated_time == 30

    def test_center_coordinates(self, sample_addresses):
        """測試中心座標計算"""
        group = RouteGroup(
            group_id="G001",
            addresses=sample_addresses[:3],
        )

        center = group.center_coordinates
        assert center is not None
        assert len(center) == 2
        assert isinstance(center[0], float)
        assert isinstance(center[1], float)

    def test_coverage_area(self, sample_addresses):
        """測試覆蓋範圍計算"""
        group = RouteGroup(
            group_id="G001",
            addresses=sample_addresses[:3],
        )

        coverage = group.coverage_area
        assert coverage is not None
        assert len(coverage) == 4  # min_lat, min_lng, max_lat, max_lng

    def test_neighborhood_distribution(self, sample_addresses):
        """測試鄰別分布統計"""
        group = RouteGroup(
            group_id="G001",
            addresses=sample_addresses,
        )

        distribution = group.address_count_by_neighborhood
        assert isinstance(distribution, dict)
        assert len(distribution) > 0

    def test_route_distance_calculation(self, sample_addresses):
        """測試路線距離計算"""
        group = RouteGroup(
            group_id="G001",
            addresses=sample_addresses[:3],
            route_order=[1, 2, 3],
        )

        distance = group.calculate_route_distance()
        assert distance >= 0

    def test_route_optimization(self, sample_addresses):
        """測試路線優化"""
        group = RouteGroup(
            group_id="G001",
            addresses=sample_addresses[:3],
        )

        optimized_route = group.optimize_route_order()
        assert len(optimized_route) == 3
        assert all(addr_id in [1, 2, 3] for addr_id in optimized_route)

    def test_addresses_by_neighborhood(self, sample_addresses):
        """測試按鄰別取得地址"""
        group = RouteGroup(
            group_id="G001",
            addresses=sample_addresses,
        )

        neighborhood_1_addrs = group.get_addresses_by_neighborhood(1)
        assert len(neighborhood_1_addrs) == 2  # 根據測試資料


class TestGroupingResult:
    """分組結果測試"""

    def test_grouping_result_creation(self, sample_grouping_result):
        """測試分組結果建立"""
        result = sample_grouping_result

        assert result.district == "安南區"
        assert result.village == "安慶里"
        assert result.target_size == 3
        assert result.total_addresses == 5
        assert result.total_groups == 2
        assert len(result.groups) == 2

    def test_group_size_distribution(self, sample_grouping_result):
        """測試分組大小分布"""
        result = sample_grouping_result
        distribution = result.group_size_distribution

        assert "average" in distribution
        assert "minimum" in distribution
        assert "maximum" in distribution
        assert "total" in distribution
        assert distribution["total"] == 5

    def test_coverage_summary(self, sample_grouping_result):
        """測試覆蓋範圍摘要"""
        result = sample_grouping_result
        coverage = result.coverage_summary

        assert "total_addresses" in coverage
        assert "bounding_box" in coverage
        assert "center" in coverage

    def test_calculate_statistics(self, sample_grouping_result):
        """測試統計計算"""
        result = sample_grouping_result
        result.calculate_statistics()

        assert result.avg_group_size is not None
        assert result.min_group_size is not None
        assert result.max_group_size is not None

    def test_export_dict(self, sample_grouping_result):
        """測試匯出字典格式"""
        result = sample_grouping_result
        export_data = result.to_export_dict()

        assert "metadata" in export_data
        assert "groups" in export_data
        assert "coverage" in export_data

        metadata = export_data["metadata"]
        assert metadata["district"] == "安南區"
        assert metadata["village"] == "安慶里"
        assert metadata["target_size"] == 3


class TestAddressType:
    """地址類型測試"""

    def test_address_type_enum(self):
        """測試地址類型枚舉"""
        assert AddressType.STREET == "street"
        assert AddressType.AREA == "area"
        assert AddressType.NEIGHBOR == "neighbor"

    def test_address_with_type(self):
        """測試帶類型的地址"""
        address = Address(
            id=1,
            district="安南區",
            village="安慶里",
            neighborhood=1,
            address_type=AddressType.STREET,
            full_address="台南市安南區安慶里1鄰測試地址",
        )

        assert address.address_type == AddressType.STREET
