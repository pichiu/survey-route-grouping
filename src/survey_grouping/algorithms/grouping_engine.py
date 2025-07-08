from typing import List, Dict
from collections import defaultdict
import numpy as np
from sklearn.cluster import KMeans
from ..models.address import Address, AddressType, RouteGroup
from ..config.settings import settings
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
        self, addresses: List[Address], district: str, village: str
    ) -> List[RouteGroup]:
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
            if group.addresses and len(group.addresses) > 1:
                optimized_route = self.route_optimizer.optimize_route(group.addresses)
                group.route_order = optimized_route

            group.group_id = group_id
            final_groups.append(group)

        return final_groups

    def _group_by_type(
        self, addresses: List[Address]
    ) -> Dict[AddressType, List[Address]]:
        """按地址類型分組"""
        type_groups = defaultdict(list)
        for address in addresses:
            type_groups[address.address_type].append(address)
        return dict(type_groups)

    def _process_address_type(
        self, addr_type: AddressType, addresses: List[Address]
    ) -> List[RouteGroup]:
        """處理特定類型的地址"""

        if addr_type == AddressType.STREET:
            return self._process_street_addresses(addresses)
        elif addr_type == AddressType.AREA:
            return self._process_area_addresses(addresses)
        else:
            return self._process_neighbor_addresses(addresses)

    def _process_street_addresses(self, addresses: List[Address]) -> List[RouteGroup]:
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
                    addr_list, self.target_size
                )
                result_groups.extend(sub_groups)

        return result_groups

    def _process_area_addresses(self, addresses: List[Address]) -> List[RouteGroup]:
        """處理地區型地址 - 主要靠地理聚類"""
        return self.geo_clustering.cluster_by_coordinates(addresses, self.target_size)

    def _process_neighbor_addresses(self, addresses: List[Address]) -> List[RouteGroup]:
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
                    addr_list, self.target_size
                )
                result_groups.extend(sub_groups)

        return result_groups
