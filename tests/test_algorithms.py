"""演算法測試

測試路線優化、分組引擎、聚類等演算法。
"""

import pytest
from survey_grouping.algorithms.route_optimizer import RouteOptimizer
from survey_grouping.algorithms.grouping_engine import GroupingEngine
from survey_grouping.algorithms.clustering import GeographicClustering
from survey_grouping.models.address import Address


class TestRouteOptimizer:
    """路線優化器測試"""

    def test_nearest_neighbor_algorithm(self, sample_addresses):
        """測試最近鄰演算法"""
        optimizer = RouteOptimizer(algorithm="nearest_neighbor")
        route = optimizer.optimize_route(sample_addresses)

        assert len(route) == len(sample_addresses)
        assert all(addr.id in route for addr in sample_addresses)

    def test_genetic_algorithm(self, sample_addresses):
        """測試遺傳演算法"""
        optimizer = RouteOptimizer(algorithm="genetic")
        route = optimizer.optimize_route(sample_addresses)

        assert len(route) == len(sample_addresses)
        assert all(addr.id in route for addr in sample_addresses)

    def test_two_opt_algorithm(self, sample_addresses):
        """測試 2-opt 演算法"""
        optimizer = RouteOptimizer(algorithm="two_opt")
        route = optimizer.optimize_route(sample_addresses)

        assert len(route) == len(sample_addresses)
        assert all(addr.id in route for addr in sample_addresses)

    def test_empty_addresses(self):
        """測試空地址列表"""
        optimizer = RouteOptimizer()
        route = optimizer.optimize_route([])

        assert route == []

    def test_single_address(self, sample_addresses):
        """測試單一地址"""
        optimizer = RouteOptimizer()
        route = optimizer.optimize_route(sample_addresses[:1])

        assert len(route) == 1
        assert route[0] == sample_addresses[0].id

    def test_two_addresses(self, sample_addresses):
        """測試兩個地址"""
        optimizer = RouteOptimizer()
        route = optimizer.optimize_route(sample_addresses[:2])

        assert len(route) == 2
        assert all(addr.id in route for addr in sample_addresses[:2])

    def test_calculate_route_metrics(self, sample_addresses):
        """測試路線指標計算"""
        optimizer = RouteOptimizer()
        route_order = [addr.id for addr in sample_addresses]

        metrics = optimizer.calculate_route_metrics(sample_addresses, route_order)

        assert "total_distance" in metrics
        assert "estimated_time" in metrics
        assert "avg_distance_between_stops" in metrics
        assert "max_distance_between_stops" in metrics
        assert metrics["total_distance"] >= 0
        assert metrics["estimated_time"] >= 0

    def test_optimize_multiple_routes(self, sample_addresses):
        """測試多路線優化"""
        optimizer = RouteOptimizer()
        address_groups = [sample_addresses[:3], sample_addresses[3:]]

        results = optimizer.optimize_multiple_routes(address_groups)

        assert len(results) == 2
        for route_order, metrics in results:
            assert isinstance(route_order, list)
            assert isinstance(metrics, dict)

    def test_compare_algorithms(self, sample_addresses):
        """測試演算法比較"""
        optimizer = RouteOptimizer()
        results = optimizer.compare_algorithms(sample_addresses)

        assert "nearest_neighbor" in results
        assert "two_opt" in results
        assert "genetic" in results

        for algorithm, result in results.items():
            assert "route" in result
            assert "metrics" in result


class TestGroupingEngine:
    """分組引擎測試"""

    def test_grouping_engine_creation(self):
        """測試分組引擎建立"""
        engine = GroupingEngine(target_size=35)
        assert engine.target_size == 35

    def test_group_addresses_basic(self, sample_addresses):
        """測試基本地址分組"""
        engine = GroupingEngine(target_size=3)
        groups = engine.group_addresses(sample_addresses)

        assert len(groups) > 0
        total_addresses = sum(len(group.addresses) for group in groups)
        assert total_addresses == len(sample_addresses)

    def test_group_addresses_empty(self):
        """測試空地址分組"""
        engine = GroupingEngine(target_size=35)
        groups = engine.group_addresses([])

        assert groups == []

    def test_group_addresses_single(self, sample_addresses):
        """測試單一地址分組"""
        engine = GroupingEngine(target_size=35)
        groups = engine.group_addresses(sample_addresses[:1])

        assert len(groups) == 1
        assert len(groups[0].addresses) == 1

    def test_group_addresses_large_target(self, sample_addresses):
        """測試大目標分組"""
        engine = GroupingEngine(target_size=100)
        groups = engine.group_addresses(sample_addresses)

        # 所有地址應該在一個分組中
        assert len(groups) == 1
        assert len(groups[0].addresses) == len(sample_addresses)

    def test_group_addresses_small_target(self, sample_addresses):
        """測試小目標分組"""
        engine = GroupingEngine(target_size=1)
        groups = engine.group_addresses(sample_addresses)

        # 每個地址應該是一個分組
        assert len(groups) == len(sample_addresses)
        for group in groups:
            assert len(group.addresses) == 1


