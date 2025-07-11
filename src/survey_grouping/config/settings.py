from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Supabase 設定 (必要)
    supabase_url: str = "https://your-project.supabase.co"
    supabase_key: str = "your-anon-key"

    # Supabase Service Role Key (可選，用於管理操作)
    supabase_service_key: str | None = None

    # 分組參數
    default_group_size: int = 35
    min_group_size: int = 25
    max_group_size: int = 45

    # 地理參數
    max_distance_threshold: float = 500.0  # 最大組內距離(公尺)
    coordinate_system: str = "4326"  # WGS84 (已確認)
    use_spherical_distance: bool = True  # 使用球面距離計算

    # 演算法參數
    clustering_algorithm: str = "kmeans"
    route_optimization: bool = True

    # 系統設定
    debug: bool = False
    log_level: str = "INFO"

    @model_validator(mode="after")
    def validate_supabase_config(self):
        """驗證 Supabase 設定"""
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL 是必要的環境變數")

        if not self.supabase_key:
            raise ValueError("SUPABASE_KEY 是必要的環境變數")

        if not self.supabase_url.startswith("https://"):
            raise ValueError("SUPABASE_URL 必須是有效的 HTTPS URL")

        return self


# 全域設定實例
settings = Settings()
