import os
import json
from typing import List, Dict, Any, Callable
from core.skill import Skill


class TextSkill(Skill):

    def __init__(self):
        self.api_key = os.environ.get('GROQ_API_KEY')

    @property
    def name(self) ->str:
        return 'text_skill'

    def get_tools(self) ->List[Dict[str, Any]]:
        return [{'type': 'function', 'function': {'name': 'summarize_file',
            'description':
            'Read a text file and provide a summary of its contents',
            'parameters': {'type': 'object', 'properties': {'filepath': {
            'type': 'string', 'description':
            'Absolute path to the file to summarize'}}, 'required': [
            'filepath']}}}, {'type': 'function', 'function': {'name':
            'read_file_content', 'description':
            'Read and return the raw content of a text file', 'parameters':
            {'type': 'object', 'properties': {'filepath': {'type': 'string',
            'description': 'Absolute path to the file to read'}},
            'required': ['filepath']}}}]

    def get_functions(self) ->Dict[str, Callable]:
        return {'summarize_file': self.summarize_file, 'read_file_content':
            self.read_file_content}

    def read_file_content(self, filepath: str) ->str:
        try:
            filepath = os.path.expanduser(filepath)
            if not os.path.exists(filepath):
                desktop_path = os.path.join(os.path.expanduser('~'),
                    'Desktop', filepath)
                if os.path.exists(desktop_path):
                    filepath = desktop_path
            if not os.path.exists(filepath):
                return json.dumps({'status': 'error', 'message':
                    f'File not found: {filepath}'})
            if not os.path.isfile(filepath):
                return json.dumps({'status': 'error', 'message':
                    f'Path is not a file: {filepath}'})
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return json.dumps({'status': 'success', 'filepath': filepath,
                'content': content, 'length': len(content)})
        except UnicodeDecodeError:
            return json.dumps({'status': 'error', 'message':
                'File is not a valid text file (binary or encoding issue)'})
        except Exception as e:
            return json.dumps({'status': 'error', 'message':
                f'Error reading file: {str(e)}'})

    def summarize_file(self, filepath: str) ->str:
        read_result = json.loads(self.read_file_content(filepath))
        if read_result['status'] == 'error':
            return json.dumps(read_result)
        content = read_result['content']
        if len(content) < 100:
            return json.dumps({'status': 'success', 'summary': 
                'File is too short to summarize. Content: ' + content})
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)
            response = client.chat.completions.create(model=
                'llama-3.3-70b-versatile', messages=[{'role': 'system',
                'content':
                'You are a helpful assistant that summarizes text concisely. Provide a clear, brief summary in 2-3 sentences.'
                }, {'role': 'user', 'content':
                f"""Please summarize the following text:

{content[:4000]}"""
                }], max_tokens=150)
            summary = response.choices[0].message.content
            return json.dumps({'status': 'success', 'filepath': filepath,
                'summary': summary})
        except Exception as e:
            return json.dumps({'status': 'error', 'message':
                f'Error generating summary: {str(e)}'})
