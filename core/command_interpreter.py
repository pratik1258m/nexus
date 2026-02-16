"""
Nexus Command Interpreter - Local-first command routing
Separates command understanding from execution for latency optimization
"""

import re
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from core.logger import get_logger
from core.task_memory import MemoryManager
from core.registry import SkillRegistry

logger = get_logger(__name__)


@dataclass
class CommandIntent:
    """Parsed command with action, entities, and confidence"""
    action: str
    params: Dict[str, Any]
    confidence: float
    needs_api: bool
    original_command: str
    
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
    
    COMMAND_PATTERNS = [
        # New pattern for "send <content> to <name>" (e.g. "send linked list code to Bob")
        # Uses negative lookahead to avoid capturing "send message to" which is handled below
        (r'^(?:open\s+(?:whatsapp|chat)\s+(?:and\s+)?)?send\s+(?!message\s+to\s)(\w[\w\s]*?)\s+to\s+(\w[\w\s]*)$', 'send_whatsapp_message',
         lambda m: {'message': m.group(1).strip(), 'name': m.group(2).strip()}, 0.93),

        (r'^(?:open\s+)?(chrome|safari|firefox|edge)\s+(?:and\s+)?send\s+(?:message\s+)?(?:to\s+)?(\w+)\s+(?:saying\s+)?(.+)$', 'send_whatsapp_message',
         lambda m: {'browser': m.group(1).lower(), 'name': m.group(2).strip(), 'message': m.group(3).strip()}, 0.95),

        (r'^(?:open\s+)?whatsapp\s+(?:and\s+)?send\s+(?:message\s+)?(?:to\s+)?(\w+)\s+(?:saying\s+)?(.+)$', 'send_whatsapp_message',
         lambda m: {'name': m.group(1).strip(), 'message': m.group(2).strip()}, 0.92),
        
        (r'^send\s+(?:message\s+)?(?:to\s+)?(\w+)\s+(?:on\s+whatsapp\s+)?(?:saying\s+)?(.+)$', 'send_whatsapp_message',
         lambda m: {'name': m.group(1).strip(), 'message': m.group(2).strip()}, 0.88),
        
        (r'^(?:message|text)\s+(\w+)\s+(.+)$', 'send_whatsapp_message',
         lambda m: {'name': m.group(1).strip(), 'message': m.group(2).strip()}, 0.80),
        
        (r'^(?:open|edit)\s+(.+?)\s+(?:in|with|using)\s+([a-zA-Z0-9\s]+)$', 'open_app',
         lambda m: {'path': m.group(1).strip(), 'app_name': m.group(2).strip()}, 0.96),

        (r'^(?:open|launch|start)\s+([a-zA-Z][a-zA-Z0-9\s]{0,30})$', 'open_app', 
         lambda m: {'app_name': m.group(1).strip()}, 0.95),
        
        (r'^(?:close|quit|exit)\s+([a-zA-Z][a-zA-Z0-9\s]{0,30})$', 'close_app',
         lambda m: {'app_name': m.group(1).strip()}, 0.95),
        
        (r'^(?:set\s+)?volume\s+(?:to\s+)?(\d+)$', 'set_volume',
         lambda m: {'level': int(m.group(1))}, 0.98),

        (r'^(?:create|make)\s+(?:a\s+)?(?:new\s+)?file\s+(?:named\s+)?([\w\-\.]+)(?:\s+with\s+(?:content|text)\s+(.+))?$', 'manage_file',
         lambda m: {'action': 'create', 'filename': m.group(1).strip(), 'content': m.group(2).strip() if m.group(2) else ''}, 0.95),

        (r'^(?:delete|remove)\s+(?:the\s+)?file\s+(?:named\s+)?([\w\-\.]+)$', 'manage_file',
         lambda m: {'action': 'delete', 'filename': m.group(1).strip()}, 0.95),
        
        (r'^(?:search|google)\s+(?:for\s+)?(.+)$', 'google_search',
         lambda m: {'query': m.group(1).strip()}, 0.90),
        
        (r'^(?:open|go\s+to|visit)\s+(?:website\s+)?([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)$', 'open_website',
         lambda m: {'url': m.group(1).strip()}, 0.92),
        
        (r'^play\s+(.+)(?:\s+on\s+youtube)?$', 'play_on_youtube',
         lambda m: {'query': m.group(1).strip()}, 0.88),
        

        
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
    
    def interpret(self, command: str) -> List[CommandIntent]:
        """
        Interpret command and return list of intents (supporting compound commands)
        
        Args:
            command: Raw command text
            
        Returns:
            List of CommandIntent objects
        """
        clean_cmd = self._clean_command(command)
        
        # Split compound commands (simple splitting by specific delimiters)
        # Be careful not to split inside quotes or complex phrases handled by regex
        sub_commands = self._split_compound_command(clean_cmd)
        
        intents = []
        for sub_cmd in sub_commands:
            if not sub_cmd.strip():
                continue
                
            intent = self._pattern_match(sub_cmd.strip())
            
            if intent:
                logger.info(
                    f"Local interpretation: {intent.action} "
                    f"(confidence: {intent.confidence:.2f})"
                )
                intents.append(intent)
            else:
                logger.debug(f"No pattern match for '{sub_cmd}' - requiring API")
                # If one part fails generic matching, we might still want to try API
                # But for now, if it's a compound command, we might fallback entire thing?
                # Or just add a generic API intent for this part
                intents.append(CommandIntent(
                    action='api_required',
                    params={},
                    confidence=0.0,
                    needs_api=True,
                    original_command=sub_cmd
                ))
        
        # If no commands found (empty), return API required for original
        if not intents:
             return [CommandIntent(
                action='api_required',
                params={},
                confidence=0.0,
                needs_api=True,
                original_command=command
            )]
            
        return intents

    def _split_compound_command(self, command: str) -> List[str]:
        """Split command by 'and', 'then'"""
        # This is a basic implementation. Ideally use regex to avoid splitting inside quotes
        # But for "open X and write Y", simple split usually works if X doesn't contain 'and'
        
        # Regex to split by ' and ' or ' then ', ignoring case
        # We use a positive lookbehind/ahead to keep delimiters? No, we want to remove them.
        parts = re.split(r'\s+(?:and|then)\s+', command, flags=re.IGNORECASE)
        return parts
    
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
                    
                    confidence = self._adjust_confidence_with_context(
                        action, params, base_confidence
                    )
                    
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
        if action == 'send_whatsapp_message':
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
        prefixes = ['nexus', 'nexus ai', 'hey nexus', 'ok nexus', 'please']
        clean = command.lower().strip()
        
        for prefix in prefixes:
            if clean.startswith(prefix):
                clean = clean[len(prefix):].strip()
        
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
