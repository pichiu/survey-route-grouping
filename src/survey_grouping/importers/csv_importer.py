import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from pydantic import BaseModel, Field

from ..models.address import Address
from ..models.group import RouteGroup, GroupingResult


class CSVGroupRow(BaseModel):
    """CSV 分組資料列模型"""
    分組編號: str
    分組大小: Optional[int] = None
    目標大小: Optional[int] = None
    預估距離_公尺: Optional[float] = Field(None, alias="預估距離(公尺)")
    預估時間_分鐘: Optional[int] = Field(None, alias="預估時間(分鐘)")
    地址ID: Optional[int] = None
    完整地址: str
    區域: str
    村里: str
    鄰別: int
    經度: float
    緯度: float
    訪問順序: Optional[int] = None

    class Config:
        validate_by_name = True


class CSVImporter:
    """CSV 分組結果導入器"""
    
    def __init__(self):
        self.groups_data: Dict[str, List[CSVGroupRow]] = {}
        self.metadata: Dict[str, any] = {}
    
    def read_csv_file(self, file_path: str | Path) -> List[CSVGroupRow]:
        """讀取 CSV 檔案並解析為 CSVGroupRow 列表"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"CSV 檔案不存在: {file_path}")
        
        rows = []
        
        # 嘗試使用不同編碼讀取檔案
        encodings = ['utf-8-sig', 'utf-8']
        last_error = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    
                    for row_num, row in enumerate(reader, start=2):  # 從第2行開始計算（第1行是標題）
                        try:
                            # 處理可能的空值
                            processed_row = {}
                            for key, value in row.items():
                                if value == '' or value is None:
                                    processed_row[key] = None
                                elif key in ['分組大小', '目標大小', '預估時間(分鐘)', '地址ID', '鄰別', '訪問順序']:
                                    try:
                                        processed_row[key] = int(value) if value else None
                                    except ValueError:
                                        processed_row[key] = None
                                elif key in ['預估距離(公尺)', '經度', '緯度']:
                                    try:
                                        processed_row[key] = float(value) if value else None
                                    except ValueError:
                                        if key in ['經度', '緯度']:
                                            raise ValueError(f"第 {row_num} 行的 {key} 必須是有效數值: {value}")
                                        processed_row[key] = None
                                else:
                                    processed_row[key] = value
                            
                            csv_row = CSVGroupRow(**processed_row)
                            rows.append(csv_row)
                            
                        except Exception as e:
                            raise ValueError(f"解析 CSV 第 {row_num} 行時發生錯誤: {e}")
                    
                    # 成功讀取，跳出迴圈
                    break
                    
            except (UnicodeDecodeError, UnicodeError) as e:
                last_error = e
                continue
        else:
            # 所有編碼都失敗
            raise ValueError(f"無法使用支援的編碼 ({', '.join(encodings)}) 讀取檔案，最後錯誤: {last_error}")
        
        return rows
    
    def group_rows_by_group_id(self, rows: List[CSVGroupRow]) -> Dict[str, List[CSVGroupRow]]:
        """將 CSV 資料按分組編號分組"""
        groups = {}
        
        for row in rows:
            group_id = row.分組編號
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(row)
        
        return groups
    
    def convert_to_route_groups(self, grouped_rows: Dict[str, List[CSVGroupRow]]) -> List[RouteGroup]:
        """將分組的 CSV 資料轉換為 RouteGroup 物件"""
        route_groups = []
        
        for group_id, rows in grouped_rows.items():
            if not rows:
                continue
            
            # 轉換地址
            addresses = []
            route_order = []
            
            for row in rows:
                # 生成地址 ID（如果沒有提供的話）
                addr_id = row.地址ID if row.地址ID is not None else hash(row.完整地址) % 1000000
                
                address = Address(
                    id=addr_id,
                    district=row.區域,
                    village=row.村里,
                    neighborhood=row.鄰別,
                    full_address=row.完整地址,
                    x_coord=row.經度,
                    y_coord=row.緯度
                )
                addresses.append(address)
                
                # 建立路線順序（如果有提供的話）
                if row.訪問順序 is not None:
                    route_order.append((row.訪問順序, addr_id))
            
            # 按訪問順序排序
            if route_order:
                route_order.sort(key=lambda x: x[0])  # 按順序編號排序
                sorted_route_order = [addr_id for _, addr_id in route_order]
            else:
                sorted_route_order = []
            
            # 取得分組統計資訊（從第一筆資料）
            first_row = rows[0]
            
            route_group = RouteGroup(
                group_id=group_id,
                addresses=addresses,
                estimated_distance=first_row.預估距離_公尺,
                estimated_time=first_row.預估時間_分鐘,
                route_order=sorted_route_order,
                target_size=first_row.目標大小,
                actual_size=first_row.分組大小 or len(addresses),
                created_at=datetime.now()
            )
            
            route_groups.append(route_group)
        
        return route_groups
    
    def import_from_csv(self, file_path: str | Path) -> GroupingResult:
        """從 CSV 檔案導入完整的分組結果"""
        # 1. 讀取 CSV 檔案
        rows = self.read_csv_file(file_path)
        
        if not rows:
            raise ValueError("CSV 檔案為空或無有效資料")
        
        # 2. 按分組編號分組
        grouped_rows = self.group_rows_by_group_id(rows)
        
        # 3. 轉換為 RouteGroup 物件
        route_groups = self.convert_to_route_groups(grouped_rows)
        
        # 4. 從第一筆資料取得基本資訊
        first_row = rows[0]
        district = first_row.區域
        village = first_row.村里
        target_size = first_row.目標大小 or 35  # 預設值
        
        # 5. 建立 GroupingResult
        grouping_result = GroupingResult(
            district=district,
            village=village,
            target_size=target_size,
            total_addresses=len(rows),
            total_groups=len(route_groups),
            groups=route_groups,
            created_at=datetime.now()
        )
        
        # 6. 計算統計資訊
        grouping_result.calculate_statistics()
        
        return grouping_result
    
    def validate_csv_format(self, file_path: str | Path) -> Tuple[bool, List[str]]:
        """驗證 CSV 檔案格式"""
        file_path = Path(file_path)
        errors = []
        
        if not file_path.exists():
            return False, [f"檔案不存在: {file_path}"]
        
        # 嘗試使用不同編碼讀取檔案
        encodings = ['utf-8-sig', 'utf-8']
        last_error = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    headers = reader.fieldnames
                    
                    # 檢查必要欄位
                    required_fields = ['分組編號', '完整地址', '區域', '村里', '鄰別', '經度', '緯度']
                    missing_fields = [field for field in required_fields if field not in headers]
                    
                    if missing_fields:
                        errors.append(f"缺少必要欄位: {', '.join(missing_fields)}")
                    
                    # 檢查前幾筆資料的格式
                    sample_count = 0
                    for row_num, row in enumerate(reader, start=2):
                        if sample_count >= 5:  # 只檢查前5筆
                            break
                        
                        # 檢查經緯度是否為有效數值
                        try:
                            float(row['經度'])
                            float(row['緯度'])
                        except (ValueError, KeyError):
                            errors.append(f"第 {row_num} 行的經緯度格式錯誤")
                        
                        # 檢查鄰別是否為整數
                        try:
                            int(row['鄰別'])
                        except (ValueError, KeyError):
                            errors.append(f"第 {row_num} 行的鄰別必須是整數")
                        
                        sample_count += 1
                
                # 成功讀取，跳出迴圈
                break
                
            except (UnicodeDecodeError, UnicodeError) as e:
                last_error = e
                continue
        else:
            # 所有編碼都失敗
            errors.append(f"無法使用支援的編碼 ({', '.join(encodings)}) 讀取檔案，最後錯誤: {last_error}")
        
        return len(errors) == 0, errors