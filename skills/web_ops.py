import webbrowser
import json
from typing import List, Dict, Any, Callable
from core.skill import Skill


class WebSkill(Skill):

    @property
    def name(self) ->str:
        return 'web_skill'

    def get_tools(self) ->List[Dict[str, Any]]:
        return [{'type': 'function', 'function': {'name': 'google_search',
            'description': 'Search Google for a query', 'parameters': {
            'type': 'object', 'properties': {'search_term': {'type':
            'string'}}, 'required': ['search_term']}}}, {
                "type": "function",
                "function": {
                    "name": "open_website",
                    "description": "Open a specific website by URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "The URL to open (e.g., 'https://www.youtube.com')"}
                        },
                        "required": ["url"]
                    }
                }
            }, {
                "type": "function",
                "function": {
                    "name": "play_on_youtube",
                    "description": "Directly play a video on YouTube by topic or title.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string", "description": "The topic or video title to play"}
                        },
                        "required": ["topic"]
                    }
                }
            }]

    def get_functions(self) ->Dict[str, Callable]:
        return {
            'google_search': self.google_search,
            'open_website': self.open_website,
            'play_on_youtube': self.play_on_youtube
        }

    def google_search(self, search_term):
        try:
            webbrowser.open(f'https://www.google.com/search?q={search_term}')
            return json.dumps({'status': 'opened browser', 'term': search_term})
        except Exception as e:
            return json.dumps({'error': str(e)})

    def open_website(self, url: str) -> str:
        try:
            if not url.startswith('http'):
                url = 'https://' + url
            webbrowser.open(url)
            return json.dumps({"status": "success", "message": f"Opened {url}"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def play_on_youtube(self, topic: str) -> str:
        import pywhatkit
        try:
            pywhatkit.playonyt(topic)
            return json.dumps({"status": "success", "message": f"Playing {topic} on YouTube"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
