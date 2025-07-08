from pydantic import BaseModel
from typing import Optional, Tuple
from enum import Enum


class AddressType(str, Enum):
    STREET = "street"
    AREA = "area"
    NEIGHBOR = "neighbor"


class Address(BaseModel):
    id: int
    district: str
    village: str
    neighborhood: int
    street: Optional[str] = None
    area: Optional[str] = None
    lane: Optional[str] = None
    alley: Optional[str] = None
    number: Optional[str] = None
    x_coord: Optional[float] = None
    y_coord: Optional[float] = None
    full_address: str

    # 分類結果
    address_type: Optional[AddressType] = None
    address_key: Optional[str] = None

    @property
    def coordinates(self) -> Optional[Tuple[float, float]]:
        if self.x_coord and self.y_coord:
            return (self.x_coord, self.y_coord)
        return None

    @property
    def has_valid_coordinates(self) -> bool:
        return self.coordinates is not None


class RouteGroup(BaseModel):
    group_id: str
    addresses: list[Address]
    estimated_distance: Optional[float] = None
    estimated_time: Optional[int] = None  # 分鐘
    route_order: list[int] = []  # address id 順序

    @property
    def size(self) -> int:
        return len(self.addresses)

    @property
    def center_coordinates(self) -> Optional[Tuple[float, float]]:
        valid_coords = [
            addr.coordinates for addr in self.addresses if addr.has_valid_coordinates
        ]
        if not valid_coords:
            return None

        avg_x = sum(coord[0] for coord in valid_coords) / len(valid_coords)
        avg_y = sum(coord[1] for coord in valid_coords) / len(valid_coords)
        return (avg_x, avg_y)
