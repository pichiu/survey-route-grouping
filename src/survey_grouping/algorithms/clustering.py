import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler

from ..models.address import Address
from ..models.group import RouteGroup
from ..models.strategy import ClusteringAlgorithm
from ..utils.geo_utils import GeoUtils


class GeographicClustering:
    def __init__(self, clustering_algorithm: ClusteringAlgorithm = ClusteringAlgorithm.KMEANS):
        self.clustering_algorithm = clustering_algorithm
        self.geo_utils = GeoUtils()

    def cluster_by_coordinates(
        self,
        addresses: list[Address],
        target_size: int,
    ) -> list[RouteGroup]:
        """基於座標的地理聚類"""

        # 過濾有效座標
        valid_addresses = [addr for addr in addresses if addr.has_valid_coordinates]

        if not valid_addresses:
            return [RouteGroup(addresses=addresses, group_id="")]

        # 計算分組數量 - 使用平均分配避免最後一組過少
        total_addresses = len(valid_addresses)
        n_clusters = max(1, round(total_addresses / target_size))
        
        # 如果只需要一組
        if n_clusters == 1:
            return [RouteGroup(addresses=valid_addresses, group_id="")]
        
        # 計算平均每組大小，避免最後一組過少
        avg_group_size = total_addresses / n_clusters
        min_group_size = int(avg_group_size * 0.8)  # 最小組大小為平均值的80%
        
        # 如果最後一組會太小，減少分組數量
        if total_addresses % n_clusters < min_group_size and n_clusters > 1:
            n_clusters -= 1

        # 準備座標資料 (經度, 緯度)
        coordinates = np.array([addr.coordinates for addr in valid_addresses])

        # WGS84 座標標準化 - 考慮緯度對距離的影響
        scaler = StandardScaler()
        # 對經度進行緯度加權，因為在不同緯度經度代表的實際距離不同
        avg_lat = np.mean(coordinates[:, 1])
        lat_weight = np.cos(np.radians(avg_lat))

        weighted_coords = coordinates.copy()
        weighted_coords[:, 0] *= lat_weight  # 經度加權

        normalized_coords = scaler.fit_transform(weighted_coords)

        # 根據選擇的演算法進行聚類
        try:
            if self.clustering_algorithm == ClusteringAlgorithm.KMEANS:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(normalized_coords)
            elif self.clustering_algorithm == ClusteringAlgorithm.DBSCAN:
                # DBSCAN 參數調整
                eps = 0.1  # 根據標準化後的座標調整
                min_samples = max(2, target_size // 8)
                dbscan = DBSCAN(eps=eps, min_samples=min_samples)
                cluster_labels = dbscan.fit_predict(normalized_coords)
                # 處理 DBSCAN 的噪音點(-1)
                unique_labels = set(cluster_labels)
                if -1 in unique_labels:
                    unique_labels.remove(-1)
                n_clusters = len(unique_labels)
            else:
                # 回退到簡單分割
                return self._simple_split(valid_addresses, target_size)

            # 組織分組結果
            groups = []
            for cluster_id in range(n_clusters):
                cluster_addresses = [
                    addr
                    for i, addr in enumerate(valid_addresses)
                    if cluster_labels[i] == cluster_id
                ]

                if cluster_addresses:
                    group = RouteGroup(addresses=cluster_addresses, group_id="")
                    # 計算組內緊密度
                    group.estimated_distance = (
                        self.geo_utils.calculate_group_compactness(cluster_addresses)
                    )
                    groups.append(group)

            return groups

        except Exception as e:
            # 聚類失敗時回退到簡單分組
            return self._simple_split(valid_addresses, target_size)

    def split_by_geography(
        self,
        addresses: list[Address],
        target_size: int,
    ) -> list[RouteGroup]:
        """按地理位置分割大群組"""

        if len(addresses) <= target_size:
            return [RouteGroup(addresses=addresses, group_id="")]

        # 使用 DBSCAN 進行密度聚類
        valid_addresses = [addr for addr in addresses if addr.has_valid_coordinates]

        if len(valid_addresses) < 2:
            return self._simple_split(addresses, target_size)

        coordinates = np.array([addr.coordinates for addr in valid_addresses])

        # DBSCAN 參數：eps 代表約 200 公尺的距離
        eps = 200 / 111320  # 轉換為度數近似值
        min_samples = max(2, target_size // 4)

        try:
            dbscan = DBSCAN(eps=eps, min_samples=min_samples)
            cluster_labels = dbscan.fit_predict(coordinates)

            groups = []

            # 處理各個聚類
            unique_labels = set(cluster_labels)
            for label in unique_labels:
                if label == -1:  # 噪音點
                    continue

                cluster_addresses = [
                    addr
                    for i, addr in enumerate(valid_addresses)
                    if cluster_labels[i] == label
                ]

                # 如果聚類太大，再次分割
                if len(cluster_addresses) > target_size * 1.5:
                    sub_groups = self.cluster_by_coordinates(
                        cluster_addresses,
                        target_size,
                    )
                    groups.extend(sub_groups)
                else:
                    groups.append(RouteGroup(addresses=cluster_addresses, group_id=""))

            # 處理噪音點
            noise_addresses = [
                addr
                for i, addr in enumerate(valid_addresses)
                if cluster_labels[i] == -1
            ]

            if noise_addresses:
                noise_groups = self._simple_split(noise_addresses, target_size)
                groups.extend(noise_groups)

            return groups

        except Exception:
            return self._simple_split(addresses, target_size)

    def _simple_split(
        self,
        addresses: list[Address],
        target_size: int,
    ) -> list[RouteGroup]:
        """簡單的平均分割"""
        if not addresses:
            return []
            
        total_addresses = len(addresses)
        n_groups = max(1, round(total_addresses / target_size))
        
        # 計算每組的平均大小
        base_size = total_addresses // n_groups
        remainder = total_addresses % n_groups
        
        groups = []
        start_idx = 0
        
        for i in range(n_groups):
            # 前 remainder 組多分配一個地址
            group_size = base_size + (1 if i < remainder else 0)
            end_idx = start_idx + group_size
            
            group_addresses = addresses[start_idx:end_idx]
            groups.append(RouteGroup(addresses=group_addresses, group_id=""))
            
            start_idx = end_idx
        
        return groups
    
    def cluster_by_target_groups(
        self,
        addresses: list[Address],
        target_groups: int,
    ) -> list[RouteGroup]:
        """基於目標組數進行地理聚類"""
        
        # 過濾有效座標
        valid_addresses = [addr for addr in addresses if addr.has_valid_coordinates]

        if not valid_addresses:
            return [RouteGroup(addresses=addresses, group_id="")]

        # 如果地址數量小於等於目標組數，每個地址一組
        if len(valid_addresses) <= target_groups:
            return [RouteGroup(addresses=[addr], group_id="") for addr in valid_addresses]
        
        # 確保組數不超過地址數量
        n_clusters = min(target_groups, len(valid_addresses))
        
        # 準備座標資料 (經度, 緯度)
        coordinates = np.array([addr.coordinates for addr in valid_addresses])

        # WGS84 座標標準化 - 考慮緯度對距離的影響
        scaler = StandardScaler()
        # 對經度進行緯度加權，因為在不同緯度經度代表的實際距離不同
        avg_lat = np.mean(coordinates[:, 1])
        lat_weight = np.cos(np.radians(avg_lat))

        weighted_coords = coordinates.copy()
        weighted_coords[:, 0] *= lat_weight  # 經度加權

        normalized_coords = scaler.fit_transform(weighted_coords)

        # 根據選擇的演算法進行聚類
        try:
            if self.clustering_algorithm == ClusteringAlgorithm.KMEANS:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(normalized_coords)
            elif self.clustering_algorithm == ClusteringAlgorithm.DBSCAN:
                # DBSCAN 參數調整
                eps = 0.1  # 根據標準化後的座標調整
                min_samples = max(2, target_size // 8)
                dbscan = DBSCAN(eps=eps, min_samples=min_samples)
                cluster_labels = dbscan.fit_predict(normalized_coords)
                # 處理 DBSCAN 的噪音點(-1)
                unique_labels = set(cluster_labels)
                if -1 in unique_labels:
                    unique_labels.remove(-1)
                n_clusters = len(unique_labels)
            else:
                # 回退到簡單分割
                return self._simple_split(valid_addresses, target_size)

            # 組織分組結果
            groups = []
            for cluster_id in range(n_clusters):
                cluster_addresses = [
                    addr
                    for i, addr in enumerate(valid_addresses)
                    if cluster_labels[i] == cluster_id
                ]

                if cluster_addresses:
                    group = RouteGroup(addresses=cluster_addresses, group_id="")
                    # 計算組內緊密度
                    group.estimated_distance = (
                        self.geo_utils.calculate_group_compactness(cluster_addresses)
                    )
                    groups.append(group)

            return groups

        except Exception as e:
            # 聚類失敗時回退到簡單分組
            return self._simple_split_by_target_groups(valid_addresses, target_groups)
    
    def _simple_split_by_target_groups(
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
