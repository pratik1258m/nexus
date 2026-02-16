import json
import os
from datetime import datetime
from typing import List, Dict, Any, Callable
from core.skill import Skill

class NotesSkill(Skill):
    def __init__(self):
        self.notes_dir = os.path.expanduser('~/.nexus_notes')
        if not os.path.exists(self.notes_dir):
            os.makedirs(self.notes_dir)

    @property
    def name(self) -> str:
        return 'notes_skill'

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                'type': 'function',
                'function': {
                    'name': 'save_note',
                    'description': 'Save a text note',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'title': {'type': 'string', 'description': 'Title of the note'},
                            'content': {'type': 'string', 'description': 'Content of the note'}
                        },
                        'required': ['title', 'content']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'get_note',
                    'description': 'Retrieve a saved note by title',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'title': {'type': 'string', 'description': 'Title of the note'}
                        },
                        'required': ['title']
                    }
                }
            }
        ]

    def get_functions(self) -> Dict[str, Callable]:
        return {
            'save_note': self.save_note,
            'get_note': self.get_note
        }

    def save_note(self, title: str, content: str) -> str:
        file_path = os.path.join(self.notes_dir, f"{title}.txt")
        try:
            with open(file_path, 'w') as f:
                f.write(content)
            return json.dumps({'status': 'success', 'message': f"Note '{title}' saved successfully."})
        except Exception as e:
            return json.dumps({'status': 'error', 'message': str(e)})

    def get_note(self, title: str) -> str:
        file_path = os.path.join(self.notes_dir, f"{title}.txt")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                return json.dumps({'status': 'success', 'content': content})
            except Exception as e:
                return json.dumps({'status': 'error', 'message': str(e)})
        return json.dumps({'status': 'not_found', 'message': f"Note '{title}' not found."})
