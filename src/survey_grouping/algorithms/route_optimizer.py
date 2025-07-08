"""路線優化模組

提供多種路線優化演算法，包括最近鄰、遺傳演算法等。
"""

import math
import random
from typing import List, Tuple, Optional
from survey_grouping.models.address import Address


class RouteOptimizer:
    """路線優化器"""

    def __init__(self, algorithm: str = "nearest_neighbor"):
        """初始化路線優化器

        Args:
            algorithm: 優化演算法 ('nearest_neighbor', 'genetic', 'two_opt')
        """
        self.algorithm = algorithm

    def optimize_route(self, addresses: List[Address]) -> List[int]:
        """優化地址訪問順序

        Args:
            addresses: 地址列表

        Returns:
            優化後的地址 ID 順序
        """
        if len(addresses) <= 2:
            return [addr.id for addr in addresses]

        if self.algorithm == "nearest_neighbor":
            return self._nearest_neighbor(addresses)
        elif self.algorithm == "genetic":
            return self._genetic_algorithm(addresses)
        elif self.algorithm == "two_opt":
            return self._two_opt(addresses)
        else:
            return self._nearest_neighbor(addresses)

    def _nearest_neighbor(self, addresses: List[Address]) -> List[int]:
        """最近鄰演算法"""
        if not addresses:
            return []

        # 找到最南邊的點作為起點（通常是較好的起點）
        start_addr = min(
            addresses,
            key=lambda addr: addr.y_coord if addr.y_coord else float("inf"),
        )

        unvisited = [addr for addr in addresses if addr.id != start_addr.id]
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

    def _genetic_algorithm(
        self,
        addresses: List[Address],
        population_size: int = 50,
        generations: int = 100,
    ) -> List[int]:
        """遺傳演算法優化路線"""
        if len(addresses) <= 3:
            return self._nearest_neighbor(addresses)

        # 建立距離矩陣
        distance_matrix = self._build_distance_matrix(addresses)
        addr_ids = [addr.id for addr in addresses]

        # 初始化族群
        population = []
        for _ in range(population_size):
            route = addr_ids.copy()
            random.shuffle(route)
            population.append(route)

        # 演化過程
        for generation in range(generations):
            # 計算適應度
            fitness_scores = [
                1
                / (self._calculate_route_distance(route, distance_matrix, addr_ids) + 1)
                for route in population
            ]

            # 選擇
            new_population = []
            for _ in range(population_size):
                parent1 = self._tournament_selection(population, fitness_scores)
                parent2 = self._tournament_selection(population, fitness_scores)

                # 交叉
                child = self._order_crossover(parent1, parent2)

                # 突變
                if random.random() < 0.1:  # 10% 突變率
                    child = self._mutate(child)

                new_population.append(child)

            population = new_population

        # 返回最佳路線
        best_route = min(
            population,
            key=lambda route: self._calculate_route_distance(
                route, distance_matrix, addr_ids
            ),
        )
        return best_route

    def _two_opt(self, addresses: List[Address]) -> List[int]:
        """2-opt 優化演算法"""
        # 先用最近鄰得到初始解
        route = self._nearest_neighbor(addresses)

        if len(route) <= 3:
            return route

        # 建立距離矩陣
        distance_matrix = self._build_distance_matrix(addresses)
        addr_ids = [addr.id for addr in addresses]

        improved = True
        while improved:
            improved = False
            current_distance = self._calculate_route_distance(
                route, distance_matrix, addr_ids
            )

            for i in range(1, len(route) - 1):
                for j in range(i + 1, len(route)):
                    # 嘗試 2-opt 交換
                    new_route = route.copy()
                    new_route[i:j] = reversed(new_route[i:j])

                    new_distance = self._calculate_route_distance(
                        new_route, distance_matrix, addr_ids
                    )

                    if new_distance < current_distance:
                        route = new_route
                        improved = True
                        break

                if improved:
                    break

        return route

    def _build_distance_matrix(self, addresses: List[Address]) -> List[List[float]]:
        """建立距離矩陣"""
        n = len(addresses)
        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                distance = addresses[i].distance_to(addresses[j]) or 0.0
                matrix[i][j] = distance
                matrix[j][i] = distance

        return matrix

    def _calculate_route_distance(
        self, route: List[int], distance_matrix: List[List[float]], addr_ids: List[int]
    ) -> float:
        """計算路線總距離"""
        if len(route) <= 1:
            return 0.0

        total_distance = 0.0
        id_to_index = {addr_id: i for i, addr_id in enumerate(addr_ids)}

        for i in range(len(route) - 1):
            idx1 = id_to_index[route[i]]
            idx2 = id_to_index[route[i + 1]]
            total_distance += distance_matrix[idx1][idx2]

        return total_distance

    def _tournament_selection(
        self,
        population: List[List[int]],
        fitness_scores: List[float],
        tournament_size: int = 3,
    ) -> List[int]:
        """錦標賽選擇"""
        tournament_indices = random.sample(range(len(population)), tournament_size)
        best_index = max(tournament_indices, key=lambda i: fitness_scores[i])
        return population[best_index].copy()

    def _order_crossover(self, parent1: List[int], parent2: List[int]) -> List[int]:
        """順序交叉 (OX)"""
        size = len(parent1)
        start, end = sorted(random.sample(range(size), 2))

        child = [None] * size
        child[start:end] = parent1[start:end]

        pointer = end
        for city in parent2[end:] + parent2[:end]:
            if city not in child:
                child[pointer % size] = city
                pointer += 1

        return child

    def _mutate(self, route: List[int]) -> List[int]:
        """突變操作"""
        mutated = route.copy()
        if len(mutated) > 2:
            i, j = random.sample(range(len(mutated)), 2)
            mutated[i], mutated[j] = mutated[j], mutated[i]
        return mutated

    def calculate_route_metrics(
        self, addresses: List[Address], route_order: List[int]
    ) -> dict:
        """計算路線指標

        Args:
            addresses: 地址列表
            route_order: 路線順序

        Returns:
            包含距離、時間等指標的字典
        """
        if len(route_order) <= 1:
            return {
                "total_distance": 0.0,
                "estimated_time": 0,
                "avg_distance_between_stops": 0.0,
                "max_distance_between_stops": 0.0,
            }

        # 建立地址字典
        addr_dict = {addr.id: addr for addr in addresses}

        # 計算距離
        total_distance = 0.0
        distances = []

        for i in range(len(route_order) - 1):
            addr1 = addr_dict.get(route_order[i])
            addr2 = addr_dict.get(route_order[i + 1])

            if addr1 and addr2:
                distance = addr1.distance_to(addr2) or 0.0
                total_distance += distance
                distances.append(distance)

        # 估算時間（假設步行速度 5 km/h + 每個地址停留 3 分鐘）
        walking_time = (total_distance / 1000) / 5 * 60  # 分鐘
        stop_time = len(route_order) * 3  # 每個地址 3 分鐘
        estimated_time = int(walking_time + stop_time)

        return {
            "total_distance": round(total_distance, 2),
            "estimated_time": estimated_time,
            "avg_distance_between_stops": (
                round(sum(distances) / len(distances), 2) if distances else 0.0
            ),
            "max_distance_between_stops": (
                round(max(distances), 2) if distances else 0.0
            ),
        }

    def optimize_multiple_routes(
        self, address_groups: List[List[Address]]
    ) -> List[Tuple[List[int], dict]]:
        """優化多條路線

        Args:
            address_groups: 地址分組列表

        Returns:
            每組的優化路線和指標
        """
        results = []

        for addresses in address_groups:
            if not addresses:
                results.append(([], {}))
                continue

            # 優化路線
            route_order = self.optimize_route(addresses)

            # 計算指標
            metrics = self.calculate_route_metrics(addresses, route_order)

            results.append((route_order, metrics))

        return results

    def compare_algorithms(self, addresses: List[Address]) -> dict:
        """比較不同演算法的效果

        Args:
            addresses: 地址列表

        Returns:
            各演算法的比較結果
        """
        algorithms = ["nearest_neighbor", "two_opt", "genetic"]
        results = {}

        for algorithm in algorithms:
            optimizer = RouteOptimizer(algorithm)
            route = optimizer.optimize_route(addresses)
            metrics = self.calculate_route_metrics(addresses, route)

            results[algorithm] = {
                "route": route,
                "metrics": metrics,
            }

        return results
