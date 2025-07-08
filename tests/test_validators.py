"""驗證器測試

測試地址驗證、分組驗證等功能。
"""

import pytest
from survey_grouping.utils.validators import (
    AddressValidator,
    GroupingValidator,
    DataQualityValidator,
    validate_input_parameters,
)
from survey_grouping.models.address import Address


class TestAddressValidator:
    """地址驗證器測試"""

    def test_validate_valid_address(self, sample_addresses):
        """測試有效地址驗證"""
        address = sample_addresses[0]
        is_valid, errors = AddressValidator.validate_address(address)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_address(self, invalid_addresses):
        """測試無效地址驗證"""
        address = invalid_addresses[0]
        is_valid, errors = AddressValidator.validate_address(address)

        assert is_valid is False
        assert len(errors) > 0
        assert any("區域" in error for error in errors)

    def test_validate_coordinates_valid(self):
        """測試有效座標驗證"""
        is_valid, errors = AddressValidator.validate_coordinates(120.2436, 23.0478)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_coordinates_invalid_range(self):
        """測試超出範圍的座標"""
        is_valid, errors = AddressValidator.validate_coordinates(200.0, 50.0)

        assert is_valid is False
        assert len(errors) > 0
        assert any("超出台灣範圍" in error for error in errors)

    def test_validate_coordinates_none(self):
        """測試空座標"""
        is_valid, errors = AddressValidator.validate_coordinates(None, None)

        assert is_valid is False
        assert len(errors) > 0
        assert any("座標資訊缺失" in error for error in errors)

    def test_validate_address_list(self, sample_addresses, invalid_addresses):
        """測試地址列表驗證"""
        all_addresses = sample_addresses + invalid_addresses
        result = AddressValidator.validate_address_list(all_addresses)

        assert result["total"] == len(all_addresses)
        assert result["valid"] == len(sample_addresses)
        assert result["invalid"] == len(invalid_addresses)
        assert result["validity_rate"] < 100

    def test_validate_empty_address_list(self):
        """測試空地址列表"""
        result = AddressValidator.validate_address_list([])

        assert result["total"] == 0
        assert result["valid"] == 0
        assert result["invalid"] == 0
        assert len(result["errors"]) > 0


class TestGroupingValidator:
    """分組驗證器測試"""

    def test_validate_group_size_valid(self, sample_addresses):
        """測試有效分組大小"""
        is_valid, message = GroupingValidator.validate_group_size(
            sample_addresses[:3], target_size=3, tolerance=0.3
        )

        assert is_valid is True
        assert "合理" in message

    def test_validate_group_size_too_small(self, sample_addresses):
        """測試分組過小"""
        is_valid, message = GroupingValidator.validate_group_size(
            sample_addresses[:1], target_size=5, tolerance=0.3
        )

        assert is_valid is False
        assert "過小" in message

    def test_validate_group_size_too_large(self, sample_addresses):
        """測試分組過大"""
        is_valid, message = GroupingValidator.validate_group_size(
            sample_addresses, target_size=2, tolerance=0.3
        )

        assert is_valid is False
        assert "過大" in message

    def test_validate_empty_group(self):
        """測試空分組"""
        is_valid, message = GroupingValidator.validate_group_size(
            [], target_size=3, tolerance=0.3
        )

        assert is_valid is False
        assert "為空" in message

    def test_validate_geographic_compactness(self, sample_addresses):
        """測試地理緊密度驗證"""
        is_valid, message = GroupingValidator.validate_geographic_compactness(
            sample_addresses[:3], max_diameter=2000.0
        )

        assert is_valid is True
        assert "良好" in message

    def test_validate_neighborhood_distribution(self, sample_addresses):
        """測試鄰別分布驗證"""
        result = GroupingValidator.validate_neighborhood_distribution(sample_addresses)

        assert "total_neighborhoods" in result
        assert "max_addresses_in_single_neighborhood" in result
        assert "avg_addresses_per_neighborhood" in result
        assert "distribution" in result
        assert "is_balanced" in result


