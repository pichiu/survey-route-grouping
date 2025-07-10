from collections import defaultdict

from ..config.settings import settings
from ..models.address import Address, AddressType
from ..models.group import RouteGroup
from ..models.strategy import GroupingStrategy, ClusteringAlgorithm
from .address_classifier import AddressClassifier
from .clustering import GeographicClustering
from .route_optimizer import RouteOptimizer


class GroupingEngine:
    def __init__(
        self, 
        target_size: int = None, 
        target_groups: int = None,
        grouping_strategy: GroupingStrategy = GroupingStrategy.AUTO,
        clustering_algorithm: ClusteringAlgorithm = ClusteringAlgorithm.KMEANS
    ):
        # 優先級：target_groups > target_size > 預設值
        if target_groups:
            self.target_groups = target_groups
            self.target_size = None  # 由組數推算
        else:
            self.target_size = target_size or settings.default_group_size
            self.target_groups = None
        
        self.grouping_strategy = grouping_strategy
        self.clustering_algorithm = clustering_algorithm
        
        self.classifier = AddressClassifier()
        self.geo_clustering = GeographicClustering(clustering_algorithm)
        self.route_optimizer = RouteOptimizer()

    def create_groups(
        self,
        addresses: list[Address],
        district: str,
        village: str,
    ) -> list[RouteGroup]:
        """主要分組邏輯"""

        # 根據分組策略選擇處理方式
        if self.target_groups:
            # 指定組數模式
            return self._create_groups_by_target_count(addresses, district, village)
        else:
            # 指定組大小模式，根據策略分組
            return self._create_groups_by_strategy(addresses, district, village)
    
    def _create_groups_by_strategy(
        self,
        addresses: list[Address],
        district: str,
        village: str,
    ) -> list[RouteGroup]:
        """根據指定策略進行分組"""
        
        if self.grouping_strategy == GroupingStrategy.AUTO:
            # 原有的智能分類邏輯
            enriched_addresses = self.classifier.enrich_addresses(addresses)
            type_groups = self._group_by_type(enriched_addresses)
            all_groups = []
            for addr_type, addr_list in type_groups.items():
                groups = self._process_address_type(addr_type, addr_list)
                all_groups.extend(groups)
        
        elif self.grouping_strategy == GroupingStrategy.GEOGRAPHIC:
            # 純地理聚類
            all_groups = self.geo_clustering.cluster_by_coordinates(addresses, self.target_size)
        
        elif self.grouping_strategy == GroupingStrategy.STREET_FIRST:
            # 優先按街道分組
            all_groups = self._group_by_street_first(addresses)
        
        elif self.grouping_strategy == GroupingStrategy.NEIGHBOR_FIRST:
            # 優先按鄰別分組
            all_groups = self._group_by_neighbor_first(addresses)
        
        elif self.grouping_strategy == GroupingStrategy.DISTANCE_BASED:
            # 基於距離的聚類
            all_groups = self.geo_clustering.split_by_geography(addresses, self.target_size)
        
        elif self.grouping_strategy == GroupingStrategy.SIMPLE:
            # 簡單平均分配
            all_groups = self.geo_clustering._simple_split(addresses, self.target_size)
        
        else:
            # 預設使用智能分類
            enriched_addresses = self.classifier.enrich_addresses(addresses)
            type_groups = self._group_by_type(enriched_addresses)
            all_groups = []
            for addr_type, addr_list in type_groups.items():
                groups = self._process_address_type(addr_type, addr_list)
                all_groups.extend(groups)

        # 生成分組 ID 和路線優化
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
    
    def _create_groups_by_target_count(
        self,
        addresses: list[Address],
        district: str,
        village: str,
    ) -> list[RouteGroup]:
        """基於目標組數的分組邏輯"""
        
        # 過濾有效座標的地址
        valid_addresses = [addr for addr in addresses if addr.has_valid_coordinates]
        invalid_addresses = [addr for addr in addresses if not addr.has_valid_coordinates]
        
        if not valid_addresses:
            # 如果沒有有效座標，只能簡單平均分組
            groups = self._simple_split_by_count(addresses, self.target_groups)
        else:
            # 使用地理聚類分組
            groups = self.geo_clustering.cluster_by_target_groups(
                valid_addresses, self.target_groups
            )
            
            # 將無效座標的地址分配到各組中
            if invalid_addresses:
                groups = self._distribute_invalid_addresses(groups, invalid_addresses)
        
        # 生成分組 ID 和路線優化
        final_groups = []
        for i, group in enumerate(groups, 1):
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
    
    def _simple_split_by_count(
        self,
        addresses: list[Address],
        target_groups: int,
    ) -> list[RouteGroup]:
        """簡單的按目標組數平均分割"""
        if not addresses or target_groups <= 0:
            return []
        
        total_addresses = len(addresses)
        base_size = total_addresses // target_groups
        remainder = total_addresses % target_groups
        
        groups = []
        start_idx = 0
        
        for i in range(target_groups):
            # 前 remainder 組多分配一個地址
            group_size = base_size + (1 if i < remainder else 0)
            end_idx = start_idx + group_size
            
            group_addresses = addresses[start_idx:end_idx]
            if group_addresses:  # 只有當組內有地址時才建立組
                groups.append(RouteGroup(addresses=group_addresses, group_id=""))
            
            start_idx = end_idx
        
        return groups
    
    def _distribute_invalid_addresses(
        self,
        groups: list[RouteGroup],
        invalid_addresses: list[Address],
    ) -> list[RouteGroup]:
        """將無效座標的地址均勻分配到各組中"""
        if not invalid_addresses or not groups:
            return groups
        
        # 按組大小順序分配，讓較小的組優先獲得無效地址
        groups_with_sizes = [(i, len(group.addresses)) for i, group in enumerate(groups)]
        groups_with_sizes.sort(key=lambda x: x[1])  # 按組大小排序
        
        # 輪流分配無效地址
        for i, addr in enumerate(invalid_addresses):
            group_idx = groups_with_sizes[i % len(groups_with_sizes)][0]
            groups[group_idx].addresses.append(addr)
        
        return groups
    
    def _group_by_street_first(self, addresses: list[Address]) -> list[RouteGroup]:
        """優先按街道分組的策略"""
        # 按街道名稱分組（從完整地址中提取街道部分）
        street_groups = defaultdict(list)
        
        for addr in addresses:
            # 簡單提取街道名稱（可以改進）
            street_key = self._extract_street_name(addr.full_address)
            street_groups[street_key].append(addr)
        
        result_groups = []
        for street, addr_list in street_groups.items():
            if len(addr_list) <= self.target_size:
                # 街道地址數量不超過目標大小，直接成組
                result_groups.append(RouteGroup(addresses=addr_list, group_id=""))
            else:
                # 街道地址太多，需要進一步地理聚類分割
                sub_groups = self.geo_clustering.cluster_by_coordinates(
                    addr_list, self.target_size
                )
                result_groups.extend(sub_groups)
        
        return result_groups
    
    def _group_by_neighbor_first(self, addresses: list[Address]) -> list[RouteGroup]:
        """優先按鄰別分組的策略"""
        # 按鄰別分組
        neighbor_groups = defaultdict(list)
        
        for addr in addresses:
            neighbor_groups[addr.neighborhood].append(addr)
        
        result_groups = []
        for neighbor, addr_list in neighbor_groups.items():
            if len(addr_list) <= self.target_size:
                # 鄰別地址數量不超過目標大小，直接成組
                result_groups.append(RouteGroup(addresses=addr_list, group_id=""))
            else:
                # 鄰別地址太多，需要進一步地理聚類分割
                sub_groups = self.geo_clustering.cluster_by_coordinates(
                    addr_list, self.target_size
                )
                result_groups.extend(sub_groups)
        
        return result_groups
    
    def _extract_street_name(self, full_address: str) -> str:
        """從完整地址中提取街道名稱"""
        # 簡單的街道名稱提取邏輯
        # 可以根據實際地址格式改進
        
        # 常見的街道關鍵字
        street_keywords = ["路", "街", "巷", "弄", "大道", "Avenue", "Street", "Road"]
        
        for keyword in street_keywords:
            if keyword in full_address:
                # 找到關鍵字的位置，提取街道部分
                parts = full_address.split(keyword)
                if len(parts) >= 2:
                    # 提取包含關鍵字的街道名稱部分
                    street_part = parts[0].split()[-1] + keyword if parts[0] else keyword
                    return street_part
        
        # 如果沒有找到街道關鍵字，使用前幾個字符作為分組依據
        return full_address[:5] if len(full_address) > 5 else full_address
