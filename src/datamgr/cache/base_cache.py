from abc import ABC, abstractmethod
from threading import Lock
from collections import OrderedDict


class BaseCache(ABC):
    """
    数据缓存基类
    
    提供基本的内存缓存功能，支持LRU淘汰策略
    """
    
    def __init__(self, max_size=100):
        self._cache = OrderedDict()
        self._max_size = max_size
        self._lock = Lock()
    
    def get(self, key):
        """
        获取缓存数据
        
        Args:
            key: 缓存键
        
        Returns:
            缓存的数据，不存在返回None
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None
    
    def set(self, key, value):
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
    
    def exists(self, key):
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否存在
        """
        with self._lock:
            return key in self._cache
    
    def delete(self, key):
        """
        删除缓存
        
        Args:
            key: 缓存键
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self):
        """
        清空缓存
        """
        with self._lock:
            self._cache.clear()
    
    def size(self):
        """
        获取缓存大小
        """
        with self._lock:
            return len(self._cache)
    
    def keys(self):
        """
        获取所有缓存键
        """
        with self._lock:
            return list(self._cache.keys())
    
    @abstractmethod
    def build_key(self, *args, **kwargs):
        """
        构建缓存键
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            str: 缓存键
        """
        pass
