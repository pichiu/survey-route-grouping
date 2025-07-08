import logging

from supabase import Client, create_client

from ..config.settings import settings

logger = logging.getLogger(__name__)


class SupabaseConnection:
    """Supabase 連接管理器"""

    _client: Client | None = None
    _service_client: Client | None = None

    @classmethod
    def get_client(cls, use_service_key: bool = False) -> Client:
        """取得 Supabase 客戶端

        Args:
            use_service_key: 是否使用 Service Role Key (用於管理操作)
        """
        if use_service_key:
            if cls._service_client is None:
                cls._service_client = cls._create_service_client()
            return cls._service_client
        if cls._client is None:
            cls._client = cls._create_client()
        return cls._client

    @classmethod
    def _create_client(cls) -> Client:
        """建立一般客戶端 (使用 anon key)"""
        url = settings.supabase_url
        key = settings.supabase_key

        if not url or not key:
            raise ConnectionError(
                "缺少 Supabase 設定。請檢查 SUPABASE_URL 和 SUPABASE_KEY 環境變數",
            )

        try:
            client = create_client(url, key)
            logger.info("Supabase 客戶端連接成功")
            return client
        except Exception as e:
            raise ConnectionError(f"Supabase 連接失敗: {e}")

    @classmethod
    def _create_service_client(cls) -> Client:
        """建立服務客戶端 (使用 service role key)"""
        url = settings.supabase_url
        service_key = settings.supabase_service_key

        if not url or not service_key:
            raise ConnectionError(
                "缺少 Service Role Key。請設定 SUPABASE_SERVICE_KEY 環境變數",
            )

        try:
            client = create_client(url, service_key)
            logger.info("Supabase 服務客戶端連接成功")
            return client
        except Exception as e:
            raise ConnectionError(f"Supabase 服務連接失敗: {e}")

    @classmethod
    def test_connection(cls) -> bool:
        """測試連接是否正常"""
        try:
            client = cls.get_client()
            # 嘗試執行簡單查詢測試連接
            response = (
                client.table("addresses")
                .select("count", count="exact")
                .limit(1)
                .execute()
            )
            logger.info("Supabase 連接測試成功")
            return True
        except Exception as e:
            logger.error(f"Supabase 連接測試失敗: {e}")
            return False

    @classmethod
    def reset_connections(cls):
        """重置連接（用於測試或重新配置）"""
        cls._client = None
        cls._service_client = None
        logger.info("Supabase 連接已重置")


# 便利函數
def get_supabase_client(use_service_key: bool = False) -> Client:
    """取得 Supabase 客戶端的便利函數"""
    return SupabaseConnection.get_client(use_service_key)


def test_supabase_connection() -> bool:
    """測試 Supabase 連接的便利函數"""
    return SupabaseConnection.test_connection()


class ConnectionError(Exception):
    """連接相關錯誤"""
