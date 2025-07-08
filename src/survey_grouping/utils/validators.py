"""資料驗證模組

提供地址、座標、分組等資料的驗證功能。
"""

import re
from typing import List, Optional, Tuple, Union
from survey_grouping.models.address import Address, AddressType


class AddressValidator:
    """地址驗證器"""

    # 台灣地址格式的正則表達式
    TAIWAN_ADDRESS_PATTERNS = {
        "district": r"[\u4e00-\u9fff]{1,4}[區市鎮鄉]",
        "village": r"[\u4e00-\u9fff]{1,10}[里村]",
        "neighborhood": r"\d{1,3}鄰",
        "street": r"[\u4e00-\u9fff]{1,20}[路街道巷弄]",
        "number": r"\d{1,4}號?",
        "lane": r"\d{1,3}巷",
        "alley": r"\d{1,3}弄",
    }

    @classmethod
    def validate_address(cls, address: Address) -> Tuple[bool, List[str]]:
        """驗證地址完整性

        Args:
            address: 地址物件

        Returns:
            (是否有效, 錯誤訊息列表)
        """
        errors = []

        # 檢查必要欄位
        if not address.district:
            errors.append("缺少區域資訊")
        elif not cls._validate_district(address.district):
            errors.append(f"區域格式不正確: {address.district}")

        if not address.village:
            errors.append("缺少村里資訊")
        elif not cls._validate_village(address.village):
            errors.append(f"村里格式不正確: {address.village}")

        if address.neighborhood is None or address.neighborhood < 1:
            errors.append("鄰別資訊無效")

        # 檢查座標
        coord_valid, coord_errors = cls.validate_coordinates(
            address.x_coord, address.y_coord
        )
        if not coord_valid:
            errors.extend(coord_errors)

        # 檢查完整地址
        if not address.full_address or len(address.full_address.strip()) < 5:
            errors.append("完整地址過短或為空")

        return len(errors) == 0, errors

    @classmethod
    def validate_coordinates(
        cls, x_coord: Optional[float], y_coord: Optional[float]
    ) -> Tuple[bool, List[str]]:
        """驗證座標有效性

        Args:
            x_coord: 經度
            y_coord: 緯度

        Returns:
            (是否有效, 錯誤訊息列表)
        """
        errors = []

        if x_coord is None or y_coord is None:
            errors.append("座標資訊缺失")
            return False, errors

        # 台灣地區座標範圍檢查 (WGS84)
        if not (119.0 <= x_coord <= 122.5):
            errors.append(f"經度超出台灣範圍: {x_coord}")

        if not (21.5 <= y_coord <= 25.5):
            errors.append(f"緯度超出台灣範圍: {y_coord}")

        # 精度檢查（至少 4 位小數）
        if abs(x_coord - round(x_coord, 4)) > 1e-5:
            errors.append("經度精度不足，建議至少 4 位小數")

        if abs(y_coord - round(y_coord, 4)) > 1e-5:
            errors.append("緯度精度不足，建議至少 4 位小數")

        return len(errors) == 0, errors

    @classmethod
    def _validate_district(cls, district: str) -> bool:
        """驗證區域名稱"""
        if not district:
            return False
        return bool(re.match(cls.TAIWAN_ADDRESS_PATTERNS["district"], district))

    @classmethod
    def _validate_village(cls, village: str) -> bool:
        """驗證村里名稱"""
        if not village:
            return False
        return bool(re.match(cls.TAIWAN_ADDRESS_PATTERNS["village"], village))

    @classmethod
    def validate_address_list(cls, addresses: List[Address]) -> dict:
        """批次驗證地址列表

        Args:
            addresses: 地址列表

        Returns:
            驗證結果統計
        """
        if not addresses:
            return {
                "total": 0,
                "valid": 0,
                "invalid": 0,
                "errors": ["地址列表為空"],
            }

        valid_count = 0
        invalid_count = 0
        all_errors = []

        for i, address in enumerate(addresses):
            is_valid, errors = cls.validate_address(address)
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                all_errors.append(f"地址 {i+1} (ID: {address.id}): {'; '.join(errors)}")

        return {
            "total": len(addresses),
            "valid": valid_count,
            "invalid": invalid_count,
            "validity_rate": valid_count / len(addresses) * 100,
            "errors": all_errors[:10],  # 只顯示前 10 個錯誤
        }