class TestDataQualityValidator:
    """資料品質驗證器測試"""

    def test_check_data_completeness(self, sample_addresses):
        """測試資料完整性檢查"""
        result = DataQualityValidator.check_data_completeness(sample_addresses)

        assert result["total"] == len(sample_addresses)
        assert "completeness_counts" in result
        assert "completeness_percentages" in result
        assert "overall_quality_score" in result

    def test_check_empty_data_completeness(self):
        """測試空資料完整性"""
        result = DataQualityValidator.check_data_completeness([])

        assert result["total"] == 0
        assert "completeness" in result

    def test_detect_duplicates(self, sample_addresses):
        """測試重複檢測"""
        # 建立重複地址
        duplicate_addr = Address(
            id=999,
            district="安南區",
            village="安慶里",
            neighborhood=1,
            x_coord=120.2436,  # 與第一個地址相同座標
            y_coord=23.0478,
            full_address="台南市安南區安慶里1鄰安中路一段100號",  # 相同地址
        )

        addresses_with_duplicates = sample_addresses + [duplicate_addr]
        result = DataQualityValidator.detect_duplicates(addresses_with_duplicates)

        assert "address_duplicates" in result
        assert "coordinate_duplicates" in result
        assert "total_duplicate_groups" in result

    def test_validate_address_format_valid(self):
        """測試有效地址格式"""
        is_valid, suggestions = DataQualityValidator.validate_address_format(
            "台南市安南區安慶里1鄰安中路一段100號"
        )

        assert is_valid is True
        assert len(suggestions) == 0

    def test_validate_address_format_invalid(self):
        """測試無效地址格式"""
        is_valid, suggestions = DataQualityValidator.validate_address_format("短地址")

        assert is_valid is False
        assert len(suggestions) > 0

    def test_validate_address_format_empty(self):
        """測試空地址格式"""
        is_valid, suggestions = DataQualityValidator.validate_address_format("")

        assert is_valid is False
        assert len(suggestions) > 0
        assert any("過短" in suggestion for suggestion in suggestions)


class TestInputParametersValidator:
    """輸入參數驗證器測試"""

    def test_validate_valid_parameters(self):
        """測試有效參數"""
        is_valid, errors = validate_input_parameters("安南區", "安慶里", 35)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_empty_district(self):
        """測試空區域"""
        is_valid, errors = validate_input_parameters("", "安慶里", 35)

        assert is_valid is False
        assert any("區域名稱不能為空" in error for error in errors)

    def test_validate_empty_village(self):
        """測試空村里"""
        is_valid, errors = validate_input_parameters("安南區", "", 35)

        assert is_valid is False
        assert any("村里名稱不能為空" in error for error in errors)

    def test_validate_invalid_target_size_zero(self):
        """測試無效目標大小（零）"""
        is_valid, errors = validate_input_parameters("安南區", "安慶里", 0)

        assert is_valid is False
        assert any("正整數" in error for error in errors)

    def test_validate_invalid_target_size_negative(self):
        """測試無效目標大小（負數）"""
        is_valid, errors = validate_input_parameters("安南區", "安慶里", -5)

        assert is_valid is False
        assert any("正整數" in error for error in errors)

    def test_validate_target_size_too_large(self):
        """測試目標大小過大"""
        is_valid, errors = validate_input_parameters("安南區", "安慶里", 150)

        assert is_valid is False
        assert any("過大" in error for error in errors)

    def test_validate_target_size_too_small(self):
        """測試目標大小過小"""
        is_valid, errors = validate_input_parameters("安南區", "安慶里", 2)

        assert is_valid is False
        assert any("過小" in error for error in errors)

    def test_validate_invalid_district_format(self):
        """測試無效區域格式"""
        is_valid, errors = validate_input_parameters("無效區域", "安慶里", 35)

        assert is_valid is False
        assert any("格式不正確" in error for error in errors)

    def test_validate_invalid_village_format(self):
        """測試無效村里格式"""
        is_valid, errors = validate_input_parameters("安南區", "無效村里", 35)

        assert is_valid is False
        assert any("格式不正確" in error for error in errors)
