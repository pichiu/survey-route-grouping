from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AddressStats(BaseModel):
    """地址統計資料模型"""
    id: int
    level: str  # 統計層級：district, village, neighborhood
    district: Optional[str] = None
    village: Optional[str] = None
    neighborhood: Optional[int] = None
    address_count: int = 0
    village_count: Optional[int] = None
    neighborhood_count: Optional[int] = None
    last_updated: datetime

    @property
    def location_key(self) -> str:
        """產生位置識別鍵"""
        if self.level == "district":
            return f"{self.district}"
        elif self.level == "village":
            return f"{self.district}-{self.village}"
        elif self.level == "neighborhood":
            return f"{self.district}-{self.village}-{self.neighborhood}"
        return ""

    @property
    def display_name(self) -> str:
        """產生顯示名稱"""
        if self.level == "district":
            return f"{self.district}"
        elif self.level == "village":
            return f"{self.district}{self.village}"
        elif self.level == "neighborhood":
            return f"{self.district}{self.village}{self.neighborhood}鄰"
        return ""

    def is_stale(self, max_age_hours: int = 24) -> bool:
        """檢查統計資料是否過期"""
        from datetime import datetime, timedelta
        
        if not self.last_updated:
            return True
        
        age = datetime.now() - self.last_updated
        return age > timedelta(hours=max_age_hours)


class VillageStats(BaseModel):
    """村里統計摘要"""
    district: str
    village: str
    total_addresses: int
    total_neighborhoods: int
    avg_addresses_per_neighborhood: float
    estimated_groups: int
    coverage_area_km2: Optional[float] = None
    last_updated: datetime

    @classmethod
    def from_address_stats(
        cls, 
        stats: AddressStats, 
        target_group_size: int = 35
    ) -> 'VillageStats':
        """從 AddressStats 建立 VillageStats"""
        estimated_groups = max(1, stats.address_count // target_group_size)
        avg_per_neighborhood = (
            stats.address_count / stats.neighborhood_count 
            if stats.neighborhood_count and stats.neighborhood_count > 0 
            else 0
        )
        
        return cls(
            district=stats.district,
            village=stats.village,
            total_addresses=stats.address_count,
            total_neighborhoods=stats.neighborhood_count or 0,
            avg_addresses_per_neighborhood=avg_per_neighborhood,
            estimated_groups=estimated_groups,
            last_updated=stats.last_updated
        )


class DistrictStats(BaseModel):
    """區級統計摘要"""
    district: str
    total_addresses: int
    total_villages: int
    total_neighborhoods: int
    avg_addresses_per_village: float
    estimated_total_groups: int
    villages: list[VillageStats] = []
    last_updated: datetime

    @property
    def largest_village(self) -> Optional[VillageStats]:
        """取得最大的村里"""
        if not self.villages:
            return None
        return max(self.villages, key=lambda v: v.total_addresses)

    @property
    def smallest_village(self) -> Optional[VillageStats]:
        """取得最小的村里"""
        if not self.villages:
            return None
        return min(self.villages, key=lambda v: v.total_addresses)

    def get_village_stats(self, village_name: str) -> Optional[VillageStats]:
        """取得特定村里的統計"""
        for village in self.villages:
            if village.village == village_name:
                return village
        return None
