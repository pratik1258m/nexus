"""
Nexus State Machine - Strict synchronous state control
Implements IDLE → THINKING → EXECUTING → COMPLETED flow with abort capability
"""

import threading
from enum import Enum, auto
from typing import Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)


class NexusState(Enum):
    """Nexus AI states - strict sequential flow"""
    IDLE = auto()           # Ready for new command
    THINKING = auto()       # Interpreting command
    EXECUTING = auto()      # Executing command/tool
    COMPLETED = auto()      # Task completed successfully
    ERROR = auto()          # Task failed
    ABORTING = auto()       # Aborting current task


@dataclass
class StateTransition:
    """Record of a state transition"""
    from_state: NexusState
    to_state: NexusState
    timestamp: datetime
    reason: Optional[str] = None


class StateManager:
    """
    Thread-safe state manager with strict transition rules
    Ensures only one task executes at a time
    """
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        NexusState.IDLE: [NexusState.THINKING],
        NexusState.THINKING: [NexusState.EXECUTING, NexusState.ERROR, NexusState.ABORTING],
        NexusState.EXECUTING: [NexusState.COMPLETED, NexusState.ERROR, NexusState.ABORTING],
        NexusState.COMPLETED: [NexusState.IDLE],
        NexusState.ERROR: [NexusState.IDLE],
        NexusState.ABORTING: [NexusState.IDLE],
    }
    
    def __init__(self):
        self._current_state = NexusState.IDLE
        self._lock = threading.RLock()
        self._history: List[StateTransition] = []
        self._callbacks: dict[NexusState, List[Callable]] = {}
        self._max_history = 100
        
        logger.info("StateManager initialized in IDLE state")
    
    @property
    def current_state(self) -> NexusState:
        """Get current state (thread-safe)"""
        with self._lock:
            return self._current_state
    
    @property
    def is_idle(self) -> bool:
        """Check if system is idle and ready for commands"""
        return self.current_state == NexusState.IDLE
    
    @property
    def is_busy(self) -> bool:
        """Check if system is busy (not idle)"""
        return self.current_state != NexusState.IDLE
    
    def can_transition_to(self, target_state: NexusState) -> bool:
        """Check if transition to target state is valid"""
        with self._lock:
            return target_state in self.VALID_TRANSITIONS.get(self._current_state, [])
    
    def transition(self, target_state: NexusState, reason: Optional[str] = None) -> bool:
        """
        Attempt atomic state transition
        
        Args:
            target_state: Desired state
            reason: Optional reason for transition
            
        Returns:
            True if transition successful, False if invalid
        """
        with self._lock:
            if not self.can_transition_to(target_state):
                logger.warning(
                    f"Invalid transition: {self._current_state.name} → {target_state.name}"
                )
                return False
            
            # Record transition
            transition = StateTransition(
                from_state=self._current_state,
                to_state=target_state,
                timestamp=datetime.now(),
                reason=reason
            )
            
            self._history.append(transition)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            
            # Execute transition
            old_state = self._current_state
            self._current_state = target_state
            
            logger.info(
                f"State transition: {old_state.name} → {target_state.name}"
                + (f" ({reason})" if reason else "")
            )
            
            # Trigger callbacks
            self._trigger_callbacks(target_state)
            
            return True
    
    def force_idle(self, reason: str = "forced reset"):
        """Force system back to IDLE (emergency use only)"""
        with self._lock:
            old_state = self._current_state
            self._current_state = NexusState.IDLE
            
            transition = StateTransition(
                from_state=old_state,
                to_state=NexusState.IDLE,
                timestamp=datetime.now(),
                reason=f"FORCED: {reason}"
            )
            self._history.append(transition)
            
            logger.warning(f"FORCED state reset: {old_state.name} → IDLE ({reason})")
            self._trigger_callbacks(NexusState.IDLE)
    
    def register_callback(self, state: NexusState, callback: Callable):
        """Register callback for state entry"""
        with self._lock:
            if state not in self._callbacks:
                self._callbacks[state] = []
            self._callbacks[state].append(callback)
            logger.debug(f"Registered callback for {state.name}")
    
    def _trigger_callbacks(self, state: NexusState):
        """Trigger all callbacks for state (internal)"""
        callbacks = self._callbacks.get(state, [])
        for callback in callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.error(f"Callback error for {state.name}: {e}")
    
    def get_history(self, limit: int = 10) -> List[StateTransition]:
        """Get recent state transition history"""
        with self._lock:
            return self._history[-limit:]
    
    def wait_for_idle(self, timeout: float = 10.0) -> bool:
        """
        Wait for system to return to IDLE state
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            True if IDLE reached, False if timeout
        """
        import time
        start = time.time()
        
        while time.time() - start < timeout:
            if self.is_idle:
                return True
            time.sleep(0.1)
        
        logger.warning(f"Timeout waiting for IDLE (current: {self.current_state.name})")
        return False
    
    def __repr__(self) -> str:
        return f"StateManager(current={self._current_state.name})"