class TestGeographicClustering:
    """地理聚類測試"""

    def test_clustering_creation(self):
        """測試聚類器建立"""
        clustering = GeographicClustering()
        assert clustering is not None

    def test_cluster_by_coordinates(self, sample_addresses):
        """測試座標聚類"""
        clustering = GeographicClustering()
        groups = clustering.cluster_by_coordinates(sample_addresses, target_size=3)

        assert len(groups) > 0
        total_addresses = sum(len(group.addresses) for group in groups)
        assert total_addresses <= len(sample_addresses)  # 可能有些地址沒有座標

    def test_cluster_by_density(self, sample_addresses):
        """測試密度聚類"""
        clustering = GeographicClustering()
        groups = clustering.cluster_by_density(sample_addresses, target_size=3)

        assert len(groups) > 0
        total_addresses = sum(len(group.addresses) for group in groups)
        assert total_addresses <= len(sample_addresses)

    def test_cluster_empty_addresses(self):
        """測試空地址聚類"""
        clustering = GeographicClustering()
        groups = clustering.cluster_by_coordinates([], target_size=3)

        assert groups == []

    def test_cluster_single_address(self, sample_addresses):
        """測試單一地址聚類"""
        clustering = GeographicClustering()
        groups = clustering.cluster_by_coordinates(sample_addresses[:1], target_size=3)

        assert len(groups) == 1
        assert len(groups[0].addresses) == 1

    def test_cluster_no_coordinates(self):
        """測試無座標地址聚類"""
        addresses_no_coords = [
            Address(
                id=1,
                district="安南區",
                village="安慶里",
                neighborhood=1,
                x_coord=None,
                y_coord=None,
            )
        ]

        clustering = GeographicClustering()
        groups = clustering.cluster_by_coordinates(addresses_no_coords, target_size=3)

        # 應該回退到簡單分組
        assert len(groups) == 1
        assert len(groups[0].addresses) == 1


class TestAlgorithmIntegration:
    """演算法整合測試"""

    def test_full_pipeline(self, sample_addresses):
        """測試完整流程"""
        # 1. 分組
        engine = GroupingEngine(target_size=3)
        groups = engine.group_addresses(sample_addresses)

        assert len(groups) > 0

        # 2. 路線優化
        optimizer = RouteOptimizer()
        for group in groups:
            if group.addresses:
                route = optimizer.optimize_route(group.addresses)
                group.route_order = route

                # 3. 計算指標
                metrics = optimizer.calculate_route_metrics(group.addresses, route)
                group.estimated_distance = metrics["total_distance"]
                group.estimated_time = metrics["estimated_time"]

        # 驗證結果
        for group in groups:
            if group.addresses:
                assert group.route_order is not None
                assert len(group.route_order) == len(group.addresses)
                assert group.estimated_distance is not None
                assert group.estimated_time is not None

    def test_clustering_with_optimization(self, sample_addresses):
        """測試聚類與優化結合"""
        # 1. 地理聚類
        clustering = GeographicClustering()
        groups = clustering.cluster_by_coordinates(sample_addresses, target_size=3)

        # 2. 路線優化
        optimizer = RouteOptimizer()
        for group in groups:
            if group.addresses:
                route = optimizer.optimize_route(group.addresses)
                group.route_order = route

        # 驗證結果
        for group in groups:
            if group.addresses:
                assert group.route_order is not None
                assert len(group.route_order) == len(group.addresses)

    def test_algorithm_performance_comparison(self, sample_addresses):
        """測試演算法效能比較"""
        optimizer = RouteOptimizer()

        # 比較不同演算法
        algorithms = ["nearest_neighbor", "two_opt", "genetic"]
        results = {}

        for algorithm in algorithms:
            optimizer.algorithm = algorithm
            route = optimizer.optimize_route(sample_addresses)
            metrics = optimizer.calculate_route_metrics(sample_addresses, route)
            results[algorithm] = metrics["total_distance"]

        # 驗證所有演算法都產生了結果
        assert len(results) == 3
        for distance in results.values():
            assert distance >= 0
