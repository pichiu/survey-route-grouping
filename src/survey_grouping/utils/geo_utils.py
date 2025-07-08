from geopy.distance import geodesic

from ..models.address import Address


class GeoUtils:
    @staticmethod
    def calculate_distance(
        coord1: tuple[float, float],
        coord2: tuple[float, float],
    ) -> float:
        """計算兩點間的地理距離 (公尺)"""
        return geodesic(coord1, coord2).meters

    @staticmethod
    def calculate_centroid(addresses: list[Address]) -> tuple[float, float]:
        """計算地址群的地理中心點"""
        valid_coords = [
            addr.coordinates for addr in addresses if addr.has_valid_coordinates
        ]

        if not valid_coords:
            raise ValueError("沒有有效的座標資料")

        # WGS84 座標系統使用經緯度平均計算中心點
        avg_lat = sum(coord[1] for coord in valid_coords) / len(valid_coords)
        avg_lon = sum(coord[0] for coord in valid_coords) / len(valid_coords)

        return (avg_lon, avg_lat)

    @staticmethod
    def calculate_group_compactness(addresses: list[Address]) -> float:
        """計算分組的緊密度（平均距離）"""
        valid_addrs = [addr for addr in addresses if addr.has_valid_coordinates]

        if len(valid_addrs) < 2:
            return 0.0

        center = GeoUtils.calculate_centroid(valid_addrs)
        distances = []

        for addr in valid_addrs:
            dist = GeoUtils.calculate_distance(center, addr.coordinates)
            distances.append(dist)

        return sum(distances) / len(distances)

    @staticmethod
    def is_within_threshold(
        addresses: list[Address],
        max_distance: float = 500.0,
    ) -> bool:
        """檢查分組是否在距離閾值內"""
        if len(addresses) < 2:
            return True

        center = GeoUtils.calculate_centroid(addresses)

        for addr in addresses:
            if not addr.has_valid_coordinates:
                continue

            distance = GeoUtils.calculate_distance(center, addr.coordinates)
            if distance > max_distance:
                return False

        return True


class PostGISQueries:
    """利用 PostGIS 進行高效地理查詢"""

    @staticmethod
    def nearest_neighbors_query(
        lon: float,
        lat: float,
        limit: int = 50,
        max_distance: float = 1000.0,
    ) -> str:
        """生成最近鄰查詢 SQL"""
        return f"""
        SELECT *, 
               ST_Distance(geom, ST_SetSRID(ST_Point({lon}, {lat}), 4326)) as distance_meters
        FROM addresses 
        WHERE ST_DWithin(
            geom, 
            ST_SetSRID(ST_Point({lon}, {lat}), 4326), 
            {max_distance/111320}  -- 轉換為度數近似值
        )
        ORDER BY geom <-> ST_SetSRID(ST_Point({lon}, {lat}), 4326)
        LIMIT {limit};
        """

    @staticmethod
    def spatial_clustering_query(
        district: str,
        village: str,
        cluster_distance: float = 200.0,
    ) -> str:
        """生成空間聚類查詢 SQL"""
        return f"""
        WITH clustered AS (
            SELECT *,
                   ST_ClusterDBSCAN(geom, {cluster_distance/111320}, 5) 
                   OVER () AS cluster_id
            FROM addresses 
            WHERE district = '{district}' AND village = '{village}'
            AND geom IS NOT NULL
        )
        SELECT cluster_id, 
               COUNT(*) as address_count,
               ST_AsText(ST_Centroid(ST_Collect(geom))) as cluster_center,
               array_agg(id) as address_ids
        FROM clustered 
        WHERE cluster_id IS NOT NULL
        GROUP BY cluster_id
        ORDER BY cluster_id;
        """
