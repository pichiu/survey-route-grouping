import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler

from ..models.address import Address
from ..models.group import RouteGroup
from ..utils.geo_utils import GeoUtils


class GeographicClustering:
    def __init__(self):
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

        # 計算分組數量
        n_clusters = max(1, len(valid_addresses) // target_size)

        if n_clusters == 1:
            return [RouteGroup(addresses=valid_addresses, group_id="")]

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

        # K-means 聚類
        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(normalized_coords)

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
        """簡單的順序分割"""
        groups = []

        for i in range(0, len(addresses), target_size):
            group_addresses = addresses[i : i + target_size]
            groups.append(RouteGroup(addresses=group_addresses, group_id=""))

        return groups
