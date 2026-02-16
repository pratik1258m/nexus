"""
WhatsApp Native Automation - URL Scheme Approach
Most reliable method using whatsapp:// protocol
"""
import subprocess
import time
import urllib.parse
from core.logger import get_logger

logger = get_logger(__name__)

def run_applescript(script: str):
    """Run an AppleScript and return the output."""
    try:
        process = subprocess.Popen(['osascript', '-e', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(timeout=15)
        if process.returncode != 0:
            logger.error(f"AppleScript error: {stderr}")
            return False, stderr
        return True, stdout.strip()
    except Exception as e:
        logger.error(f"Failed to run AppleScript: {e}")
        return False, str(e)

def open_whatsapp_native():
    """Open or focus the WhatsApp Desktop app."""
    script = 'tell application "WhatsApp" to activate'
    success, error = run_applescript(script)
    if success:
        time.sleep(2.0)
    else:
        logger.error(f"Failed to open WhatsApp: {error}")
    return success

def send_message_simple(contact_name: str, message: str):
    """
    Send message using whatsapp:// URL scheme.
    This is the most reliable method.
    """
    encoded_contact = urllib.parse.quote(contact_name)
    
    url = f"whatsapp://send?text={encoded_contact}"
    
    try:
        subprocess.run(['open', url], check=True)
        time.sleep(3.0)
        
        escaped_message = message.replace('"', '\\"').replace('\\', '\\\\')
        
        script = f'''
        set the clipboard to "{escaped_message}"
        
        tell application "System Events"
            tell process "WhatsApp"
                set frontmost to true
                delay 1.0
                
                -- Clear the pre-filled text and paste our message
                keystroke "a" using {{command down}}
                delay 0.3
                keystroke "v" using {{command down}}
                delay 1.0
                
                -- Send with Enter
                key code 36
                delay 0.5
            end tell
        end tell
        '''
        
        success, error = run_applescript(script)
        if not success:
            if "not allowed" in error.lower() or "permissions" in error.lower():
                return False, "❌ Accessibility permissions required. Go to System Settings → Privacy & Security → Accessibility and enable Terminal/Python."
            return False, f"❌ Failed to send: {error}"
        
        return True, "✅ Message sent successfully"
        
    except Exception as e:
        logger.error(f"URL scheme failed: {e}")
        return False, f"❌ Failed to open WhatsApp: {e}"
