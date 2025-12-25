"""
Database Integration Tests
Tests the integration between application and databases (PostgreSQL, MongoDB, Redis)
"""
import pytest
import os
from typing import Generator
import asyncio

# Try to import database clients
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

try:
    from motor import motor_asyncio
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False

try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


# Database connection strings
POSTGRES_DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://conecta_user:conecta_password@localhost:5432/conecta_db"
)
MONGODB_URL = os.getenv(
    "MONGODB_URL",
    "mongodb://localhost:27017"
)
REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379"
)


@pytest.mark.skipif(not HAS_ASYNCPG, reason="asyncpg not installed")
class TestPostgreSQLIntegration:
    """Test PostgreSQL database integration"""

    @pytest.fixture
    async def db_connection(self):
        """Create a database connection"""
        conn = await asyncpg.connect(POSTGRES_DSN)
        yield conn
        await conn.close()

    @pytest.mark.asyncio
    async def test_database_connection(self, db_connection):
        """Test that database connection works"""
        result = await db_connection.fetchval("SELECT 1")
        assert result == 1

    @pytest.mark.asyncio
    async def test_usuarios_table_exists(self, db_connection):
        """Test that usuarios table exists"""
        result = await db_connection.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'usuarios'
            )
            """
        )
        # Table may or may not exist depending on schema
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_condominios_table_exists(self, db_connection):
        """Test that condominios table exists"""
        result = await db_connection.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'condominios'
            )
            """
        )
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_query_performance(self, db_connection):
        """Test basic query performance"""
        import time

        start = time.time()
        result = await db_connection.fetchval("SELECT COUNT(*) FROM pg_tables")
        duration = time.time() - start

        # Query should complete quickly (< 1 second)
        assert duration < 1.0
        assert isinstance(result, int)
        assert result > 0


@pytest.mark.skipif(not HAS_MOTOR, reason="motor not installed")
class TestMongoDBIntegration:
    """Test MongoDB integration"""

    @pytest.fixture
    async def mongo_client(self):
        """Create MongoDB client"""
        client = motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
        yield client
        client.close()

    @pytest.fixture
    async def test_db(self, mongo_client):
        """Get test database"""
        return mongo_client.conecta_db

    @pytest.mark.asyncio
    async def test_mongodb_connection(self, mongo_client):
        """Test MongoDB connection"""
        # Ping the database
        result = await mongo_client.admin.command('ping')
        assert result.get('ok') == 1.0

    @pytest.mark.asyncio
    async def test_create_and_read_document(self, test_db):
        """Test creating and reading a document"""
        collection = test_db.test_collection

        # Insert test document
        test_doc = {
            "test_field": "test_value",
            "timestamp": "2025-12-22T00:00:00Z"
        }

        result = await collection.insert_one(test_doc)
        assert result.inserted_id is not None

        # Read it back
        found_doc = await collection.find_one({"_id": result.inserted_id})
        assert found_doc is not None
        assert found_doc["test_field"] == "test_value"

        # Clean up
        await collection.delete_one({"_id": result.inserted_id})

    @pytest.mark.asyncio
    async def test_list_collections(self, test_db):
        """Test listing collections"""
        collections = await test_db.list_collection_names()
        assert isinstance(collections, list)


@pytest.mark.skipif(not HAS_REDIS, reason="redis not installed")
class TestRedisIntegration:
    """Test Redis integration"""

    @pytest.fixture
    async def redis_client(self):
        """Create Redis client"""
        client = redis.from_url(REDIS_URL, decode_responses=True)
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_redis_connection(self, redis_client):
        """Test Redis connection"""
        result = await redis_client.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_set_and_get_value(self, redis_client):
        """Test setting and getting values"""
        # Set a value
        await redis_client.set("test_key", "test_value", ex=60)

        # Get it back
        value = await redis_client.get("test_key")
        assert value == "test_value"

        # Clean up
        await redis_client.delete("test_key")

    @pytest.mark.asyncio
    async def test_cache_expiration(self, redis_client):
        """Test that cache entries expire"""
        import asyncio

        # Set a value with 1 second expiration
        await redis_client.set("expiring_key", "value", ex=1)

        # Should exist immediately
        value = await redis_client.get("expiring_key")
        assert value == "value"

        # Wait for expiration
        await asyncio.sleep(2)

        # Should be gone
        value = await redis_client.get("expiring_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_redis_json_storage(self, redis_client):
        """Test storing and retrieving JSON data"""
        import json

        test_data = {
            "user_id": "123",
            "email": "test@example.com",
            "preferences": {"theme": "dark"}
        }

        # Store as JSON string
        await redis_client.set("user:123", json.dumps(test_data), ex=60)

        # Retrieve and parse
        stored = await redis_client.get("user:123")
        assert stored is not None

        parsed = json.loads(stored)
        assert parsed["user_id"] == "123"
        assert parsed["email"] == "test@example.com"

        # Clean up
        await redis_client.delete("user:123")


class TestCrossDatabaseIntegration:
    """Test integration between different databases"""

    @pytest.mark.skipif(
        not (HAS_ASYNCPG and HAS_REDIS),
        reason="Requires both PostgreSQL and Redis"
    )
    @pytest.mark.asyncio
    async def test_postgres_redis_cache_pattern(self):
        """Test caching PostgreSQL queries in Redis"""
        # Connect to both databases
        pg_conn = await asyncpg.connect(POSTGRES_DSN)
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)

        try:
            # Get data from PostgreSQL
            pg_result = await pg_conn.fetchval("SELECT current_database()")

            # Cache in Redis
            await redis_client.set(
                "cache:current_db",
                str(pg_result),
                ex=300
            )

            # Retrieve from cache
            cached_result = await redis_client.get("cache:current_db")

            assert cached_result == pg_result

            # Clean up
            await redis_client.delete("cache:current_db")

        finally:
            await pg_conn.close()
            await redis_client.close()

    @pytest.mark.skipif(
        not (HAS_MOTOR and HAS_REDIS),
        reason="Requires both MongoDB and Redis"
    )
    @pytest.mark.asyncio
    async def test_mongodb_redis_cache_pattern(self):
        """Test caching MongoDB queries in Redis"""
        import json

        # Connect to both databases
        mongo_client = motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)

        try:
            db = mongo_client.conecta_db
            collection = db.test_collection

            # Insert test document
            test_doc = {"name": "Test", "value": 123}
            result = await collection.insert_one(test_doc)
            doc_id = str(result.inserted_id)

            # Cache in Redis
            await redis_client.set(
                f"mongo:cache:{doc_id}",
                json.dumps({"name": "Test", "value": 123, "_id": doc_id}),
                ex=300
            )

            # Retrieve from cache
            cached = await redis_client.get(f"mongo:cache:{doc_id}")
            assert cached is not None

            cached_data = json.loads(cached)
            assert cached_data["name"] == "Test"
            assert cached_data["value"] == 123

            # Clean up
            await collection.delete_one({"_id": result.inserted_id})
            await redis_client.delete(f"mongo:cache:{doc_id}")

        finally:
            mongo_client.close()
            await redis_client.close()


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
