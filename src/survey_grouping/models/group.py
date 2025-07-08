from datetime import datetime

from pydantic import BaseModel

from .address import Address


class RouteGroup(BaseModel):
    """路線分組模型"""

    group_id: str
    addresses: list[Address]
    estimated_distance: float | None = None  # 公尺
    estimated_time: int | None = None  # 分鐘
    route_order: list[int] = []  # address id 順序
    created_at: datetime | None = None

    # 分組統計
    target_size: int | None = None
    actual_size: int | None = None

    # 地理資訊
    center_lat: float | None = None
    center_lng: float | None = None
    bounding_box: tuple[float, float, float, float] | None = (
        None  # (min_lat, min_lng, max_lat, max_lng)
    )

    @property
    def size(self) -> int:
        """取得分組大小"""
        return len(self.addresses)

    @property
    def center_coordinates(self) -> tuple[float, float] | None:
        """計算分組的地理中心點"""
        valid_coords = [
            addr.coordinates for addr in self.addresses if addr.has_valid_coordinates
        ]
        if not valid_coords:
            return None

        avg_x = sum(coord[0] for coord in valid_coords) / len(valid_coords)
        avg_y = sum(coord[1] for coord in valid_coords) / len(valid_coords)
        return (avg_x, avg_y)

    @property
    def address_count_by_neighborhood(self) -> dict:
        """按鄰別統計地址數量"""
        neighborhood_count = {}
        for addr in self.addresses:
            neighborhood = addr.neighborhood
            neighborhood_count[neighborhood] = (
                neighborhood_count.get(neighborhood, 0) + 1
            )
        return neighborhood_count

    @property
    def coverage_area(self) -> tuple[float, float, float, float] | None:
        """計算分組覆蓋的地理範圍 (min_lat, min_lng, max_lat, max_lng)"""
        valid_coords = [
            addr.coordinates for addr in self.addresses if addr.has_valid_coordinates
        ]
        if not valid_coords:
            return None

        lngs = [coord[0] for coord in valid_coords]
        lats = [coord[1] for coord in valid_coords]

        return (min(lats), min(lngs), max(lats), max(lngs))

    def get_addresses_by_neighborhood(self, neighborhood: int) -> list[Address]:
        """取得指定鄰別的地址"""
        return [addr for addr in self.addresses if addr.neighborhood == neighborhood]

    def calculate_route_distance(self) -> float:
        """計算路線總距離（簡化版本）"""
        if len(self.addresses) < 2:
            return 0.0

        total_distance = 0.0
        if self.route_order:
            # 按照路線順序計算
            ordered_addresses = []
            addr_dict = {addr.id: addr for addr in self.addresses}

            for addr_id in self.route_order:
                if addr_id in addr_dict:
                    ordered_addresses.append(addr_dict[addr_id])

            for i in range(len(ordered_addresses) - 1):
                distance = ordered_addresses[i].distance_to(ordered_addresses[i + 1])
                if distance:
                    total_distance += distance
        else:
            # 簡單的相鄰距離計算
            for i in range(len(self.addresses) - 1):
                distance = self.addresses[i].distance_to(self.addresses[i + 1])
                if distance:
                    total_distance += distance

        return total_distance

    def optimize_route_order(self) -> list[int]:
        """簡化的路線優化（最近鄰演算法）"""
        if len(self.addresses) <= 2:
            return [addr.id for addr in self.addresses]

        # 找到最南邊的點作為起點
        start_addr = min(
            self.addresses,
            key=lambda addr: addr.y_coord if addr.y_coord else float("inf"),
        )

        unvisited = [addr for addr in self.addresses if addr.id != start_addr.id]
        route = [start_addr.id]
        current = start_addr

        while unvisited:
            # 找到最近的未訪問地址
            nearest = min(
                unvisited,
                key=lambda addr: current.distance_to(addr) or float("inf"),
            )
            route.append(nearest.id)
            unvisited.remove(nearest)
            current = nearest

        return route

    def to_summary_dict(self) -> dict:
        """轉換為摘要字典"""
        center = self.center_coordinates
        coverage = self.coverage_area

        return {
            "group_id": self.group_id,
            "size": self.size,
            "target_size": self.target_size,
            "estimated_distance": self.estimated_distance,
            "estimated_time": self.estimated_time,
            "center_coordinates": center,
            "coverage_area": coverage,
            "neighborhood_distribution": self.address_count_by_neighborhood,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class GroupingResult(BaseModel):
    """分組結果模型"""

    district: str
    village: str
    target_size: int
    total_addresses: int
    total_groups: int
    groups: list[RouteGroup]
    created_at: datetime

    # 統計資訊
    avg_group_size: float | None = None
    min_group_size: int | None = None
    max_group_size: int | None = None
    total_estimated_distance: float | None = None
    total_estimated_time: int | None = None

    @property
    def group_size_distribution(self) -> dict:
        """分組大小分布統計"""
        sizes = [group.size for group in self.groups]
        return {
            "average": sum(sizes) / len(sizes) if sizes else 0,
            "minimum": min(sizes) if sizes else 0,
            "maximum": max(sizes) if sizes else 0,
            "total": sum(sizes),
        }

    @property
    def coverage_summary(self) -> dict:
        """覆蓋範圍摘要"""
        all_coords = []
        for group in self.groups:
            for addr in group.addresses:
                if addr.has_valid_coordinates:
                    all_coords.append(addr.coordinates)

        if not all_coords:
            return {}

        lngs = [coord[0] for coord in all_coords]
        lats = [coord[1] for coord in all_coords]

        return {
            "total_addresses": len(all_coords),
            "bounding_box": {
                "min_lat": min(lats),
                "min_lng": min(lngs),
                "max_lat": max(lats),
                "max_lng": max(lngs),
            },
            "center": {"lat": sum(lats) / len(lats), "lng": sum(lngs) / len(lngs)},
        }

    def calculate_statistics(self):
        """計算統計資訊"""
        if not self.groups:
            return

        sizes = [group.size for group in self.groups]
        self.avg_group_size = sum(sizes) / len(sizes)
        self.min_group_size = min(sizes)
        self.max_group_size = max(sizes)

        # 計算總距離和時間
        total_distance = 0.0
        total_time = 0

        for group in self.groups:
            if group.estimated_distance:
                total_distance += group.estimated_distance
            if group.estimated_time:
                total_time += group.estimated_time

        self.total_estimated_distance = total_distance if total_distance > 0 else None
        self.total_estimated_time = total_time if total_time > 0 else None

    def to_export_dict(self) -> dict:
        """轉換為匯出格式"""
        return {
            "metadata": {
                "district": self.district,
                "village": self.village,
                "target_size": self.target_size,
                "total_addresses": self.total_addresses,
                "total_groups": self.total_groups,
                "created_at": self.created_at.isoformat(),
                "statistics": {
                    "avg_group_size": self.avg_group_size,
                    "min_group_size": self.min_group_size,
                    "max_group_size": self.max_group_size,
                    "total_estimated_distance": self.total_estimated_distance,
                    "total_estimated_time": self.total_estimated_time,
                },
            },
            "groups": [group.to_summary_dict() for group in self.groups],
            "coverage": self.coverage_summary,
        }
