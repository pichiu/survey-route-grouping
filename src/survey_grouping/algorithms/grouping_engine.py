from collections import defaultdict

from ..config.settings import settings
from ..models.address import Address, AddressType
from ..models.group import RouteGroup
from .address_classifier import AddressClassifier
from .clustering import GeographicClustering
from .route_optimizer import RouteOptimizer


class GroupingEngine:
    def __init__(self, target_size: int = None):
        self.target_size = target_size or settings.default_group_size
        self.classifier = AddressClassifier()
        self.geo_clustering = GeographicClustering()
        self.route_optimizer = RouteOptimizer()

    def create_groups(
        self,
        addresses: list[Address],
        district: str,
        village: str,
    ) -> list[RouteGroup]:
        """主要分組邏輯"""

        # 1. 地址分類
        enriched_addresses = self.classifier.enrich_addresses(addresses)

        # 2. 按類型分組
        type_groups = self._group_by_type(enriched_addresses)

        # 3. 各類型內部聚類
        all_groups = []
        for addr_type, addr_list in type_groups.items():
            groups = self._process_address_type(addr_type, addr_list)
            all_groups.extend(groups)

        # 4. 生成分組 ID 和路線優化
        final_groups = []
        for i, group in enumerate(all_groups, 1):
            group_id = f"{district}{village}-{i:02d}"

            # 路線優化
            if group.addresses:
                if len(group.addresses) > 1:
                    optimized_route = self.route_optimizer.optimize_route(group.addresses)
                    group.route_order = optimized_route
                    
                    # 計算路線指標
                    metrics = self.route_optimizer.calculate_route_metrics(
                        group.addresses, group.route_order
                    )
                    group.estimated_distance = metrics["total_distance"]
                    group.estimated_time = metrics["estimated_time"]
                else:
                    # 單一地址的情況
                    group.route_order = [group.addresses[0].id]
                    group.estimated_distance = 0.0
                    group.estimated_time = 3  # 假設單一地址需要 3 分鐘

            group.group_id = group_id
            final_groups.append(group)

        return final_groups

    def _group_by_type(
        self,
        addresses: list[Address],
    ) -> dict[AddressType, list[Address]]:
        """按地址類型分組"""
        type_groups = defaultdict(list)
        for address in addresses:
            type_groups[address.address_type].append(address)
        return dict(type_groups)

    def _process_address_type(
        self,
        addr_type: AddressType,
        addresses: list[Address],
    ) -> list[RouteGroup]:
        """處理特定類型的地址"""

        if addr_type == AddressType.STREET:
            return self._process_street_addresses(addresses)
        if addr_type == AddressType.AREA:
            return self._process_area_addresses(addresses)
        return self._process_neighbor_addresses(addresses)

    def _process_street_addresses(self, addresses: list[Address]) -> list[RouteGroup]:
        """處理街道型地址"""
        # 按街道名稱分組
        street_groups = defaultdict(list)
        for addr in addresses:
            street_groups[addr.address_key].append(addr)

        result_groups = []
        for street, addr_list in street_groups.items():
            if len(addr_list) <= self.target_size:
                # 小街道直接成組
                result_groups.append(RouteGroup(addresses=addr_list, group_id=""))
            else:
                # 大街道需要細分
                sub_groups = self.geo_clustering.split_by_geography(
                    addr_list,
                    self.target_size,
                )
                result_groups.extend(sub_groups)

        return result_groups

    def _process_area_addresses(self, addresses: list[Address]) -> list[RouteGroup]:
        """處理地區型地址 - 主要靠地理聚類"""
        return self.geo_clustering.cluster_by_coordinates(addresses, self.target_size)

    def _process_neighbor_addresses(self, addresses: list[Address]) -> list[RouteGroup]:
        """處理鄰別型地址"""
        # 按鄰別分組，然後地理聚類
        neighbor_groups = defaultdict(list)
        for addr in addresses:
            neighbor_groups[addr.neighborhood].append(addr)

        result_groups = []
        for neighbor, addr_list in neighbor_groups.items():
            if len(addr_list) <= self.target_size:
                result_groups.append(RouteGroup(addresses=addr_list, group_id=""))
            else:
                sub_groups = self.geo_clustering.cluster_by_coordinates(
                    addr_list,
                    self.target_size,
                )
                result_groups.extend(sub_groups)

        return result_groups
