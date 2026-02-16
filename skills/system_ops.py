import os
import json
import time
import subprocess
from typing import List, Dict, Any, Callable
from core.skill import Skill
from core.platform_utils import get_os


class SystemSkill(Skill):

    @property
    def name(self) -> str:
        return 'system_skill'

    def get_tools(self) -> List[Dict[str, Any]]:
        return [{'type': 'function', 'function': {'name': 'set_volume',
            'description': 'Set system volume (0-100)', 'parameters': {
            'type': 'object', 'properties': {'level': {'type': 'integer'}},
            'required': ['level']}}}, {'type': 'function', 'function': {
            'name': 'open_app', 'description':
            'Open an application on the computer', 'parameters': {'type':
            'object', 'properties': {'app_name': {'type': 'string'}, 
            'path': {'type': 'string', 'description': 'Optional file or folder path to open'}},
            'required': ['app_name']}}}, {'type': 'function', 'function': {
            'name': 'close_app', 'description':
            'Close/quit an application on the computer', 'parameters': {'type':
            'object', 'properties': {'app_name': {'type': 'string'}},
            'required': ['app_name']}}}]

    def get_functions(self) -> Dict[str, Callable]:
        return {'set_volume': self.set_volume, 'open_app': self.open_app, 'close_app': self.close_app}

    def set_volume(self, level):
        """Set system volume (cross-platform)"""
        try:
            current_os=get_os()
            
            if current_os=='macos':
                os.system(f"osascript -e 'set volume output volume {level}'")
            elif current_os=='windows':
                try:
                    from ctypes import cast, POINTER
                    from comtypes import CLSCTX_ALL
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                    
                    devices=AudioUtilities.GetSpeakers()
                    interface=devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume=cast(interface, POINTER(IAudioEndpointVolume))
                    volume.SetMasterVolumeLevelScalar(level / 100, None)
                except Exception as e:
                    return json.dumps({'error': f'Windows volume control requires pycaw: {e}'})
            else:
                return json.dumps({'error': 'Volume control not supported on Linux'})
            
            return json.dumps({'status': 'success', 'level': level})
        except Exception as e:
            return json.dumps({'error': str(e)})

    def open_app(self, app_name, path=None):
        """Open and activate an application (cross-platform)"""
        try:
            current_os=get_os()
            
            app_mapping_common={
                'notepad': {'macos': 'TextEdit', 'windows': 'notepad', 'linux': 'gedit'},
                'calculator': {'macos': 'Calculator', 'windows': 'calc', 'linux': 'gnome-calculator'},
                'browser': {'macos': 'Safari', 'windows': 'msedge', 'linux': 'firefox'},
                'chrome': {'macos': 'Google Chrome', 'windows': 'chrome', 'linux': 'google-chrome'},
                'firefox': {'macos': 'Firefox', 'windows': 'firefox', 'linux': 'firefox'},
                'terminal': {'macos': 'Terminal', 'windows': 'cmd', 'linux': 'gnome-terminal'},
                'vscode': {'macos': 'Visual Studio Code', 'windows': 'code', 'linux': 'code'},
                'vs code': {'macos': 'Visual Studio Code', 'windows': 'code', 'linux': 'code'},
                'code': {'macos': 'Visual Studio Code', 'windows': 'code', 'linux': 'code'},
            }
            
            app_name_lower=app_name.lower()
            if app_name_lower in app_mapping_common:
                actual_app=app_mapping_common[app_name_lower][current_os]
            else:
                actual_app=app_name
            
            if current_os=='macos':
                return self._open_app_macos(actual_app, app_name, path)
            elif current_os=='windows':
                return self._open_app_windows(actual_app, app_name, path)
            else:
                return self._open_app_linux(actual_app, app_name, path)
                
        except Exception as e:
            return json.dumps({'status': 'error', 'message': str(e)})

    def close_app(self, app_name):
        """Close/quit an application (cross-platform)"""
        try:
            current_os = get_os()
            
            app_mapping_common = {
                'notepad': {'macos': 'TextEdit', 'windows': 'notepad', 'linux': 'gedit'},
                'calculator': {'macos': 'Calculator', 'windows': 'calc', 'linux': 'gnome-calculator'},
                'browser': {'macos': 'Safari', 'windows': 'msedge', 'linux': 'firefox'},
                'chrome': {'macos': 'Google Chrome', 'windows': 'chrome', 'linux': 'google-chrome'},
                'firefox': {'macos': 'Firefox', 'windows': 'firefox', 'linux': 'firefox'},
                'terminal': {'macos': 'Terminal', 'windows': 'cmd', 'linux': 'gnome-terminal'},
                'vscode': {'macos': 'Visual Studio Code', 'windows': 'code', 'linux': 'code'},
                'vs code': {'macos': 'Visual Studio Code', 'windows': 'code', 'linux': 'code'},
                'code': {'macos': 'Visual Studio Code', 'windows': 'code', 'linux': 'code'},
            }
            
            app_name_lower = app_name.lower()
            if app_name_lower in app_mapping_common:
                actual_app = app_mapping_common[app_name_lower][current_os]
            else:
                actual_app = app_name
            
            if current_os == 'macos':
                return self._close_app_macos(actual_app, app_name)
            elif current_os == 'windows':
                return self._close_app_windows(actual_app, app_name)
            else:
                return self._close_app_linux(actual_app, app_name)
                
        except Exception as e:
            return json.dumps({'status': 'error', 'message': str(e)})

    def _open_app_macos(self, actual_app, original_name, path=None):
        """Open app on macOS using AppleScript"""
        def find_app(name):
            try:
                result=subprocess.run(
                    ['mdfind', f'kMDItemKind == "Application"'],
                    capture_output=True, text=True, timeout=5
                )
                for app_path in result.stdout.strip().split('\n'):
                    if name.lower() in app_path.lower() and app_path.endswith('.app'):
                        return app_path
            except:
                pass
            return None
        
        app_path=find_app(actual_app)
        
        if not app_path:
            return json.dumps({
                'status': 'not_found',
                'app': actual_app
            })
        
        if path:
            # Handle user home directory expansion ~
            if path.startswith('~'):
                path = os.path.expanduser(path)
            # Or assume relative to Documents if not absolute
            elif not os.path.isabs(path):
                # Try finding it in Documents or Home
                possible_paths = [
                    os.path.join(os.path.expanduser('~/Documents'), path),
                    os.path.join(os.path.expanduser('~'), path),
                    path 
                ]
                for p in possible_paths:
                    if os.path.exists(p):
                        path = p
                        break
            
            # Using 'open -a "App" "Path"' is more reliable for opening files
            cmd = f'open -a "{app_path}" "{path}"'
            result = os.system(cmd)
        else:
            script=f'tell application "{actual_app}"\n    activate\nend tell'
            result=os.system(f"osascript -e '{script}'")
        
        if result==0:
            return json.dumps({
                'status': 'success', 
                'app': actual_app,
                'original_name': original_name,
                'path': app_path
            })
        else:
            return json.dumps({
                'status': 'error',
                'message': f'Failed to open {actual_app}'
            })

    def _open_app_windows(self, actual_app, original_name):
        """Open app on Windows using start command"""
        try:
            subprocess.Popen(['start', actual_app], shell=True)
            return json.dumps({
                'status': 'success',
                'app': actual_app,
                'original_name': original_name
            })
        except Exception as e:
            return json.dumps({
                'status': 'error',
                'message': f'Failed to open {actual_app}: {e}'
            })

    def _open_app_linux(self, actual_app, original_name):
        """Open app on Linux using xdg-open or direct command"""
        try:
            try:
                subprocess.Popen([actual_app])
            except FileNotFoundError:
                subprocess.Popen(['xdg-open', actual_app])
            
            return json.dumps({
                'status': 'success',
                'app': actual_app,
                'original_name': original_name
            })
        except Exception as e:
            return json.dumps({
                'status': 'error',
                'message': f'Failed to open {actual_app}: {e}'
            })

    def _close_app_macos(self, actual_app, original_name):
        """Close app on macOS using AppleScript quit command"""
        script = f'tell application "{actual_app}" to quit'
        result = os.system(f"osascript -e '{script}'")
        
        if result == 0:
            return json.dumps({
                'status': 'success', 
                'app': actual_app,
                'original_name': original_name
            })
        else:
            return json.dumps({
                'status': 'error',
                'message': f'Failed to close {actual_app}'
            })

    def _close_app_windows(self, actual_app, original_name):
        """Close app on Windows using taskkill"""
        try:
            subprocess.run(['taskkill', '/IM', f'{actual_app}.exe'], check=False)
            return json.dumps({
                'status': 'success',
                'app': actual_app,
                'original_name': original_name
            })
        except Exception as e:
            return json.dumps({
                'status': 'error',
                'message': f'Failed to close {actual_app}: {e}'
            })

    def _close_app_linux(self, actual_app, original_name):
        """Close app on Linux using pkill"""
        try:
            subprocess.run(['pkill', '-f', actual_app], check=False)
            return json.dumps({
                'status': 'success',
                'app': actual_app,
                'original_name': original_name
            })
        except Exception as e:
            return json.dumps({
                'status': 'error',
                'message': f'Failed to close {actual_app}: {e}'
            })