class GroupingValidator:
    """分組驗證器"""

    @classmethod
    def validate_group_size(
        cls, addresses: List[Address], target_size: int, tolerance: float = 0.3
    ) -> Tuple[bool, str]:
        """驗證分組大小是否合理

        Args:
            addresses: 地址列表
            target_size: 目標大小
            tolerance: 容忍度 (0.3 表示 30%)

        Returns:
            (是否有效, 訊息)
        """
        if not addresses:
            return False, "分組為空"

        actual_size = len(addresses)
        min_size = int(target_size * (1 - tolerance))
        max_size = int(target_size * (1 + tolerance))

        if actual_size < min_size:
            return False, f"分組過小: {actual_size} < {min_size}"
        elif actual_size > max_size:
            return False, f"分組過大: {actual_size} > {max_size}"
        else:
            return True, f"分組大小合理: {actual_size}"

    @classmethod
    def validate_geographic_compactness(
        cls, addresses: List[Address], max_diameter: float = 2000.0
    ) -> Tuple[bool, str]:
        """驗證分組的地理緊密度

        Args:
            addresses: 地址列表
            max_diameter: 最大直徑（公尺）

        Returns:
            (是否有效, 訊息)
        """
        valid_addresses = [addr for addr in addresses if addr.has_valid_coordinates]

        if len(valid_addresses) < 2:
            return True, "地址數量不足，無法計算緊密度"

        # 計算最大距離
        max_distance = 0.0
        for i in range(len(valid_addresses)):
            for j in range(i + 1, len(valid_addresses)):
                distance = valid_addresses[i].distance_to(valid_addresses[j]) or 0.0
                max_distance = max(max_distance, distance)

        if max_distance > max_diameter:
            return (
                False,
                f"分組過於分散: 最大距離 {max_distance:.0f}m > {max_diameter}m",
            )
        else:
            return True, f"分組緊密度良好: 最大距離 {max_distance:.0f}m"

    @classmethod
    def validate_neighborhood_distribution(cls, addresses: List[Address]) -> dict:
        """驗證鄰別分布

        Args:
            addresses: 地址列表

        Returns:
            鄰別分布統計
        """
        neighborhood_count = {}
        for addr in addresses:
            neighborhood = addr.neighborhood
            neighborhood_count[neighborhood] = (
                neighborhood_count.get(neighborhood, 0) + 1
            )

        total_neighborhoods = len(neighborhood_count)
        max_in_neighborhood = (
            max(neighborhood_count.values()) if neighborhood_count else 0
        )
        avg_per_neighborhood = (
            len(addresses) / total_neighborhoods if total_neighborhoods > 0 else 0
        )

        return {
            "total_neighborhoods": total_neighborhoods,
            "max_addresses_in_single_neighborhood": max_in_neighborhood,
            "avg_addresses_per_neighborhood": round(avg_per_neighborhood, 2),
            "distribution": neighborhood_count,
            "is_balanced": max_in_neighborhood <= avg_per_neighborhood * 2,
        }


