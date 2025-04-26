import redis.asyncio as redis
from redis.exceptions import RedisError
from functools import wraps
import pickle
import logging
from typing import Optional, Any, Callable, Coroutine
from ..config import settings

class CacheManager:
    """Async Redis cache manager with connection pooling"""
    
    def __init__(self):
        self._pool: Optional[redis.Redis] = None
        self.logger = logging.getLogger(__name__)
        self._fallback_cache = {}

    async def init_redis(self, max_retries: int = 3, retry_delay: float = 1.0):
        """Initialize Redis with retry logic"""
        for attempt in range(max_retries):
            try:
                self._pool = redis.Redis.from_url(
                    settings.redis_url,
                    socket_connect_timeout=5,  # 5 seconds timeout
                    health_check_interval=30
                )
                await self._pool.ping()
                self.logger.info(f"Redis connection established (attempt {attempt + 1})")
                return
            except RedisError as e:
                self.logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
        
        self.logger.error("All Redis connection attempts failed")
        self._pool = None  # Ensure we don't have a half-connected pool

    async def close(self):
        """Close Redis connections"""
        if self._pool:
            await self._pool.close()
            self.logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value by key"""
        if not self._pool:
            return None
        try:
            data = await self._pool.get(key)
            return pickle.loads(data) if data else None                
        except RedisError as e:
            self.logger.warning(f"Cache get failed for key {key}: {e}")
        return self._fallback_cache.get(key)      

    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = 3600
    ) -> bool:
        """Set cached value with optional TTL (seconds)"""
        if not self._pool:
            return False            
        try:
            serialized = pickle.dumps(value)
            if ttl:
                await self._pool.setex(key, ttl, serialized)
            else:
                await self._pool.set(key, serialized)
            return True
        except (RedisError, pickle.PickleError) as e:
            self.logger.warning(f"Cache set failed for key {key}: {e}")
            pass
        self._fallback_cache[key] = value
        
    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        if not self._pool:
            return False
            
        try:
            await self._pool.delete(key)
            return True
        except RedisError as e:
            self.logger.warning(f"Cache delete failed for key {key}: {e}")
            return False

    async def ping(self) -> bool:
        """Check if Redis is available"""
        try:
            return await self._pool.ping() if self._pool else False
        except RedisError:
            return False

    def cached(
        self,
        key_prefix: str,
        ttl: int = 600
    ) -> Callable[[Callable[..., Coroutine]], Callable[..., Coroutine]]:
        """Decorator for caching async function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self._pool:
                    return await func(*args, **kwargs)
                    
                cache_key = f"{key_prefix}:{str(args)}:{str(kwargs)}"
                cached = await self.get(cache_key)
                if cached is not None:
                    return cached
                    
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator

# Singleton instance
cache = CacheManager()