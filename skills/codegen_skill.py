"""
Code Generation Skill - Local fallback for when API tool calling fails
Handles code generation requests directly without API dependencies
"""
import os
import json
import pyautogui
from typing import List, Dict, Any, Callable
from core.skill import Skill
from core.logger import get_logger

logger = get_logger(__name__)


class CodeGenSkill(Skill):
    """Generate code files locally without API dependencies"""
    
    @property
    def name(self) -> str:
        return 'codegen_skill'
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                'type': 'function',
                'function': {
                    'name': 'generate_code_file',
                    'description': 'Save provided code content to a file. REQUIRED: You MUST provide the full code content.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'filename': {
                                'type': 'string',
                                'description': 'Output filename (e.g., script.py)'
                            },
                            'content': {
                                'type': 'string',
                                'description': 'The complete code content to write to the file.'
                            }
                        },
                        'required': ['filename', 'content']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'type_code',
                    'description': 'Type the provided code content into the active window (using clipboard for speed). REQUIRED: You MUST provide the full code content.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'content': {
                                'type': 'string',
                                'description': 'The complete code content to type.'
                            },
                            'app_name': {
                                'type': 'string',
                                'description': 'Optional. The name of the application to type into (e.g. "notepad", "vscode", "chrome").'
                            }
                        },
                        'required': ['content']
                    }
                }
            }
        ]
    
    def get_functions(self) -> Dict[str, Callable]:
        return {
            'generate_code_file': self.generate_code_file,
            'type_code': self.type_code
        }
    
    def generate_code_file(self, filename: str, content: str) -> str:
        """Save provided code content to a file"""
        try:
            # Handle user home directory expansion if needed (though filename should be simple)
            filename = os.path.basename(filename)
            
            filepath = os.path.join(os.path.expanduser('~/Documents/nexus'), filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w') as f:
                f.write(content)
            
            logger.info(f"Generated code file: {filepath}")
            return json.dumps({
                'status': 'success',
                'message': f'Created {filename}',
                'path': filepath
            })
        
        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return json.dumps({'status': 'error', 'message': str(e)})

    def type_code(self, content: str, app_name: str = None) -> str:
        """Type provided code content into active window"""
        try:
            import platform
            import os
            import time
            system = platform.system()
            
            if app_name:
                app_name_lower = app_name.lower()
                app_mapping = {
                    'notepad': {'Darwin': 'TextEdit', 'Windows': 'notepad', 'Linux': 'gedit'},
                    'vscode': {'Darwin': 'Visual Studio Code', 'Windows': 'code', 'Linux': 'code'},
                    'vs code': {'Darwin': 'Visual Studio Code', 'Windows': 'code', 'Linux': 'code'},
                    'code': {'Darwin': 'Visual Studio Code', 'Windows': 'code', 'Linux': 'code'},
                }
                actual_app = app_name
                if app_name_lower in app_mapping and system in app_mapping[app_name_lower]:
                    actual_app = app_mapping[app_name_lower][system]
                
                if system == 'Darwin':
                    os.system(f'''osascript -e 'tell application "{actual_app}" to activate' ''')
                    time.sleep(0.5)
            
            # Use clipboard for speed (pyautogui.write is too slow for code)
            import pyperclip
            
            pyperclip.copy(content)
            time.sleep(0.5)  # Synchronization buffer for the OS clipboard
            
            # Simulate paste
            # On Mac: AppleScript is most reliable, Windows/Linux: ctrl+v
            import platform
            import os
            
            if platform.system() == 'Darwin':
                os.system('''osascript -e 'tell application "System Events" to keystroke "v" using command down' ''')
            else:
                import pyautogui
                pyautogui.keyDown('ctrl')
                pyautogui.press('v')
                pyautogui.keyUp('ctrl')
            
            return json.dumps({
                'status': 'success',
                'message': 'Typed code content into active window'
            })
        except Exception as e:
            logger.error(f"Type code error: {e}")
            return json.dumps({'status': 'error', 'message': str(e)})
