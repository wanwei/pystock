import os
from abc import ABC, abstractmethod
from threading import Lock


class BaseStore(ABC):
    """
    数据存储基类
    
    提供基本的文件存储功能，子类需要实现具体的存储逻辑
    """
    
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self._lock = Lock()
        self._ensure_directory()
    
    def _ensure_directory(self):
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
    
    @abstractmethod
    def save(self, key, data, **kwargs):
        """
        保存数据
        
        Args:
            key: 数据键
            data: 要保存的数据
            **kwargs: 额外参数
        
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    def load(self, key, **kwargs):
        """
        加载数据
        
        Args:
            key: 数据键
            **kwargs: 额外参数
        
        Returns:
            加载的数据
        """
        pass
    
    @abstractmethod
    def exists(self, key, **kwargs):
        """
        检查数据是否存在
        
        Args:
            key: 数据键
            **kwargs: 额外参数
        
        Returns:
            bool: 是否存在
        """
        pass
    
    @abstractmethod
    def delete(self, key, **kwargs):
        """
        删除数据
        
        Args:
            key: 数据键
            **kwargs: 额外参数
        
        Returns:
            bool: 是否成功
        """
        pass
    
    def get_filepath(self, key, **kwargs):
        """
        获取数据文件路径
        
        Args:
            key: 数据键
            **kwargs: 额外参数
        
        Returns:
            str: 文件路径
        """
        return os.path.join(self.base_dir, str(key))
