from supabase import Client
from typing import List, Optional, Tuple
from ..models.address import Address
from ..models.address_stats import AddressStats, VillageStats, DistrictStats


class AddressQueries:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def get_addresses_by_village(
        self, district: str, village: str
    ) -> List[Address]:
        """取得指定村里的所有地址"""
        try:
            response = (
                self.supabase.table("addresses")
                .select("*")
                .eq("district", district)
                .eq("village", village)
                .order("neighborhood", desc=False)
                .order("street", desc=False)
                .execute()
            )

            addresses = [Address(**addr) for addr in response.data]
            return addresses

        except Exception as e:
            raise DatabaseError(f"查詢地址失敗: {e}")

    async def get_addresses_within_distance(
        self, 
        center_x: float, 
        center_y: float, 
        distance_meters: float,
        district: Optional[str] = None,
        village: Optional[str] = None
    ) -> List[Address]:
        """使用 PostGIS 查詢指定距離內的地址"""
        try:
            # 建立 PostGIS 空間查詢
            point_wkt = f"POINT({center_x} {center_y})"
            
            query = self.supabase.table("addresses").select("*")
            
            # 使用 PostGIS ST_DWithin 函數
            query = query.filter(
                "geom", 
                "st_dwithin", 
                f"ST_GeomFromText('{point_wkt}', 4326)::{distance_meters}"
            )
            
            if district:
                query = query.eq("district", district)
            if village:
                query = query.eq("village", village)
                
            response = query.execute()
            addresses = [Address(**addr) for addr in response.data]
            return addresses

        except Exception as e:
            raise DatabaseError(f"空間查詢失敗: {e}")

    async def get_village_center(
        self, district: str, village: str
    ) -> Optional[Tuple[float, float]]:
        """取得村里的地理中心點"""
        try:
            # 使用 PostGIS ST_Centroid 計算中心點
            response = (
                self.supabase.rpc(
                    "get_village_center",
                    {
                        "p_district": district,
                        "p_village": village
                    }
                )
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                center = response.data[0]
                return (center["x"], center["y"])
            
            return None

        except Exception:
            # 如果 RPC 函數不存在，使用簡單的平均值計算
            addresses = await self.get_addresses_by_village(district, village)
            valid_coords = [
                addr.coordinates for addr in addresses 
                if addr.has_valid_coordinates
            ]
            
            if not valid_coords:
                return None
                
            avg_x = sum(coord[0] for coord in valid_coords) / len(valid_coords)
            avg_y = sum(coord[1] for coord in valid_coords) / len(valid_coords)
            return (avg_x, avg_y)

    async def get_addresses_by_neighborhood(
        self, district: str, village: str, neighborhood: int
    ) -> List[Address]:
        """取得指定鄰的所有地址"""
        try:
            response = (
                self.supabase.table("addresses")
                .select("*")
                .eq("district", district)
                .eq("village", village)
                .eq("neighborhood", neighborhood)
                .order("street", desc=False)
                .order("number", desc=False)
                .execute()
            )

            addresses = [Address(**addr) for addr in response.data]
            return addresses

        except Exception as e:
            raise DatabaseError(f"查詢鄰別地址失敗: {e}")

    async def get_address_stats(
        self, district: str, village: Optional[str] = None
    ) -> List[AddressStats]:
        """取得地址統計資訊"""
        try:
            query = (
                self.supabase.table("address_stats")
                .select("*")
                .eq("district", district)
            )

            if village:
                query = query.eq("village", village)

            response = query.execute()
            stats = [AddressStats(**stat) for stat in response.data]
            return stats

        except Exception as e:
            raise DatabaseError(f"查詢統計資料失敗: {e}")

    async def get_village_stats(
        self, district: str, village: str
    ) -> Optional[VillageStats]:
        """取得村里統計摘要"""
        try:
            stats = await self.get_address_stats(district, village)
            # 找到村里統計資料
            village_stat = None
            for s in stats:
                is_village = s.level == "village"
                match = s.village == village
                if is_village and match:
                    village_stat = s
                    break
            
            if village_stat:
                return VillageStats.from_address_stats(village_stat)
            
            return None

        except Exception as e:
            raise DatabaseError(f"查詢村里統計失敗: {e}")

    async def get_district_stats(self, district: str) -> Optional[DistrictStats]:
        """取得區級統計摘要"""
        try:
            all_stats = await self.get_address_stats(district)
            
            district_stat = next(
                (s for s in all_stats if s.level == "district"), None
            )
            
            if not district_stat:
                return None
            
            # 收集所有村里統計
            village_stats = []
            for stat in all_stats:
                if stat.level == "village":
                    village_stats.append(
                        VillageStats.from_address_stats(stat)
                    )
            
            if village_stats:
                count = district_stat.address_count
                avg_per_village = count / len(village_stats)
            else:
                avg_per_village = 0
            
            estimated_total = sum(vs.estimated_groups for vs in village_stats)
            
            return DistrictStats(
                district=district,
                total_addresses=district_stat.address_count,
                total_villages=len(village_stats),
                total_neighborhoods=(
                    district_stat.neighborhood_count or 0
                ),
                avg_addresses_per_village=avg_per_village,
                estimated_total_groups=estimated_total,
                villages=village_stats,
                last_updated=district_stat.last_updated
            )

        except Exception as e:
            raise DatabaseError(f"查詢區級統計失敗: {e}")

    async def calculate_distances_matrix(
        self, addresses: List[Address]
    ) -> List[List[float]]:
        """計算地址間的距離矩陣（使用 PostGIS）"""
        try:
            if len(addresses) < 2:
                return []
            
            # 建立地址 ID 列表
            address_ids = [addr.id for addr in addresses]
            
            # 使用 PostGIS 計算距離矩陣
            response = (
                self.supabase.rpc(
                    "calculate_distance_matrix",
                    {"address_ids": address_ids}
                )
                .execute()
            )
            
            if response.data:
                return response.data
            
            # 如果 RPC 不存在，使用簡化計算
            matrix = []
            for i, addr1 in enumerate(addresses):
                row = []
                for j, addr2 in enumerate(addresses):
                    if i == j:
                        row.append(0.0)
                    else:
                        distance = addr1.distance_to(addr2) or 0.0
                        row.append(distance)
                matrix.append(row)
            
            return matrix

        except Exception as e:
            raise DatabaseError(f"計算距離矩陣失敗: {e}")


class DatabaseError(Exception):
    pass
