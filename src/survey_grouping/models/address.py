from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AddressType(str, Enum):
    STREET = "street"
    AREA = "area"
    NEIGHBOR = "neighbor"


class Address(BaseModel):
    id: int
    district: str
    village: str
    neighborhood: int
    street: str | None = None
    area: str | None = None
    lane: str | None = None
    alley: str | None = None
    number: str | None = None
    x_coord: float | None = None
    y_coord: float | None = None
    full_address: str

    # PostGIS 支援
    geom: dict | str | None = Field(None, description="PostGIS GEOMETRY 欄位")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # 分類結果
    address_type: AddressType | None = None
    address_key: str | None = None

    @property
    def coordinates(self) -> tuple[float, float] | None:
        """取得座標元組 (經度, 緯度)"""
        if self.x_coord and self.y_coord:
            return (self.x_coord, self.y_coord)
        return None

    @property
    def has_valid_coordinates(self) -> bool:
        """檢查是否有有效的座標"""
        return self.coordinates is not None

    @property
    def wgs84_point(self) -> str | None:
        """取得 WGS84 格式的點座標 WKT"""
        if self.has_valid_coordinates:
            return f"POINT({self.x_coord} {self.y_coord})"
        return None

    def distance_to(self, other: "Address") -> float | None:
        """計算到另一個地址的直線距離（公尺）- 簡化版本"""
        if not (self.has_valid_coordinates and other.has_valid_coordinates):
            return None

        # 簡化的距離計算，實際應使用 PostGIS 的 ST_Distance
        import math

        lat1, lon1 = math.radians(self.y_coord), math.radians(self.x_coord)
        lat2, lon2 = math.radians(other.y_coord), math.radians(other.x_coord)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # 地球半徑（公尺）
        r = 6371000

        return c * r


class RouteGroup(BaseModel):
    group_id: str
    addresses: list[Address]
    estimated_distance: float | None = None
    estimated_time: int | None = None  # 分鐘
    route_order: list[int] = []  # address id 順序

    @property
    def size(self) -> int:
        return len(self.addresses)

    @property
    def center_coordinates(self) -> tuple[float, float] | None:
        valid_coords = [
            addr.coordinates for addr in self.addresses if addr.has_valid_coordinates
        ]
        if not valid_coords:
            return None

        avg_x = sum(coord[0] for coord in valid_coords) / len(valid_coords)
        avg_y = sum(coord[1] for coord in valid_coords) / len(valid_coords)
        return (avg_x, avg_y)
