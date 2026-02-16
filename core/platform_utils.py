"""
Cross-platform utility functions for Nexus AI
Provides OS detection and platform-specific helpers
"""

import platform
import os
from pathlib import Path
from typing import Literal

OSType=Literal['macos', 'windows', 'linux']

def get_os() -> OSType:
    """
    Detect the current operating system
    
    Returns:
        'macos', 'windows', or 'linux'
    """
    system=platform.system().lower()
    if system=='darwin':
        return 'macos'
    elif system=='windows':
        return 'windows'
    elif system=='linux':
        return 'linux'
    else:
        return 'linux'

def get_home_dir() -> Path:
    """
    Get user's home directory (cross-platform)
    
    Returns:
        Path object to home directory
    """
    return Path.home()

def get_nexus_dir() -> Path:
    """
    Get Nexus AI data directory (cross-platform)
    
    Returns:
        Path to ~/.nexus directory
    """
    nexus_dir=get_home_dir() / '.nexus'
    nexus_dir.mkdir(exist_ok=True)
    return nexus_dir

def get_log_dir() -> Path:
    """
    Get logs directory (cross-platform)
    
    Returns:
        Path to logs directory
    """
    log_dir=get_nexus_dir() / 'logs'
    log_dir.mkdir(exist_ok=True)
    return log_dir

def is_feature_available(feature: str) -> bool:
    """
    Check if a feature is available on current platform
    
    Args:
        feature: Feature name ('voice', 'gui', 'automation', etc.)
    
    Returns:
        True if feature is supported on this platform
    """
    current_os=get_os()
    
    feature_matrix={
        'voice_tts': {'macos': True, 'windows': True, 'linux': True},
        'voice_stt': {'macos': True, 'windows': True, 'linux': True},
        'gui': {'macos': True, 'windows': True, 'linux': True},
        'app_opening': {'macos': True, 'windows': True, 'linux': True},
        'volume_control': {'macos': True, 'windows': True, 'linux': False},
        'whatsapp': {'macos': True, 'windows': True, 'linux': True},
        'applescript': {'macos': True, 'windows': False, 'linux': False},
    }
    
    if feature not in feature_matrix:
        return True
    
    return feature_matrix[feature].get(current_os, False)

def get_default_browser() -> str:
    """
    Get default browser name for current platform
    
    Returns:
        Browser name
    """
    current_os=get_os()
    
    if current_os=='macos':
        return 'Safari'
    elif current_os=='windows':
        return 'Microsoft Edge'
    else:
        return 'Firefox'

def get_text_editor() -> str:
    """
    Get default text editor for current platform
    
    Returns:
        Text editor name
    """
    current_os=get_os()
    
    if current_os=='macos':
        return 'TextEdit'
    elif current_os=='windows':
        return 'notepad'
    else:
        return 'gedit'

def get_calculator_app() -> str:
    """
    Get calculator app name for current platform
    
    Returns:
        Calculator app name
    """
    current_os=get_os()
    
    if current_os=='macos':
        return 'Calculator'
    elif current_os=='windows':
        return 'calc'
    else:
        return 'gnome-calculator'

def get_terminal_app() -> str:
    """
    Get terminal app name for current platform
    
    Returns:
        Terminal app name
    """
    current_os=get_os()
    
    if current_os=='macos':
        return 'Terminal'
    elif current_os=='windows':
        return 'cmd'
    else:
        return 'gnome-terminal'

if __name__=='__main__':
    print(f"OS: {get_os()}")
    print(f"Home: {get_home_dir()}")
    print(f"Nexus Dir: {get_nexus_dir()}")
    print(f"Log Dir: {get_log_dir()}")
    print(f"Default Browser: {get_default_browser()}")
    print(f"Text Editor: {get_text_editor()}")
    print(f"Calculator: {get_calculator_app()}")
    print(f"Terminal: {get_terminal_app()}")
    print(f"\nFeature Availability:")
    for feature in ['voice_tts', 'gui', 'app_opening', 'volume_control', 'whatsapp']:
        print(f"  {feature}: {is_feature_available(feature)}")
