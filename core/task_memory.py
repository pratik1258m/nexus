"""
Nexus Task Memory - Short-term context retention
Maintains context for multi-step commands (e.g., "open WhatsApp" → "send message")
"""

import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TaskContext:
    """Context from a completed task"""
    command: str                          # Original command
    entities: Dict[str, Any]              # Extracted entities (app, contact, etc.)
    result: str                           # Task result
    timestamp: datetime                   # When task completed
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional context
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if context has expired"""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > ttl_seconds
    
    def age_seconds(self) -> float:
        """Get age of context in seconds"""
        return (datetime.now() - self.timestamp).total_seconds()


class MemoryManager:
    """
    Manages short-term task memory for context retention
    Automatically expires old contexts
    """
    
    # Entity extraction patterns
    ENTITY_PATTERNS = {
        'app': r'\b(?:open|close|launch|quit)\s+(\w+(?:\s+\w+)?)',
        'contact': r'\b(?:to|message|call|text)\s+(\w+)',
        'action': r'\b(open|close|send|message|call|search|play|set)\b',
        'volume': r'\bvolume\s+(\d+)',
        'url': r'(https?://\S+|www\.\S+)',
    }
    
    def __init__(self, ttl_seconds: int = 60):
        """
        Initialize memory manager
        
        Args:
            ttl_seconds: Time-to-live for contexts (default 60s)
        """
        self.ttl_seconds = ttl_seconds
        self._contexts: List[TaskContext] = []
        self._max_contexts = 10
        
        logger.info(f"MemoryManager initialized (TTL: {ttl_seconds}s)")
    
    def add_context(
        self,
        command: str,
        result: str,
        entities: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add new task context
        
        Args:
            command: Original command text
            result: Task execution result
            entities: Extracted entities (auto-extracted if None)
            metadata: Additional context metadata
        """
        # Auto-extract entities if not provided
        if entities is None:
            entities = self._extract_entities(command)
        
        context = TaskContext(
            command=command,
            entities=entities,
            result=result,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self._contexts.append(context)
        
        # Limit context history
        if len(self._contexts) > self._max_contexts:
            self._contexts.pop(0)
        
        logger.debug(
            f"Added context: {command[:50]}... | Entities: {entities}"
        )
    
    def get_recent_context(self, max_age_seconds: Optional[int] = None) -> Optional[TaskContext]:
        """
        Get most recent non-expired context
        
        Args:
            max_age_seconds: Override TTL for this query
            
        Returns:
            Most recent valid context or None
        """
        self._cleanup_expired()
        
        if not self._contexts:
            return None
        
        recent = self._contexts[-1]
        ttl = max_age_seconds if max_age_seconds is not None else self.ttl_seconds
        
        if recent.is_expired(ttl):
            return None
        
        return recent
    
    def get_entity(self, entity_type: str, max_age_seconds: Optional[int] = None) -> Optional[Any]:
        """
        Get specific entity from recent context
        
        Args:
            entity_type: Type of entity (app, contact, action, etc.)
            max_age_seconds: Override TTL for this query
            
        Returns:
            Entity value or None
        """
        context = self.get_recent_context(max_age_seconds)
        if context:
            return context.entities.get(entity_type)
        return None
    
    def has_recent_action(self, action: str, max_age_seconds: int = 30) -> bool:
        """
        Check if specific action was recently performed
        
        Args:
            action: Action to check (open, send, etc.)
            max_age_seconds: How recent to check
            
        Returns:
            True if action found in recent context
        """
        context = self.get_recent_context(max_age_seconds)
        if context:
            return context.entities.get('action') == action
        return False
    
    def build_context_prompt(self, new_command: str) -> str:
        """
        Build context-aware prompt for command interpretation
        
        Args:
            new_command: New command to interpret
            
        Returns:
            Enhanced prompt with context
        """
        context = self.get_recent_context()
        
        if not context:
            return new_command
        
        # Detect follow-up/reference commands
        follow_up_indicators = [
            'do that', 'try that', 'retry', 'again', 'same thing',
            'on chrome', 'on safari', 'with chrome', 'with safari',
            'use chrome', 'use safari', 'in chrome', 'in safari'
        ]
        
        new_lower = new_command.lower()
        is_follow_up = any(indicator in new_lower for indicator in follow_up_indicators)
        
        if is_follow_up:
            # This is a follow-up command - inject full previous context
            logger.info(f"Detected follow-up command: {new_command}")
            
            # Extract browser preference from new command
            browser = None
            if 'chrome' in new_lower:
                browser = 'chrome'
            elif 'safari' in new_lower:
                browser = 'safari'
            
            # Build enhanced prompt with full context
            enhanced_parts = []
            
            # Include previous command
            if context.command:
                enhanced_parts.append(f"Previous command: {context.command}")
            
            # Include entities from previous command
            if context.entities:
                if 'name' in context.entities:
                    enhanced_parts.append(f"Contact: {context.entities['name']}")
                if 'message' in context.entities:
                    enhanced_parts.append(f"Message: {context.entities['message']}")
                if 'action' in context.entities:
                    enhanced_parts.append(f"Action: {context.entities['action']}")
            
            # Add browser preference if detected
            if browser:
                enhanced_parts.append(f"Browser: {browser}")
            
            # Reconstruct the command
            if context.entities.get('action') == 'send_whatsapp_message':
                name = context.entities.get('name', 'unknown')
                message = context.entities.get('message', 'hello')
                browser_str = f" using {browser}" if browser else ""
                enhanced = f"send whatsapp message to {name} saying {message}{browser_str}"
                logger.info(f"Reconstructed command: {enhanced}")
                return enhanced
            
            # Fallback: append context to new command
            context_str = " | ".join(enhanced_parts)
            return f"{new_command} [Context: {context_str}]"
        
        # Not a follow-up - just add hints
        hints = []
        
        if 'app' in context.entities:
            app = context.entities['app']
            hints.append(f"{app} was recently opened")
        
        if 'contact' in context.entities:
            contact = context.entities['contact']
            hints.append(f"recent contact: {contact}")
        
        if hints:
            context_str = " | ".join(hints)
            enhanced = f"{new_command} [Context: {context_str}]"
            logger.debug(f"Enhanced prompt with context: {enhanced}")
            return enhanced
        
        return new_command
    
    def clear(self):
        """Clear all contexts"""
        count = len(self._contexts)
        self._contexts.clear()
        logger.info(f"Cleared {count} contexts")
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract entities from command text
        
        Args:
            text: Command text
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        text_lower = text.lower()
        
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                entities[entity_type] = match.group(1).strip()
        
        return entities
    
    def _cleanup_expired(self):
        """Remove expired contexts"""
        before_count = len(self._contexts)
        self._contexts = [
            ctx for ctx in self._contexts
            if not ctx.is_expired(self.ttl_seconds)
        ]
        
        removed = before_count - len(self._contexts)
        if removed > 0:
            logger.debug(f"Cleaned up {removed} expired contexts")
    
    def get_all_contexts(self) -> List[TaskContext]:
        """Get all non-expired contexts"""
        self._cleanup_expired()
        return self._contexts.copy()
    
    def __repr__(self) -> str:
        self._cleanup_expired()
        return f"MemoryManager(contexts={len(self._contexts)}, ttl={self.ttl_seconds}s)"
