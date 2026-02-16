import json
import os
import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Callable
from core.skill import Skill
from core.logger import get_logger
from core.voice import speak

logger = get_logger(__name__)

class ReminderSkill(Skill):
    def __init__(self):
        self.reminders_file = os.path.expanduser('~/.nexus_reminders.json')
        self._ensure_file()
        self.reminders = self._load_reminders()
        self.stop_event = threading.Event()
        self.monitor_thread = threading.Thread(target=self._monitor_reminders, daemon=True)
        self.monitor_thread.start()

    def _ensure_file(self):
        if not os.path.exists(self.reminders_file):
            with open(self.reminders_file, 'w') as f:
                json.dump([], f)

    def _load_reminders(self) -> List[Dict]:
        try:
            with open(self.reminders_file, 'r') as f:
                return json.load(f)
        except:
            return []

    def _save_reminders(self):
        with open(self.reminders_file, 'w') as f:
            json.dump(self.reminders, f, indent=2)

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                'type': 'function',
                'function': {
                    'name': 'add_reminder',
                    'description': 'Add a new reminder',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'text': {'type': 'string', 'description': 'What to remind about'},
                            'time_str': {'type': 'string', 'description': 'Time in HH:MM format (24h)'}
                        },
                        'required': ['text', 'time_str']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'list_reminders',
                    'description': 'List all active reminders',
                    'parameters': {'type': 'object', 'properties': {}}
                }
            }
        ]

    def get_functions(self) -> Dict[str, Callable]:
        return {
            'add_reminder': self.add_reminder,
            'list_reminders': self.list_reminders
        }

    @property
    def name(self) -> str:
        return 'reminder_skill'

    def add_reminder(self, text: str, time_str: str) -> str:
        try:
            # Simple check for HH:MM format
            datetime.strptime(time_str, '%H:%M')
            reminder = {
                'text': text,
                'time': time_str,
                'created_at': datetime.now().isoformat(),
                'notified': False
            }
            self.reminders.append(reminder)
            self._save_reminders()
            return json.dumps({'status': 'success', 'message': f'Reminder set for {time_str}: {text}'})
        except Exception as e:
            return json.dumps({'status': 'error', 'message': str(e)})

    def list_reminders(self) -> str:
        active = [r for r in self.reminders if not r.get('notified')]
        if not active:
            return json.dumps({'status': 'success', 'message': 'No active reminders.'})
        return json.dumps({'status': 'success', 'reminders': active})

    def _monitor_reminders(self):
        while not self.stop_event.is_set():
            now = datetime.now().strftime('%H:%M')
            for r in self.reminders:
                if r['time'] == now and not r.get('notified'):
                    logger.info(f"🔔 REMINDER: {r['text']}")
                    speak(f"Excuse me, sir. You have a reminder: {r['text']}")
                    r['notified'] = True
                    self._save_reminders()
            time.sleep(30) # Check every 30 seconds
