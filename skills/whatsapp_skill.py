from core.skill import Skill
from core.logger import get_logger
import json
import os
from skills.whatsapp.whatsapp_client import WhatsAppClient

logger=get_logger(__name__)

class WhatsappSkill(Skill):

    def __init__(self):
        self.contacts=self._load_contacts()
        self.client=None

    @property
    def name(self):
        return 'whatsapp_skill'

    def _load_contacts(self):
        contacts_path=os.path.join(os.path.dirname(os.path.dirname(
            __file__)), 'contacts.json')
        try:
            with open(contacts_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f'Error loading contacts: {e}')
            return {}

    def _get_client(self):
        if not self.client:
            self.client=WhatsAppClient()
        return self.client

    def get_tools(self):
        return [{'type': 'function', 'function': {'name':
            'send_whatsapp_message', 'description':
            'Send a WhatsApp message to a specific person. Use Chrome browser by default, or Safari if user specifically requests it.',
            'parameters': {'type': 'object', 'properties': {'name': {'type':
            'string', 'description':
            "The name of the contact (e.g., 'Dad', 'Mom')."}, 'message': {
            'type': 'string', 'description': 'The message to send.'}, 'browser': {
            'type': 'string', 'description': 'Browser to use for Web mode: "chrome" (default) or "safari".', 
            'enum': ['chrome', 'safari'], 'default': 'chrome'}, 'mode': {
            'type': 'string', 'description': 'Mode: "web" (browser - most reliable), "auto" (tries native first), "native" (app only).',
            'enum': ['web', 'auto', 'native'], 'default': 'web'}},
            'required': ['name', 'message']}}}]

    def get_functions(self):
        return {'send_whatsapp_message': self.send_whatsapp_message}

    def send_whatsapp_message(self, name, message, browser='chrome', mode='web'):
        """
        Send WhatsApp message to a contact
        
        Args:
            name: Contact name (from contacts.json) or phone number with country code
            message: Message text to send
            browser: Browser to use for web mode
            mode: Sending mode ('auto', 'native', 'web')
        """
        clean_name=name.lower().strip()
        
        try:
            self._get_client()
            
            contact_name_lower=name.lower()
            
            if contact_name_lower in self.contacts:
                search_term=self.contacts[contact_name_lower] # Use the actual value from contacts.json
                logger.info(f"Found '{name}' in contacts: {search_term}")
            else:
                search_term=name
                logger.info(f"Using provided name/number: {search_term}")
            
            logger.info(f"Sending message to: {search_term} (Mode: {mode})")
            result=self.client.send_message(search_term, message, browser=browser, mode=mode)
            return result
        except Exception as e:
            error_msg=f'Error sending WhatsApp message: {e}'
            logger.error(error_msg)
            return error_msg
