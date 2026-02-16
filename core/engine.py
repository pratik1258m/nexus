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
            'Execute tasks precisely with minimal response. '
            'Rules: '
            '1. RESPOND WITH SINGLE-WORD CONFIRMATIONS ONLY: "Done.", "Opened.", "Sent.", "Error." '
            '2. Do NOT explain what you are doing unless explicitly asked "why" or "how". '
            '3. Use ONLY provided tools - never simulate functions. '
            '4. Execute exactly what is asked - do not add extra steps. '
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
                error_msg=str(e).lower()
                logger.warning(f"Gemini API error: {e}")
                if ('quota' in error_msg or 'resource_exhausted' in
                    error_msg or '429' in error_msg):
                    logger.info('Gemini quota exceeded. Falling back to Groq...')
                else:
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
        messages=[{'role': 'system', 'content': self.system_instruction},
            {'role': 'user', 'content': user_prompt}]
        tools_schema=self.registry.get_tools_schema()
        
        # Limit tokens to reduce hallucinations and costs
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
                response=self.groq_client.chat.completions.create(**
                    completion_kwargs)
            else:
                raise e

        response_message=response.choices[0].message
        
        # Check for hallucinated tags in the content even if tool_calls is empty
        if response_message.content:
            recovered=recover_hallucinations(response_message.content)
            if recovered:
                return recovered

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
        
        # Error cases
        if any(word in response_lower for word in ['error', 'failed', 'cannot', 'unable', '❌']):
            return "Error."
        
        # Success patterns
        if 'open' in response_lower:
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
        
        # Default success
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
        
        # Check for simple responses (no execution needed)
        simple_response = CommandInterpreter.get_response_for_simple_action(None, intent.action)
        if simple_response:
            return simple_response
        
        # Execute function
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
