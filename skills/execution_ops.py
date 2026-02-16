import subprocess
import json
import os
from typing import List, Dict, Any, Callable
from core.skill import Skill


class ExecutionSkill(Skill):

    @property
    def name(self) ->str:
        return 'execution_skill'

    def get_tools(self) ->List[Dict[str, Any]]:
        return [{'type': 'function', 'function': {'name': 'run_command',
            'description':
            'Execute a shell command and return the output or error.',
            'parameters': {'type': 'object', 'properties': {'command': {
            'type': 'string', 'description': 'The shell command to execute'
            }}, 'required': ['command']}}}, {'type': 'function', 'function':
            {'name': 'debug_python_script', 'description':
            'Run a python script and return the output. Useful for testing and debugging.'
            , 'parameters': {'type': 'object', 'properties': {'script_path':
            {'type': 'string', 'description':
            'Absolute path to the python script'}}, 'required': [
            'script_path']}}}]

    def get_functions(self) ->Dict[str, Callable]:
        return {'run_command': self.run_command, 'debug_python_script':
            self.debug_python_script}

    def run_command(self, command: str) ->str:
        try:
            result = subprocess.run(command, shell=True, capture_output=
                True, text=True, timeout=30)
            return json.dumps({'status': 'success' if result.returncode == 
                0 else 'error', 'stdout': result.stdout, 'stderr': result.
                stderr, 'returncode': result.returncode})
        except Exception as e:
            return json.dumps({'status': 'error', 'message': str(e)})

    def debug_python_script(self, script_path: str) ->str:
        if not os.path.exists(script_path):
            return json.dumps({'status': 'error', 'message':
                'Script not found.'})
        return self.run_command(f'python3 {script_path}')
