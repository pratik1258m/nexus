from core.skill import Skill
import subprocess
import threading
import sys
import os


class VisionSkill(Skill):

    @property
    def name(self):
        return 'vision_skill'

    def get_tools(self):
        return [{'type': 'function', 'function': {'name':
            'start_live_vision', 'description':
            'Start the live vision system (opens a new window with camera feed and object detection).'
            , 'parameters': {'type': 'object', 'properties': {}, 'required':
            []}}}]

    def get_functions(self):
        return {'start_live_vision': self.start_live_vision}

    def start_live_vision(self, **kwargs):
        try:
            root_dir = os.path.dirname(os.path.dirname(__file__))
            script_path = os.path.join(root_dir, 'video_system.py')
            if not os.path.exists(script_path):
                return (
                    f'Error: Vision system script not found at {script_path}')
            subprocess.Popen([sys.executable, script_path])
            return 'Live Vision System started. Check for the new window.'
        except Exception as e:
            return f'Error starting vision system: {str(e)}'
