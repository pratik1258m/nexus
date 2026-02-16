import json
import os
from typing import List, Dict, Any, Callable
from core.skill import Skill

class TaskSkill(Skill):
    def __init__(self):
        self.tasks_file = os.path.expanduser('~/.nexus_tasks.json')
        self._ensure_file()
        self.tasks = self._load_tasks()

    def _ensure_file(self):
        if not os.path.exists(self.tasks_file):
            with open(self.tasks_file, 'w') as f:
                json.dump([], f)

    def _load_tasks(self) -> List[Dict]:
        try:
            with open(self.tasks_file, 'r') as f:
                return json.load(f)
        except:
            return []

    def _save_tasks(self):
        with open(self.tasks_file, 'w') as f:
            json.dump(self.tasks, f, indent=2)

    @property
    def name(self) -> str:
        return 'task_skill'

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                'type': 'function',
                'function': {
                    'name': 'add_task',
                    'description': 'Add a task to the todo list',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'task': {'type': 'string', 'description': 'Task description'},
                            'priority': {'type': 'string', 'enum': ['low', 'medium', 'high'], 'default': 'medium'}
                        },
                        'required': ['task']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'list_tasks',
                    'description': 'List all tasks',
                    'parameters': {'type': 'object', 'properties': {}}
                }
            }
        ]

    def get_functions(self) -> Dict[str, Callable]:
        return {
            'add_task': self.add_task,
            'list_tasks': self.list_tasks
        }

    def add_task(self, task: str, priority: str = 'medium') -> str:
        new_task = {
            'task': task,
            'priority': priority,
            'completed': False
        }
        self.tasks.append(new_task)
        self._save_tasks()
        return json.dumps({'status': 'success', 'message': f"Added task: {task}"})

    def list_tasks(self) -> str:
        if not self.tasks:
            return json.dumps({'status': 'success', 'message': 'Task list is empty.'})
        return json.dumps({'status': 'success', 'tasks': self.tasks})
