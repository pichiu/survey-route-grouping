from ..models.address import Address, AddressType


class AddressClassifier:
    @staticmethod
    def classify_address(address: Address) -> tuple[AddressType, str]:
        """分類地址類型並生成地址鍵值"""

        # 優先判斷是否有街道
        if address.street and address.street.strip():
            return AddressType.STREET, address.street.strip()

        # 其次判斷是否有地區
        if address.area and address.area.strip():
            return AddressType.AREA, address.area.strip()

        # 最後使用鄰別
        return AddressType.NEIGHBOR, f"第{address.neighborhood}鄰"

    @staticmethod
    def enrich_addresses(addresses: List[Address]) -> List[Address]:
        """為地址列表添加分類資訊"""
        for address in addresses:
            address_type, address_key = AddressClassifier.classify_address(address)
            address.address_type = address_type
            address.address_key = address_key

        return addresses
