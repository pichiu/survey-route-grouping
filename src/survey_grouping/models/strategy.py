from enum import Enum


class GroupingStrategy(str, Enum):
    """分組策略選項"""
    AUTO = "auto"                 # 智能分類邏輯（預設）
    GEOGRAPHIC = "geographic"     # 純地理聚類
    STREET_FIRST = "street-first" # 優先按街道分組
    NEIGHBOR_FIRST = "neighbor-first"  # 優先按鄰別分組
    DISTANCE_BASED = "distance-based"  # 基於距離閾值的聚類
    SIMPLE = "simple"            # 簡單平均分配


class ClusteringAlgorithm(str, Enum):
    """聚類演算法選項"""
    KMEANS = "kmeans"           # K-means 聚類（預設）
    DBSCAN = "dbscan"          # DBSCAN 密度聚類
    SIMPLE_SPLIT = "simple"    # 簡單分割


# 策略說明
STRATEGY_DESCRIPTIONS = {
    GroupingStrategy.AUTO: "智能分類邏輯，根據地址類型自動選擇最佳策略",
    GroupingStrategy.GEOGRAPHIC: "純地理聚類，忽略地址類型，完全基於座標位置分組",
    GroupingStrategy.STREET_FIRST: "優先按街道名稱分組，相同街道盡量分在同組",
    GroupingStrategy.NEIGHBOR_FIRST: "優先按鄰別分組，相同鄰別盡量分在同組",
    GroupingStrategy.DISTANCE_BASED: "基於距離閾值聚類，相近地址自動分組",
    GroupingStrategy.SIMPLE: "簡單平均分配，不考慮地理因素，按順序平均分組",
}

ALGORITHM_DESCRIPTIONS = {
    ClusteringAlgorithm.KMEANS: "K-means 聚類，適合密度均勻的地址分布",
    ClusteringAlgorithm.DBSCAN: "密度聚類，適合密度不均勻或有噪音的地址分布",
    ClusteringAlgorithm.SIMPLE_SPLIT: "簡單分割，直接按順序平均分組",
}