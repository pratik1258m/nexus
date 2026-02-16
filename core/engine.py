import os
import json
from google import genai
from core.logger import get_logger
from core.config import get_config
from core.registry import SkillRegistry

logger=get_logger(__name__)

class NexusEngine:

    def __init__(self, registry: SkillRegistry):
        self.registry=registry
        config=get_config()
        
        self.gemini_key=config.api.gemini_api_key
        self.gemini_client=None
        self.gemini_model=config.api.gemini_model
        if self.gemini_key:
            self.gemini_client=genai.Client(api_key=self.gemini_key)
            logger.info(f"Gemini client initialized with model: {self.gemini_model}")
        else:
            logger.warning("Gemini API key not found - Gemini features unavailable")
        
        self.groq_key=config.api.groq_api_key
        self.groq_client=None
        self.groq_model=config.api.groq_model
        if self.groq_key:
            from groq import Groq
            self.groq_client=Groq(api_key=self.groq_key)
            logger.info(f"Groq client initialized with model: {self.groq_model}")
        else:
            logger.warning("Groq API key not found - Groq features unavailable")
        
        self.system_instruction=(
            'You are Nexus AI, a disciplined assistant created by Pratik Mishra. '
            'Execute tasks precisely with minimal response but MAXIMUM quality. '
            'Rules: '
            '1. RESPOND WITH SINGLE-WORD CONFIRMATIONS ONLY: "Done.", "Opened.", "Sent.", "Error." '
            '2. Do NOT explain what you are doing unless explicitly asked "why" or "how". '
            '3. Use ONLY provided tools - never simulate functions. '
            '4. Execute exactly what is asked, but ensure solutions are OPTIMAL and COMPLETED. '
            '   - For HTML, ALWAYS include modern CSS and interactive JS logic. '
            '   - For Python, ensure efficient, clean, and error-free code. '
            '   - IF context shows an app/editor is open (e.g. "notepad was recently opened"), use `type_code` to type directly. '
            '     ONLY use `generate_code_file` if the user explicitly asks to "save" or "create a file". '
            '5. CRITICAL: When sending messages, pass the COMPLETE message text - never truncate. '
            '6. For greetings: "Hello." For thanks: "Welcome." '
            'Be calm, synchronous, and human-like. Respond like a disciplined system, not a chatbot.'
        )

    def run_conversation(self, user_prompt: str) -> str:
        if self.gemini_client:
            try:
                logger.debug(f"Attempting Gemini API call for query: {user_prompt[:50]}...")
                return self._run_gemini_workflow(user_prompt)
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Resource has been exhausted" in error_str:
                    logger.warning("Gemini Free Tier rate limit reached.")
                    logger.info("🔄 Seamlessly switching to Groq (Llama 3) fallback...")
                    return self._run_groq_workflow(user_prompt)
                else:
                    logger.warning(f"Gemini API error: {e}")
                    logger.info('Gemini encountered an error. Falling back to Groq...')
        
        if self.groq_client:
            try:
                logger.debug(f"Using Groq API for query: {user_prompt[:50]}...")
                return self._run_groq_workflow(user_prompt)
            except Exception as e:
                logger.error(f'Groq API error: {e}', exc_info=True)
                return (
                    'I am currently experiencing connectivity issues with all my neural networks, sir.'
                    )
        
        logger.error("No valid API clients available")
        return (
            'I am offline, sir. No valid API keys found for my neural networks.'
            )

    def _run_gemini_workflow(self, user_prompt: str) ->str:
        tools_schema=self.registry.get_tools_schema()
        gemini_tools=[]
        if tools_schema:
            gemini_tools=[{'function_declarations': [t['function'] for t in
                tools_schema]}]
        response=self.gemini_client.models.generate_content(model=self.
            gemini_model, contents=user_prompt, config={
            'system_instruction': self.system_instruction, 'tools': 
            gemini_tools if gemini_tools else None})
        if response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    func_name=part.function_call.name
                    func_args=part.function_call.args
                    logger.info(f'Executing function: {func_name} with args: {func_args}')
                    function_to_call=self.registry.get_function(func_name)
                    if function_to_call:
                        res=function_to_call(**func_args)
                        response=self.gemini_client.models.generate_content(
                            model=self.gemini_model, contents=[{'role':
                            'user', 'content': user_prompt}, response.
                            candidates[0].content, {'role': 'function',
                            'parts': [{'function_response': {'name':
                            func_name, 'response': {'result': str(res)}}}]}
                            ], config={'system_instruction': self.
                            system_instruction})
                        return response.text
        return response.text

    def _run_groq_workflow(self, user_prompt: str) -> str:
        import re
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Nexus AI, an advanced and intelligent assistant. "
                    "Your outputs must be top-notch, professional, and precise. "
                    "When writing content (emails, letters, code), produce the FINAL polished version. "
                    "Do NOT use placeholders like '[Your Name]'—infer context or use generic but professional fillers. "
                    "If writing code, provide only the code in markdown blocks. "
                    "Be concise but thorough."
                )
            },
            {"role": "user", "content": user_prompt}
        ]
        tools_schema=self.registry.get_tools_schema()
        
        completion_kwargs={
            'model': self.groq_model, 
            'messages': messages,
            'max_tokens': 500,
            'temperature': 0.3
        }

        def recover_hallucinations(text):
            TOOL_MAPPING={
                'navigate_to_url': 'open_website',
                'search_google': 'google_search',
                'play_video': 'play_on_youtube',
                'search_youtube': 'play_on_youtube',
                'send_whatsapp': 'send_whatsapp_message',
                'send_message': 'send_whatsapp_message',
                'click_element': 'none'
            }
            results=[]
            matches=re.findall(r'<function=([\w.]+)>?(\{.*?\})</function>', text)
            if not matches:
                matches=re.findall(r'<function=([\w.]+)(\{.*?\})</function>', text)
            
            for func_name, func_args_str in matches:
                if '.' in func_name:
                    func_name=func_name.split('.')[-1]
                
                real_func_name=TOOL_MAPPING.get(func_name, func_name)
                if real_func_name == 'none':
                    results.append(f"Successfully simulated: {func_name}")
                    continue
                logger.debug(f'Recovering hallucinated tool call: {func_name} -> {real_func_name}')
                function_to_call=self.registry.get_function(real_func_name)
                if function_to_call:
                    try:
                        args=json.loads(func_args_str)
                        res=function_to_call(**args)
                        results.append(str(res))
                    except Exception as e:
                        logger.error(f"Hallucination execution error: {e}")
                        results.append(f"Execution Error: {e}")
            return " | ".join(results) if results else None

        try:
            if tools_schema:
                completion_kwargs['tools'] = tools_schema
                completion_kwargs['tool_choice'] = 'auto'
            response=self.groq_client.chat.completions.create(**
                completion_kwargs)
        except Exception as e:
            error_str=str(e)
            recovered=recover_hallucinations(error_str)
            if recovered:
                return recovered
            
            if 'tool_use_failed' in error_str.lower() or '400' in error_str:
                logger.warning('Groq tool calling failed. Retrying as text-only...')
                completion_kwargs.pop('tools', None)
                completion_kwargs.pop('tool_choice', None)
                
                # Instruct model to provide code cleanly if generic text
                messages.append({
                    'role': 'system', 
                    'content': 'Tool execution failed. Please write the requested code directly in a markdown block. '
                               'Include the filename in a comment at the top, e.g. "# filename: script.py".'
                })
                
                response=self.groq_client.chat.completions.create(**completion_kwargs)
            else:
                raise e

        response_message=response.choices[0].message
        content = response_message.content
        
        if content:
            recovered=recover_hallucinations(content)
            if recovered:
                return recovered
            
            # Check for code blocks if text-only fallback was used or tools failed
                # Intelligent Fallback: Check if context implies typing
                logger.info(f"DEBUG: Checking typing context. Prompt: {user_prompt[:100]}...")
                if "was recently opened" in user_prompt or "type" in user_prompt.lower():
                    logger.info("DEBUG: Context implies typing. Checking for code blocks.")
                    import re
                    # Extract first code block
                    match = re.search(r'```(?:\w+)?\n(.*?)```', content, re.DOTALL)
                    if match:
                        logger.info("DEBUG: Code block match found.")
                        code_content = match.group(1).strip()
                        type_tool = self.registry.get_function('type_code')
                        if type_tool:
                            logger.info("DEBUG: Calling type_code tool.")
                            type_tool(content=code_content)
                            return "Typed code into active window."
                        else:
                            logger.error("DEBUG: type_code tool missing.")
                    else:
                        logger.info("DEBUG: No code block match in content.")

                saved_file = self._extract_and_save_code(content)
                if saved_file:
                    return f"Created {saved_file}."

        if response_message.tool_calls:
            messages.append(response_message)
            tool_failed=False
            for tool_call in response_message.tool_calls:
                function_name=tool_call.function.name
                function_to_call=self.registry.get_function(function_name)
                if function_to_call:
                    try:
                        args=json.loads(tool_call.function.arguments) or {}
                        result=function_to_call(**args)
                        logger.info(f'Tool executed: {function_name} -> {str(result)[:100]}')
                        
                        if result and isinstance(result, str):
                            if result.startswith('❌') or 'Error' in result or 'Failed' in result:
                                messages.append({'role': 'tool', 'tool_call_id':
                                    tool_call.id, 'name': function_name, 'content':
                                    result})
                                tool_failed=True
                            else:
                                messages.append({'role': 'tool', 'tool_call_id':
                                    tool_call.id, 'name': function_name, 'content':
                                    result})
                        else:
                            messages.append({'role': 'tool', 'tool_call_id':
                                tool_call.id, 'name': function_name, 'content': str(
                                result)})
                    except Exception as e:
                        error_msg=f'Tool execution error: {str(e)[:200]}'
                        logger.error(error_msg)
                        messages.append({'role': 'tool', 'tool_call_id':
                            tool_call.id, 'name': function_name, 'content':
                            error_msg})
                        tool_failed=True
            
            if tool_failed:
                messages.append({'role': 'user', 'content': 'Tool failed. Respond with: "Error."'})

            second_response=self.groq_client.chat.completions.create(model=self.groq_model, messages=messages)
            return self._minimize_response(second_response.choices[0].message.content)
        return self._minimize_response(response_message.content)
    
    def _minimize_response(self, api_response: str) -> str:
        """
        Convert API response to minimal confirmation
        
        Args:
            api_response: Raw API response
            
        Returns:
            Minimized response (single word + period)
        """
        if not api_response:
            return "Done."
        
        response_lower = api_response.lower()
        
        if any(word in response_lower for word in ['error', 'failed', 'cannot', 'unable', '❌']):
            return "Error."
        
        if 'typed' in response_lower:
            return "Typed."
        elif 'created' in response_lower:
            return "Created."
        elif 'open' in response_lower:
            return "Opened."
        elif 'close' in response_lower or 'quit' in response_lower:
            return "Closed."
        elif 'send' in response_lower or 'sent' in response_lower or 'message' in response_lower:
            return "Sent."
        elif 'search' in response_lower:
            return "Searched."
        elif 'play' in response_lower:
            return "Playing."
        elif 'volume' in response_lower or 'set' in response_lower:
            return "Set."
        elif any(word in response_lower for word in ['hello', 'hi', 'hey']):
            return "Hello."
        elif any(word in response_lower for word in ['thank', 'welcome']):
            return "Welcome."
        elif 'created' in response_lower:
            return "Created."
        
        return "Done."
    
    def execute_local(self, intent) -> str:
        """
        Execute command locally without API call
        
        Args:
            intent: CommandIntent from interpreter
            
        Returns:
            Minimal response string
        """
        from core.command_interpreter import CommandInterpreter
        
        simple_response = CommandInterpreter.get_response_for_simple_action(None, intent.action)
        if simple_response:
            return simple_response
        
        function = self.registry.get_function(intent.action)
        if not function:
            logger.error(f"Function not found: {intent.action}")
            return "Error."
        
        try:
            result = function(**intent.params)
            logger.info(f"Local execution: {intent.action} -> {str(result)[:100]}")
            return self._minimize_response(str(result))
        except Exception as e:
            logger.error(f"Local execution error: {e}")
            return "Error."

    def _extract_and_save_code(self, text: str) -> str:
        """
        Extract code generated in text-only mode and save to file
        
        Args:
            text: Response text containing markdown code blocks
            
        Returns:
            Filename if saved, None otherwise
        """
        import re
        
        # Regex to find code blocks: ```language\ncode```
        # Captures: 1=language (optional), 2=code
        matches = re.findall(r'```(\w*)\n(.*?)```', text, re.DOTALL)
        
        if not matches:
            return None
            
        saved_files = []
        
        for lang, code in matches:
            lines = code.strip().split('\n')
            
            # Try to find filename in first few lines
            filename = None
            for line in lines[:3]:
                # Check for comment pattern # filename: ... or // filename: ...
                file_match = re.search(r'(?:#|//|<!--)\s*filename:\s*([\w\-\.]+)', line, re.IGNORECASE)
                if file_match:
                    filename = file_match.group(1).strip()
                    break
            
            if not filename:
                # Generate fallback filename
                import time
                ext = 'txt'
                if 'python' in lang or 'py' in lang: ext = 'py'
                elif 'html' in lang: ext = 'html'
                elif 'javascript' in lang or 'js' in lang: ext = 'js'
                elif 'css' in lang: ext = 'css'
                elif 'java' in lang: ext = 'java'
                elif 'cpp' in lang: ext = 'cpp'
                
                filename = f"generated_{int(time.time())}.{ext}"
            
            try:
                # Save to Documents/nexus
                save_path = os.path.join(os.path.expanduser('~/Documents/nexus'), filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                with open(save_path, 'w') as f:
                    f.write(code.strip())
                    
                logger.info(f"Saved generated code to {save_path}")
                saved_files.append(filename)
            except Exception as e:
                logger.error(f"Failed to save generated code: {e}")
                
        return ", ".join(saved_files) if saved_files else None