class DataQualityValidator:
    """資料品質驗證器"""

    @classmethod
    def check_data_completeness(cls, addresses: List[Address]) -> dict:
        """檢查資料完整性

        Args:
            addresses: 地址列表

        Returns:
            完整性報告
        """
        if not addresses:
            return {"total": 0, "completeness": {}}

        total = len(addresses)
        completeness = {
            "has_coordinates": sum(
                1 for addr in addresses if addr.has_valid_coordinates
            ),
            "has_full_address": sum(1 for addr in addresses if addr.full_address),
            "has_street": sum(1 for addr in addresses if addr.street),
            "has_area": sum(1 for addr in addresses if addr.area),
            "has_lane": sum(1 for addr in addresses if addr.lane),
            "has_alley": sum(1 for addr in addresses if addr.alley),
            "has_number": sum(1 for addr in addresses if addr.number),
        }

        # 計算百分比
        percentages = {
            key: round(count / total * 100, 2) for key, count in completeness.items()
        }

        return {
            "total": total,
            "completeness_counts": completeness,
            "completeness_percentages": percentages,
            "overall_quality_score": round(
                sum(percentages.values()) / len(percentages), 2
            ),
        }

    @classmethod
    def detect_duplicates(cls, addresses: List[Address]) -> dict:
        """檢測重複地址

        Args:
            addresses: 地址列表

        Returns:
            重複檢測結果
        """
        # 按完整地址檢測重複
        address_groups = {}
        for addr in addresses:
            key = addr.full_address.strip().lower()
            if key not in address_groups:
                address_groups[key] = []
            address_groups[key].append(addr.id)

        duplicates = {key: ids for key, ids in address_groups.items() if len(ids) > 1}

        # 按座標檢測重複（容忍 10 公尺誤差）
        coordinate_duplicates = []
        processed = set()

        for i, addr1 in enumerate(addresses):
            if i in processed or not addr1.has_valid_coordinates:
                continue

            similar_addresses = [addr1.id]
            for j, addr2 in enumerate(addresses[i + 1 :], i + 1):
                if not addr2.has_valid_coordinates:
                    continue

                distance = addr1.distance_to(addr2) or float("inf")
                if distance < 10:  # 10 公尺內視為重複
                    similar_addresses.append(addr2.id)
                    processed.add(j)

            if len(similar_addresses) > 1:
                coordinate_duplicates.append(similar_addresses)

        return {
            "address_duplicates": duplicates,
            "coordinate_duplicates": coordinate_duplicates,
            "total_duplicate_groups": len(duplicates) + len(coordinate_duplicates),
        }

    @classmethod
    def validate_address_format(cls, address_string: str) -> Tuple[bool, List[str]]:
        """驗證地址字串格式

        Args:
            address_string: 地址字串

        Returns:
            (是否有效, 建議)
        """
        if not address_string or len(address_string.strip()) < 5:
            return False, ["地址過短"]

        suggestions = []
        address = address_string.strip()

        # 檢查是否包含基本元素
        if not re.search(r"[\u4e00-\u9fff]+[區市鎮鄉]", address):
            suggestions.append("缺少區域資訊（如：○○區）")

        if not re.search(r"[\u4e00-\u9fff]+[里村]", address):
            suggestions.append("缺少村里資訊（如：○○里）")

        if not re.search(r"\d+號?", address):
            suggestions.append("缺少門牌號碼")

        # 檢查常見錯誤
        if "巷弄" in address:
            suggestions.append("'巷弄' 應分開寫成 '巷' 和 '弄'")

        if re.search(r"\d+\s+\d+", address):
            suggestions.append("數字間不應有空格")

        return len(suggestions) == 0, suggestions


def validate_input_parameters(
    district: str, village: str, target_size: int
) -> Tuple[bool, List[str]]:
    """驗證輸入參數

    Args:
        district: 區域名稱
        village: 村里名稱
        target_size: 目標分組大小

    Returns:
        (是否有效, 錯誤訊息列表)
    """
    errors = []

    # 驗證區域
    if not district or not district.strip():
        errors.append("區域名稱不能為空")
    elif not AddressValidator._validate_district(district):
        errors.append(f"區域名稱格式不正確: {district}")

    # 驗證村里
    if not village or not village.strip():
        errors.append("村里名稱不能為空")
    elif not AddressValidator._validate_village(village):
        errors.append(f"村里名稱格式不正確: {village}")

    # 驗證目標大小
    if not isinstance(target_size, int) or target_size < 1:
        errors.append("目標分組大小必須是正整數")
    elif target_size > 100:
        errors.append("目標分組大小過大（建議不超過 100）")
    elif target_size < 5:
        errors.append("目標分組大小過小（建議至少 5 個）")

    return len(errors) == 0, errors
