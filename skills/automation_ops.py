import pyautogui
import json
import time
from typing import List, Dict, Any, Callable
from core.skill import Skill

class AutomationSkill(Skill):
    def __init__(self):
        pyautogui.FAILSAFE = True

    @property
    def name(self) -> str:
        return "automation_skill"

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "type_text",
                    "description": "Simulate keyboard typing to enter text.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The text to type"
                            },
                            "interval": {
                                "type": "number",
                                "description": "Seconds between keypresses (optional, default: 0.05)"
                            }
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "press_key",
                    "description": "Press a specific key or combination (e.g., 'enter', 'tab', 'esc', 'command', 'c').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "The key to press"
                            },
                        },
                        "required": ["key"]
                    }
                }
            },
            {
                 "type": "function",
                 "function": {
                     "name": "hotkey",
                     "description": "Press a combination of keys (e.g., ['command', 'c'] for copy).",
                     "parameters": {
                         "type": "object",
                         "properties": {
                             "keys": {
                                 "type": "array",
                                 "items": {"type": "string"},
                                 "description": "List of keys to press simultaneously"
                             }
                         },
                         "required": ["keys"]
                     }
                 }
            },
            {
                "type": "function",
                "function": {
                    "name": "click_position",
                    "description": "Click at specific screen coordinates.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "integer",
                                "description": "X coordinate on screen"
                            },
                            "y": {
                                "type": "integer",
                                "description": "Y coordinate on screen"
                            }
                        },
                        "required": ["x", "y"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_screen_size",
                    "description": "Get the current screen dimensions (width and height).",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]

    def get_functions(self) -> Dict[str, Callable]:
        return {
            "type_text": self.type_text,
            "press_key": self.press_key,
            "hotkey": self.hotkey,
            "click_position": self.click_position,
            "get_screen_size": self.get_screen_size
        }

    def type_text(self, text: str, interval: float = 0.05) -> str:
        try:
            # For long text, code blocks, or special characters, use clipboard paste
            # This is more reliable than pyautogui.write()
            if len(text) > 100 or '\n' in text or any(char in text for char in ['`', '{', '}', '[', ']', '"', "'"]):
                import pyperclip
                
                # Copy to clipboard
                pyperclip.copy(text)
                
                # Paste using Cmd+V (macOS)
                pyautogui.hotkey('command', 'v')
                time.sleep(0.3)
                
                return json.dumps({"status": "success", "message": f"Pasted {len(text)} characters via clipboard"})
            else:
                # For short simple text, use direct typing
                pyautogui.write(text, interval=interval)
                return json.dumps({"status": "success", "message": f"Typed: {text[:50]}"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def press_key(self, key: str) -> str:
        try:
            pyautogui.press(key)
            return json.dumps({"status": "success", "message": f"Pressed: {key}"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def hotkey(self, keys: List[str]) -> str:
        try:
            pyautogui.hotkey(*keys)
            return json.dumps({"status": "success", "message": f"Executed hotkey: {keys}"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def click_position(self, x: int, y: int) -> str:
        """Click at specific screen coordinates."""
        try:
            pyautogui.click(x, y)
            return json.dumps({"status": "success", "message": f"Clicked at ({x}, {y})"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def get_screen_size(self) -> str:
        """Get current screen dimensions."""
        try:
            size = pyautogui.size()
            return json.dumps({
                "status": "success",
                "width": size.width,
                "height": size.height
            })
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
