"""
Centralized logging system for Nexus AI
Provides structured logging with file rotation and multiple output targets
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from datetime import datetime

class NexusLogger:
    """Centralized logger for Nexus AI with file and console output"""
    
    _instance: Optional['NexusLogger'] = None
    _initialized: bool=False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance=super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized=True
        self.log_dir=Path.home() / '.nexus' / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.detailed_formatter=logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.simple_formatter=logging.Formatter(
            '%(levelname)-8s | %(message)s'
        )
        
        self.root_logger=logging.getLogger('nexus')
        self.root_logger.setLevel(logging.DEBUG)
        self.root_logger.handlers.clear()
        
        log_file=self.log_dir / f'nexus_{datetime.now().strftime("%Y%m%d")}.log'
        file_handler=RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(self.detailed_formatter)
        self.root_logger.addHandler(file_handler)
        
        console_handler=logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self.simple_formatter)
        self.root_logger.addHandler(console_handler)
        
        self.root_logger.info("=" * 60)
        self.root_logger.info("Nexus AI Logging System Initialized")
        self.root_logger.info(f"Log directory: {self.log_dir}")
        self.root_logger.info("=" * 60)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger for a specific module"""
        return logging.getLogger(f'nexus.{name}')
    
    def set_console_level(self, level: str):
        """Set console output level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""
        level_map={
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        log_level=level_map.get(level.upper(), logging.INFO)
        for handler in self.root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                handler.setLevel(log_level)
                self.root_logger.info(f"Console log level set to: {level.upper()}")
    
    def disable_console(self):
        """Disable console output (useful for text mode)"""
        for handler in self.root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                self.root_logger.removeHandler(handler)

_logger_instance=NexusLogger()

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module
    
    Usage:
        from core.logger import get_logger
        logger=get_logger(__name__)
        logger.info("Message")
    """
    return _logger_instance.get_logger(name)

def set_console_level(level: str):
    """Set console output level"""
    _logger_instance.set_console_level(level)

def disable_console():
    """Disable console logging output"""
    _logger_instance.disable_console()
