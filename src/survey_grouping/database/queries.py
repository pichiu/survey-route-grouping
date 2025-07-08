from supabase import Client
from typing import List, Optional
from ..models.address import Address


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
                .execute()
            )

            addresses = [Address(**addr) for addr in response.data]
            return addresses

        except Exception as e:
            raise DatabaseError(f"查詢地址失敗: {e}")

    async def get_address_stats(
        self, district: str, village: Optional[str] = None
    ) -> dict:
        """取得地址統計資訊"""
        query = (
            self.supabase.table("address_stats").select("*").eq("district", district)
        )

        if village:
            query = query.eq("village", village)

        response = query.execute()
        return response.data


class DatabaseError(Exception):
    pass
