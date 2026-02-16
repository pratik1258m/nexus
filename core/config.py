"""
Centralized configuration management for Nexus AI
Handles environment variables, validation, and default values
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

@dataclass
class APIConfig:
    """API configuration settings"""
    groq_api_key: Optional[str] = None
    groq_model: str='llama-3.3-70b-versatile'
    gemini_api_key: Optional[str] = None
    gemini_model: str='gemini-2.0-flash'
    openweathermap_api_key: Optional[str] = None
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate API configuration"""
        errors=[]
        warnings=[]
        
        if not self.groq_api_key and not self.gemini_api_key:
            errors.append("At least one AI API key (GROQ or GEMINI) is required")
        
        if not self.groq_api_key:
            warnings.append("GROQ_API_KEY not set - no fallback available if Gemini fails")
        
        if not self.gemini_api_key:
            warnings.append("GEMINI_API_KEY not set - will use Groq as primary")
        
        return (len(errors) == 0, errors + warnings)

@dataclass
class VoiceConfig:
    """Voice recognition and TTS settings"""
    energy_threshold_min: int=150
    energy_threshold_max: int=600
    pause_threshold: float=0.8
    listen_timeout: int=5
    phrase_time_limit: int=15
    ambient_duration: float=0.5
    preferred_voice: str='Daniel'
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate voice configuration"""
        errors=[]
        
        if self.energy_threshold_min >= self.energy_threshold_max:
            errors.append("energy_threshold_min must be less than energy_threshold_max")
        
        if self.pause_threshold <= 0:
            errors.append("pause_threshold must be positive")
        
        return (len(errors) == 0, errors)

@dataclass
class SystemConfig:
    """System-level configuration"""
    default_city: str='Mumbai'
    email_address: Optional[str] = None
    email_password: Optional[str] = None
    email_imap_server: str='imap.gmail.com'
    contacts_file: str='contacts.json'
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate system configuration"""
        warnings=[]
        
        if not self.email_address:
            warnings.append("EMAIL_ADDRESS not set - email features will be unavailable")
        
        if not self.email_password:
            warnings.append("EMAIL_PASSWORD not set - email features will be unavailable")
        
        return (True, warnings)

@dataclass
class StateMachineConfig:
    """State machine configuration"""
    memory_ttl_seconds: int = 60
    max_abort_wait_seconds: int = 5
    enable_local_execution: bool = True
    local_confidence_threshold: float = 0.9
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate state machine configuration"""
        errors = []
        
        if self.memory_ttl_seconds < 10:
            errors.append("memory_ttl_seconds must be >= 10")
        
        if self.local_confidence_threshold < 0.5 or self.local_confidence_threshold > 1.0:
            errors.append("local_confidence_threshold must be between 0.5 and 1.0")
        
        return (len(errors) == 0, errors)

@dataclass
class NexusConfig:
    """Main Nexus AI configuration"""
    api: APIConfig=field(default_factory=APIConfig)
    voice: VoiceConfig=field(default_factory=VoiceConfig)
    system: SystemConfig=field(default_factory=SystemConfig)
    state_machine: StateMachineConfig=field(default_factory=StateMachineConfig)
    
    # Paths
    base_dir: Path=field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path=field(default_factory=lambda: Path.home() / '.nexus')
    
    # Runtime settings
    debug_mode: bool=False
    log_level: str='INFO'
    
    def __post_init__(self):
        """Ensure data directory exists"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate entire configuration"""
        all_messages=[]
        
        api_valid, api_msgs=self.api.validate()
        voice_valid, voice_msgs=self.voice.validate()
        system_valid, system_msgs=self.system.validate()
        sm_valid, sm_msgs=self.state_machine.validate()
        
        all_messages.extend(api_msgs)
        all_messages.extend(voice_msgs)
        all_messages.extend(system_msgs)
        all_messages.extend(sm_msgs)
        
        is_valid=api_valid and voice_valid and system_valid and sm_valid
        return (is_valid, all_messages)

class ConfigManager:
    """Configuration manager singleton"""
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional[NexusConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance=super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is not None:
            return
        
        # Load environment variables
        load_dotenv()
        
        # Initialize configuration
        self._config=NexusConfig()
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # API Configuration
        self._config.api.groq_api_key=os.getenv('GROQ_API_KEY')
        self._config.api.groq_model=os.getenv('GROQ_MODEL', self._config.api.groq_model)
        self._config.api.gemini_api_key=os.getenv('GEMINI_API_KEY')
        self._config.api.gemini_model=os.getenv('GEMINI_MODEL', self._config.api.gemini_model)
        self._config.api.openweathermap_api_key=os.getenv('OPENWEATHERMAP_API_KEY')
        
        # Voice Configuration
        self._config.voice.energy_threshold_min=int(os.getenv('VOICE_ENERGY_MIN', self._config.voice.energy_threshold_min))
        self._config.voice.energy_threshold_max=int(os.getenv('VOICE_ENERGY_MAX', self._config.voice.energy_threshold_max))
        self._config.voice.pause_threshold=float(os.getenv('VOICE_PAUSE_THRESHOLD', self._config.voice.pause_threshold))
        self._config.voice.preferred_voice=os.getenv('VOICE_PREFERRED', self._config.voice.preferred_voice)
        
        # System Configuration
        self._config.system.default_city=os.getenv('DEFAULT_CITY', self._config.system.default_city)
        self._config.system.email_address=os.getenv('EMAIL_ADDRESS')
        self._config.system.email_password=os.getenv('EMAIL_PASSWORD')
        self._config.system.email_imap_server=os.getenv('EMAIL_IMAP_SERVER', self._config.system.email_imap_server)
        
        # State Machine Configuration
        self._config.state_machine.memory_ttl_seconds=int(os.getenv('MEMORY_TTL_SECONDS', self._config.state_machine.memory_ttl_seconds))
        self._config.state_machine.enable_local_execution=os.getenv('ENABLE_LOCAL_EXECUTION', 'true').lower() == 'true'
        self._config.state_machine.local_confidence_threshold=float(os.getenv('LOCAL_CONFIDENCE_THRESHOLD', self._config.state_machine.local_confidence_threshold))
        
        # Runtime settings
        self._config.debug_mode=os.getenv('DEBUG', 'false').lower() == 'true'
        self._config.log_level=os.getenv('LOG_LEVEL', 'INFO').upper()
    
    @property
    def config(self) -> NexusConfig:
        """Get current configuration"""
        return self._config
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration and return status with messages"""
        return self._config.validate()
    
    def get_api_config(self) -> APIConfig:
        """Get API configuration"""
        return self._config.api
    
    def get_voice_config(self) -> VoiceConfig:
        """Get voice configuration"""
        return self._config.voice
    
    def get_system_config(self) -> SystemConfig:
        """Get system configuration"""
        return self._config.system

# Global configuration instance
_config_manager=ConfigManager()

def get_config() -> NexusConfig:
    """
    Get the global configuration instance
    
    Usage:
        from core.config import get_config
        config=get_config()
        api_key=config.api.groq_api_key
    """
    return _config_manager.config

def validate_config() -> tuple[bool, list[str]]:
    """Validate configuration and return (is_valid, messages)"""
    return _config_manager.validate()
