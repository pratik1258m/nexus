import os

# Suppress annoying third-party deprecation warnings (google-auth, urllib3 NotOpenSSLWarning) globally
# This must happen before *any* other imports to catch implicit site-packages resolutions
os.environ["PYTHONWARNINGS"] = "ignore"

import sys
import argparse
import threading
import time
import string
from pathlib import Path
import signal
import queue

from core.logger import get_logger, set_console_level, disable_console
from core.config import get_config, validate_config
from core.voice import speak, listen
from core.registry import SkillRegistry
from core.engine import NexusEngine
from gui.app import NexusMainWindow, P_SUCCESS, P_PROCESSING, P_LISTENING, P_PRIMARY
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor

logger=get_logger(__name__)

class NexusAppWindow(NexusMainWindow):
    """Bridge between Nexus AI loop and the Nexus UI"""
    status_changed=pyqtSignal(str, str)
    
    def __init__(self, pause_event):
        super().__init__()
        self.pause_event=pause_event
        self.status_changed.connect(self._update_ui_status)
        
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
            
        logger.info("Nexus UI initialized and linked to AI core")

    def _update_ui_status(self, status, command):
        color=P_PRIMARY
        if "Ready" in status or "✨" in status:
            color=P_SUCCESS
        elif "Listening" in status or "🎤" in status:
            color=P_LISTENING
        elif "Processing" in status or "🔄" in status:
            color=P_PROCESSING
        elif "Error" in status or "❌" in status:
            color=QColor("#FFADAD")
            
        self.status_badge.set_status(status, color)
        
        if command:
            logger.info(f"AI UI Status Update: {status} | Command: {command}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)

def validate_startup_config():
    """Validate configuration and display warnings/errors"""
    is_valid, messages=validate_config()
    
    if not is_valid:
        logger.critical("Configuration validation failed:")
        for msg in messages:
            if "required" in msg.lower() or "error" in msg.lower():
                logger.error(f"  ❌ {msg}")
            else:
                logger.warning(f"  ⚠️  {msg}")
        logger.critical("Please check your .env file and fix the errors above.")
        sys.exit(1)
    else:
        for msg in messages:
            logger.warning(f"⚠️  {msg}")
    
    return is_valid

def nexus_loop(pause_event, registry, args, gui_window=None):
    """Main Nexus AI loop with state machine control"""
    from core.state_machine import StateManager, NexusState
    from core.task_memory import MemoryManager
    from core.command_interpreter import CommandInterpreter
    from core.config import get_config
    
    loop_logger=get_logger('nexus_loop')
    
    config = get_config()
    state_manager = StateManager()
    memory_manager = MemoryManager(ttl_seconds=config.state_machine.memory_ttl_seconds)
    nexus = NexusEngine(registry)
    interpreter = CommandInterpreter(registry, memory_manager)
    
    if args.text:
        loop_logger.info('Nexus AI Online. Ready for command (Text Mode).')
        print('NEXUS: Nexus AI Online. Ready for command (Text Mode).')
    else:
        loop_logger.info('Nexus AI Online. Ready for voice commands.')
        speak('Nexus Online.')
        if gui_window:
            gui_window.status_changed.emit("✨ Ready", "")
    
    def handle_abort():
        """Safely abort current task"""
        if state_manager.current_state in [NexusState.EXECUTING, NexusState.THINKING]:
            state_manager.transition(NexusState.ABORTING, "user abort")
            memory_manager.clear()
            state_manager.transition(NexusState.IDLE)
            if not args.text:
                speak('Stopped.')
            else:
                print('NEXUS: Stopped.')
    
    while True:
        if pause_event.is_set():
            time.sleep(0.5)
            continue
        
        if not state_manager.is_idle:
            loop_logger.warning(f"System busy (state: {state_manager.current_state.name})")
            time.sleep(0.5)
            continue
        
        if args.text:
            try:
                user_query=input('YOU: ').lower()
            except EOFError:
                break
        else:
            if gui_window:
                gui_window.status_changed.emit("🎤 Listening...", "")
            user_query=listen()
        
        if pause_event.is_set():
            continue
        
        if user_query == 'none' or not user_query:
            continue
        
        if 'quit' in user_query or 'exit' in user_query:
            loop_logger.info('Shutdown command received')
            if not args.text:
                speak('Goodbye.')
            break
        
        if 'stop' in user_query or 'abort' in user_query:
            handle_abort()
            continue
        
        try:
            if not state_manager.transition(NexusState.THINKING, "command received"):
                loop_logger.error("Failed to transition to THINKING")
                continue
            
            if gui_window:
                gui_window.status_changed.emit("🧠 Thinking...", user_query[:50])
            
            intents = interpreter.interpret(user_query)
            
            for intent in intents:
                loop_logger.debug(f"Processing Intent: {intent.action} (confidence: {intent.confidence:.2f})")
                
                # If we are in IDLE (e.g. 2nd command), go to THINKING first
                if state_manager.current_state == NexusState.IDLE:
                    if not state_manager.transition(NexusState.THINKING, "processing next sub-command"):
                        loop_logger.error("Failed to transition to THINKING")
                        break
                        
                if not state_manager.transition(NexusState.EXECUTING, f"executing {intent.action}"):
                    loop_logger.error("Failed to transition to EXECUTING")
                    state_manager.force_idle("transition failure")
                    break
                
                if gui_window:
                    gui_window.status_changed.emit("⚡ Executing...", intent.action)
                
                response = None
                
                if config.state_machine.enable_local_execution and intent.is_high_confidence:
                    loop_logger.info(f"Local execution: {intent.action}")
                    response = nexus.execute_local(intent)
                else:
                    # For API execution, we use the original sub-command or full query?
                    # valid point: if it's "api_required", intent.original_command holds the sub-command
                    query_to_use = intent.original_command if intent.original_command else user_query
                    enhanced_query = memory_manager.build_context_prompt(query_to_use)
                    loop_logger.info(f"API execution: {enhanced_query[:50]}...")
                    response = nexus.run_conversation(enhanced_query)
                
                memory_manager.add_context(
                    command=user_query,
                    result=response,
                    entities=intent.params if intent.action != 'api_required' else None
                )
                
                if not state_manager.transition(NexusState.COMPLETED, "task completed"):
                    loop_logger.error("Failed to transition to COMPLETED")
                    state_manager.force_idle("transition failure")
                    break
                
                if pause_event.is_set():
                    state_manager.transition(NexusState.IDLE)
                    break
                
                if response:
                    if args.text:
                        print(f'NEXUS: {response}')
                    else:
                        speak(response)
                        
                # Small delay and reset state for next command
                import time
                time.sleep(0.5)
                # Must go back to IDLE to allow transition to EXECUTING again
                state_manager.transition(NexusState.IDLE, "ready for next sub-command")
            
            # Ensure we end in IDLE (already done if loop finished normally)
            if not state_manager.is_idle:
                state_manager.transition(NexusState.IDLE, "ready for next command")
            
            if gui_window:
                gui_window.status_changed.emit("✨ Ready", "")
                
        except KeyboardInterrupt:
            handle_abort()
            break
        except Exception as e:
            loop_logger.error(f'Main loop error: {e}', exc_info=args.debug)
            
            state_manager.transition(NexusState.ERROR, str(e))
            
            if args.text:
                print(f'NEXUS: Error.')
            else:
                speak('Error.')
            
            state_manager.transition(NexusState.IDLE, "error recovery")
            
            if gui_window:
                gui_window.status_changed.emit("❌ Error", str(e)[:50])

def main():
    parser=argparse.ArgumentParser(description='NEXUS AI Assistant')
    parser.add_argument('--text', action='store_true', help='Run in text mode (no voice I/O)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with verbose logging')
    parser.add_argument('--log-level', type=str, default='INFO', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set logging level')
    args=parser.parse_args()
    
    if args.debug:
        set_console_level('DEBUG')
        logger.info("Debug mode enabled")
    else:
        set_console_level(args.log_level)
    
    logger.info("Validating configuration...")
    validate_startup_config()
    logger.info("Configuration validated successfully")
    
    pause_event=threading.Event()
    context={'pause_event': pause_event}
    
    logger.info("Loading skills...")
    registry=SkillRegistry()
    skills_dir=Path(__file__).parent / 'skills'
    registry.load_skills(str(skills_dir), context=context)
    logger.info(f"Loaded {len(registry.skill_classes)} skills successfully")
    
    if not args.text:
        from PyQt6.QtWidgets import QApplication
        app=QApplication(sys.argv)
        
        gui_window=NexusAppWindow(pause_event)
        gui_window.show()
        
        t=threading.Thread(
            target=nexus_loop, 
            args=(pause_event, registry, args, gui_window), 
            daemon=True
        )
        t.start()
        
        sys.exit(app.exec())
    else:
        t=threading.Thread(
            target=nexus_loop, 
            args=(pause_event, registry, args), 
            daemon=True
        )
        t.start()
        t.join()

if __name__ == '__main__':
    main()
