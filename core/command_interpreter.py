"""
Nexus Command Interpreter - Local-first command routing
Separates command understanding from execution for latency optimization
"""

import re
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from core.logger import get_logger
from core.task_memory import MemoryManager
from core.registry import SkillRegistry

logger = get_logger(__name__)


@dataclass
class CommandIntent:
    """Parsed command with action, entities, and confidence"""
    action: str                           # Function to call (open_app, send_whatsapp_message, etc.)
    params: Dict[str, Any]                # Function parameters
    confidence: float                     # Confidence score (0.0-1.0)
    needs_api: bool                       # Whether API interpretation needed
    original_command: str                 # Original command text
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if confidence is high enough for local execution"""
        return self.confidence >= 0.9
    
    @property
    def is_medium_confidence(self) -> bool:
        """Check if confidence is medium (needs validation)"""
        return 0.5 <= self.confidence < 0.9


class CommandInterpreter:
    """
    Interprets commands using pattern matching and context
    Routes high-confidence commands to local execution (no API)
    """
    
    # Command patterns with confidence scores
    # Format: (pattern, action, param_extractor, confidence)
    # IMPORTANT: Order matters - more specific patterns first!
    COMMAND_PATTERNS = [
        # WhatsApp - HIGH priority (before generic open/send)
        (r'^(?:open\s+)?whatsapp\s+(?:and\s+)?send\s+(?:message\s+)?(?:to\s+)?(\w+)\s+(?:saying\s+)?(.+)$', 'send_whatsapp_message',
         lambda m: {'name': m.group(1).strip(), 'message': m.group(2).strip()}, 0.92),
        
        (r'^send\s+(?:message\s+)?(?:to\s+)?(\w+)\s+(?:on\s+whatsapp\s+)?(?:saying\s+)?(.+)$', 'send_whatsapp_message',
         lambda m: {'name': m.group(1).strip(), 'message': m.group(2).strip()}, 0.88),
        
        (r'^(?:message|text)\s+(\w+)\s+(.+)$', 'send_whatsapp_message',
         lambda m: {'name': m.group(1).strip(), 'message': m.group(2).strip()}, 0.80),
        
        # System operations - HIGH confidence (but after WhatsApp)
        (r'^(?:open|launch|start)\s+([a-zA-Z][a-zA-Z0-9\s]{0,30})$', 'open_app', 
         lambda m: {'app_name': m.group(1).strip()}, 0.95),
        
        (r'^(?:close|quit|exit)\s+([a-zA-Z][a-zA-Z0-9\s]{0,30})$', 'close_app',
         lambda m: {'app_name': m.group(1).strip()}, 0.95),
        
        (r'^(?:set\s+)?volume\s+(?:to\s+)?(\d+)$', 'set_volume',
         lambda m: {'level': int(m.group(1))}, 0.98),
        
        # Web operations - HIGH confidence
        (r'^(?:search|google)\s+(?:for\s+)?(.+)$', 'google_search',
         lambda m: {'query': m.group(1).strip()}, 0.90),
        
        (r'^(?:open|go\s+to|visit)\s+(?:website\s+)?(.+\..+)$', 'open_website',
         lambda m: {'url': m.group(1).strip()}, 0.92),
        
        (r'^play\s+(.+)(?:\s+on\s+youtube)?$', 'play_on_youtube',
         lambda m: {'query': m.group(1).strip()}, 0.88),
        
        # Greetings - HIGH confidence (no action needed)
        (r'^(?:hi|hello|hey)(?:\s+nexus)?$', 'greeting',
         lambda m: {}, 0.99),
        
        (r'^(?:thank|thanks)(?:\s+you)?$', 'thanks',
         lambda m: {}, 0.99),
    ]
    
    def __init__(self, registry: SkillRegistry, memory_manager: MemoryManager):
        """
        Initialize command interpreter
        
        Args:
            registry: Skill registry for function lookup
            memory_manager: Memory manager for context
        """
        self.registry = registry
        self.memory = memory_manager
        logger.info("CommandInterpreter initialized")
    
    def interpret(self, command: str) -> CommandIntent:
        """
        Interpret command and return intent
        
        Args:
            command: Raw command text
            
        Returns:
            CommandIntent with action, params, and confidence
        """
        # Clean command
        clean_cmd = self._clean_command(command)
        
        # Try pattern matching first (local interpretation)
        intent = self._pattern_match(clean_cmd)
        
        if intent:
            logger.info(
                f"Local interpretation: {intent.action} "
                f"(confidence: {intent.confidence:.2f})"
            )
            return intent
        
        # No pattern match - needs API interpretation
        logger.debug("No pattern match - requires API interpretation")
        return CommandIntent(
            action='api_required',
            params={},
            confidence=0.0,
            needs_api=True,
            original_command=command
        )
    
    def _pattern_match(self, command: str) -> Optional[CommandIntent]:
        """
        Match command against known patterns
        
        Args:
            command: Cleaned command text
            
        Returns:
            CommandIntent if pattern matched, None otherwise
        """
        for pattern, action, param_extractor, base_confidence in self.COMMAND_PATTERNS:
            match = re.match(pattern, command, re.IGNORECASE)
            if match:
                try:
                    params = param_extractor(match)
                    
                    # Enhance with context if available
                    confidence = self._adjust_confidence_with_context(
                        action, params, base_confidence
                    )
                    
                    # Validate function exists
                    if action not in ['greeting', 'thanks']:
                        func = self.registry.get_function(action)
                        if not func:
                            logger.warning(f"Function not found: {action}")
                            continue
                    
                    return CommandIntent(
                        action=action,
                        params=params,
                        confidence=confidence,
                        needs_api=confidence < 0.9,
                        original_command=command
                    )
                except Exception as e:
                    logger.error(f"Pattern extraction error: {e}")
                    continue
        
        return None
    
    def _adjust_confidence_with_context(
        self,
        action: str,
        params: Dict[str, Any],
        base_confidence: float
    ) -> float:
        """
        Adjust confidence based on context memory
        
        Args:
            action: Intended action
            params: Action parameters
            base_confidence: Base confidence from pattern
            
        Returns:
            Adjusted confidence score
        """
        # Check for recent related actions
        if action == 'send_whatsapp_message':
            # If WhatsApp was recently opened, boost confidence
            recent_app = self.memory.get_entity('app', max_age_seconds=60)
            if recent_app and 'whatsapp' in recent_app.lower():
                logger.debug("Context boost: WhatsApp recently opened")
                return min(base_confidence + 0.1, 1.0)
        
        return base_confidence
    
    def _clean_command(self, command: str) -> str:
        """
        Clean and normalize command text
        
        Args:
            command: Raw command
            
        Returns:
            Cleaned command
        """
        # Remove common prefixes
        prefixes = ['nexus', 'nexus ai', 'hey nexus', 'ok nexus', 'please']
        clean = command.lower().strip()
        
        for prefix in prefixes:
            if clean.startswith(prefix):
                clean = clean[len(prefix):].strip()
        
        # Remove trailing punctuation
        clean = clean.rstrip('.,!?')
        
        return clean
    
    def get_response_for_simple_action(self, action: str) -> Optional[str]:
        """
        Get canned response for simple actions (no execution needed)
        
        Args:
            action: Action type
            
        Returns:
            Response string or None if execution needed
        """
        SIMPLE_RESPONSES = {
            'greeting': 'Hello.',
            'thanks': 'Welcome.',
        }
        
        return SIMPLE_RESPONSES.get(action)
