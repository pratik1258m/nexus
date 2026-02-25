"""
Cross-platform voice system for Nexus AI
Supports macOS (native), Windows (pyttsx3/SAPI5), and Linux (pyttsx3/espeak)
"""

import os
import sys
import subprocess
import platform
import shlex
import threading
import time
from typing import Optional, List
import logging

try:
    from core.logger import get_logger
    from core.config import get_config
    logger = get_logger(__name__)
except (ImportError, ModuleNotFoundError):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | VOICE | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    logger.warning("Using fallback logger - core.logger not available")

def get_os() -> str:
    """Reliable cross-platform OS detection"""
    system = platform.system().lower()
    if system == 'darwin':
        return 'macos'
    elif system == 'windows':
        return 'windows'
    elif system == 'linux':
        return 'linux'
    else:
        return 'unknown'

_tts_engine = None
_tts_lock = threading.Lock()
_current_voice = 'Daniel'
_is_initialized = False
_speech_active = threading.Event()

MACOS_VOICES = ['Daniel', 'Samantha', 'Karen', 'Moira', 'Tessa', 'Veena']
WINDOWS_VOICES = ['David', 'Zira', 'Hazel']
LINUX_VOICES = ['english-us', 'english-mb-en1', 'english-wm']

def _sanitize_text(text: str) -> str:
    """Safely sanitize text for TTS engines while preserving meaning"""
    if not text or not isinstance(text, str):
        return ""
    
    if '{' in text and '}' in text:
        import re
        text = re.sub(r'\{status:[^}]*\}', '', text).strip()
        if not text:
            text = "Task completed"
    
    if get_os() == 'macos':
        return text.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')
    return text.strip()

def _chunk_text(text: str, max_length: int = 500) -> List[str]:
    """Split long texts into safe chunks for TTS engines"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    sentences = text.replace('!', '. ').replace('?', '. ').split('. ')
    
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence = sentence.strip() + '. '
        if not sentence.strip():
            continue
            
        if current_length + len(sentence) > max_length and current_chunk:
            chunks.append(' '.join(current_chunk).strip())
            current_chunk = [sentence]
            current_length = len(sentence)
        else:
            current_chunk.append(sentence)
            current_length += len(sentence)
    
    if current_chunk:
        chunks.append(' '.join(current_chunk).strip())
    
    return chunks or [text[:max_length]]

def _init_macos_tts() -> bool:
    """Initialize macOS TTS with voice validation"""
    global _current_voice
    
    try:
        subprocess.run(['which', 'say'], capture_output=True, check=True)
        
        result = subprocess.run(
            ['say', '-v', '?'], 
            capture_output=True, 
            text=True, 
            timeout=3
        )
        
        available_voices = [line.split()[0] for line in result.stdout.strip().split('\n') if line.strip()]
        
        if _current_voice not in available_voices:
            for voice in MACOS_VOICES:
                if voice in available_voices:
                    _current_voice = voice
                    logger.info(f"Voice '{_current_voice}' not found, using fallback: {voice}")
                    break
            else:
                _current_voice = available_voices[0] if available_voices else 'Daniel'
                logger.warning(f"No preferred voices found, using system default: {_current_voice}")
        
        logger.info(f"macOS TTS ready with voice: {_current_voice}")
        return True
        
    except Exception as e:
        logger.error(f"macOS TTS initialization failed: {type(e).__name__}: {e}")
        return False

def _init_pyttsx3() -> Optional:
    """Safely initialize pyttsx3 with platform-specific drivers"""
    global _tts_engine
    
    try:
        import pyttsx3
        
        current_os = get_os()
        driver = None
        if current_os == 'windows':
            driver = 'sapi5'
        elif current_os == 'linux':
            driver = 'espeak'
        elif current_os == 'macos':
            driver = 'nsss'
        
        engine = pyttsx3.init(driverName=driver) if driver else pyttsx3.init()
        
        engine.setProperty('rate', 190)
        engine.setProperty('volume', 0.9)
        
        voices = engine.getProperty('voices')
        target_voice = _current_voice.lower()
        
        if voices:
            selected_voice = None
            for voice in voices:
                if target_voice in voice.name.lower():
                    selected_voice = voice
                    break
            
            if not selected_voice:
                platform_voices = WINDOWS_VOICES if current_os == 'windows' else \
                                 LINUX_VOICES if current_os == 'linux' else MACOS_VOICES
                
                for voice in voices:
                    if any(pv.lower() in voice.name.lower() for pv in platform_voices):
                        selected_voice = voice
                        break
            
            if selected_voice:
                engine.setProperty('voice', selected_voice.id)
                logger.info(f"Using voice: {selected_voice.name}")
            else:
                logger.warning("No preferred voice found, using default engine voice")
        
        engine.say("ready")
        engine.runAndWait()
        
        logger.info(f"pyttsx3 initialized successfully ({current_os})")
        return engine
        
    except ImportError:
        logger.error("pyttsx3 not installed. Install with: pip install pyttsx3")
        return None
    except Exception as e:
        logger.error(f"pyttsx3 initialization failed: {type(e).__name__}: {e}")
        return None

def _init_tts_engine() -> str:
    """Thread-safe TTS engine initialization with fallbacks"""
    global _tts_engine, _is_initialized
    
    with _tts_lock:
        if _is_initialized:
            return 'ready'
        
        current_os = get_os()
        logger.info(f"Initializing TTS for {current_os}")
        
        if current_os == 'macos':
            if _init_macos_tts():
                _tts_engine = 'native'
                _is_initialized = True
                return 'ready'
        
        engine = _init_pyttsx3()
        if engine:
            _tts_engine = engine
            _is_initialized = True
            return 'ready'
        
        logger.critical("All TTS initialization attempts failed. Voice output disabled.")
        _tts_engine = 'disabled'
        _is_initialized = True
        return 'disabled'

def speak(text: str, interrupt: bool = True) -> bool:
    """
    Speak text using platform-appropriate TTS with safety features
    
    Args:
        text: Text to speak (will be sanitized)
        interrupt: Whether to interrupt current speech
    
    Returns:
        True if speech was initiated successfully
    """
    if not text or not isinstance(text, str):
        logger.debug("Empty or invalid text provided for speech")
        return False
    
    if interrupt and _speech_active.is_set():
        logger.debug("Interrupting current speech")
        if hasattr(_tts_engine, 'stop'):
            try:
                _tts_engine.stop()
            except:
                pass
    
    _speech_active.set()
    
    try:
        if not _is_initialized:
            status = _init_tts_engine()
            if status == 'disabled':
                logger.warning(f"TTS disabled. Would say: {text[:50]}...")
                _speech_active.clear()
                return False
        
        clean_text = _sanitize_text(text)
        if not clean_text:
            logger.debug("Text became empty after sanitization")
            _speech_active.clear()
            return False
        
        logger.info(f"Speaking: {clean_text[:60]}..." if len(clean_text) > 60 else f"Speaking: {clean_text}")
        
        current_os = get_os()
        
        if _tts_engine == 'native' and current_os == 'macos':
            chunks = _chunk_text(clean_text, max_length=450)
            
            for i, chunk in enumerate(chunks):
                if i > 0:
                    time.sleep(0.3)
                
                cmd = ['say', '-v', _current_voice, '-r', '190', chunk]
                try:
                    subprocess.run(cmd, timeout=15, capture_output=True, check=False)
                except subprocess.TimeoutExpired:
                    logger.warning("Speech timed out (macOS)")
                    break
                except Exception as e:
                    logger.error(f"macOS speech error: {e}")
                    break
            
        elif _tts_engine and _tts_engine != 'disabled' and _tts_engine != 'native':
            chunks = _chunk_text(clean_text, max_length=300)
            
            for i, chunk in enumerate(chunks):
                if i > 0:
                    time.sleep(0.4)
                
                try:
                    _tts_engine.say(chunk)
                    _tts_engine.runAndWait()
                except Exception as e:
                    logger.error(f"pyttsx3 speech error: {e}")
                    break
        else:
            logger.debug(f"TTS disabled, skipping speech: {clean_text[:50]}...")
            return False
            
        return True
        
    except Exception as e:
        logger.exception(f"Unexpected error during speech: {e}")
        return False
    finally:
        _speech_active.clear()

def listen(timeout: int = 5, phrase_time_limit: int = 10) -> str:
    """
    Listen for voice input with robust error handling
    
    Args:
        timeout: Seconds to wait for speech to start
        phrase_time_limit: Maximum seconds of speech to capture
    
    Returns:
        Recognized text in lowercase, or 'none' if no speech detected
    """
    try:
        import speech_recognition as sr
    except ImportError:
        logger.error("speech_recognition not installed. Install with: pip install SpeechRecognition pyaudio")
        return 'none'
    
    try:
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.5
        
        mic = None
        for attempt in range(3):
            try:
                mic = sr.Microphone()
                break
            except OSError as e:
                if attempt < 2:
                    logger.warning(f"Microphone init failed (attempt {attempt+1}/3): {e}")
                    time.sleep(0.5)
                else:
                    logger.error(f"Microphone initialization failed after 3 attempts: {e}")
                    _show_microphone_help()
                    return 'none'
            except Exception as e:
                logger.error(f"Unexpected microphone error: {e}")
                _show_microphone_help()
                return 'none'
        
        if not mic:
            return 'none'
        
        try:
            with mic as source:
                logger.debug("Adjusting for ambient noise...")
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                logger.info(f"Listening... (timeout: {timeout}s, max duration: {phrase_time_limit}s)")
                
                try:
                    audio = recognizer.listen(
                        source, 
                        timeout=timeout, 
                        phrase_time_limit=phrase_time_limit
                    )
                    logger.debug("Audio captured, recognizing with Google Web Speech API...")
                    
                    last_error = None
                    try:
                        languages = get_config().voice.listen_languages
                    except (NameError, AttributeError, ImportError):
                        languages = ['en-US']
                    
                    for lang in languages:
                        try:
                            logger.debug(f"Policies: attempting recognition in '{lang}'")
                            text = recognizer.recognize_google(audio, language=lang)
                            logger.info(f'Recognized speech ({lang}): "{text}"')
                            return text.lower().strip()
                        except sr.UnknownValueError:
                            continue
                        except sr.RequestError as e:
                            last_error = e
                            break
                    
                    if last_error:
                        raise last_error
                    raise sr.UnknownValueError()
                    
                except sr.WaitTimeoutError:
                    logger.debug("No speech detected within timeout period")
                    return 'none'
                except sr.UnknownValueError:
                    logger.debug("Speech recognition could not understand audio in any configured language")
                    speak("Sir, can you repeat it please?", interrupt=False)
                    return 'none'
                except sr.RequestError as e:
                    logger.error(f"Speech recognition service error: {e}")
                    return 'none'
                    
        except Exception as e:
            logger.exception(f"Microphone session error: {e}")
            return 'none'
            
    except Exception as e:
        logger.exception(f"Unexpected error in listen(): {e}")
        return 'none'

def _show_microphone_help():
    """Display platform-specific microphone permission guidance"""
    current_os = get_os()
    logger.error("\n" + "="*60)
    logger.error("MICROPHONE ACCESS REQUIRED")
    logger.error("="*60)
    
    if current_os == 'macos':
        logger.error("macOS: Go to System Settings → Privacy & Security → Microphone")
        logger.error("       Ensure your terminal/app has microphone access enabled")
    elif current_os == 'windows':
        logger.error("Windows: Settings → Privacy → Microphone → Allow apps to access microphone")
    elif current_os == 'linux':
        logger.error("Linux: Ensure PulseAudio/ALSA is running and mic permissions are set")
        logger.error("       May need: sudo usermod -a -G audio $USER")
    
    logger.error("="*60 + "\n")

def set_voice(voice_name: str) -> bool:
    """
    Set TTS voice with platform-aware validation
    
    Args:
        voice_name: Preferred voice name
    
    Returns:
        True if voice was set successfully
    """
    global _current_voice
    
    if not voice_name or not isinstance(voice_name, str):
        logger.warning("Invalid voice name provided")
        return False
    
    _current_voice = voice_name.strip()
    logger.info(f"Requested voice change to: {_current_voice}")
    
    global _is_initialized, _tts_engine
    with _tts_lock:
        _is_initialized = False
        _tts_engine = None
    
    status = _init_tts_engine()
    return status == 'ready'

def get_available_voices() -> List[str]:
    """Get list of available voices for current platform"""
    current_os = get_os()
    
    if current_os == 'macos':
        try:
            result = subprocess.run(
                ['say', '-v', '?'], 
                capture_output=True, 
                text=True, 
                timeout=3
            )
            voices = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    voice_name = line.split()[0]
                    voices.append(voice_name)
            return voices[:20]
        except Exception as e:
            logger.error(f"Error listing macOS voices: {e}")
            return MACOS_VOICES
    
    elif _tts_engine and _tts_engine not in ('disabled', 'native', None):
        try:
            voices = _tts_engine.getProperty('voices')
            return [voice.name for voice in voices[:15]]
        except Exception as e:
            logger.error(f"Error listing pyttsx3 voices: {e}")
            return WINDOWS_VOICES if current_os == 'windows' else LINUX_VOICES
    
    return {
        'macos': MACOS_VOICES,
        'windows': WINDOWS_VOICES,
        'linux': LINUX_VOICES
    }.get(current_os, ['Default'])

def is_speaking() -> bool:
    """Check if TTS is currently active"""
    return _speech_active.is_set()

def cleanup():
    """Clean up TTS resources"""
    global _tts_engine, _is_initialized
    
    if _tts_engine and _tts_engine not in ('disabled', 'native', None):
        try:
            if hasattr(_tts_engine, 'stop'):
                _tts_engine.stop()
            if hasattr(_tts_engine, 'endLoop'):
                _tts_engine.endLoop()
            if hasattr(_tts_engine, 'runAndWait'):
                _tts_engine.runAndWait()
        except:
            pass
    
    _tts_engine = None
    _is_initialized = False
    logger.info("TTS resources cleaned up")

import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    print("\n" + "="*70)
    print("NEXUS AI VOICE SYSTEM - DIAGNOSTIC TEST")
    print("="*70)
    
    current_os = get_os()
    print(f"\nPlatform: {platform.system()} {platform.release()} ({current_os})")
    print(f"Python: {sys.version.split()[0]}")
    
    print("\n[1/4] Initializing TTS engine...")
    status = _init_tts_engine()
    print(f"Status: {'✓ READY' if status == 'ready' else '✗ DISABLED'}")
    
    print("\n[2/4] Available voices:")
    voices = get_available_voices()
    for i, voice in enumerate(voices[:8], 1):
        indicator = " →" if voice == _current_voice else "  "
        print(f"  {indicator} {i}. {voice}")
    if len(voices) > 8:
        print(f"  ... and {len(voices) - 8} more")
    
    print("\n[3/4] Testing speech output...")
    test_text = "Voice system operational. All systems nominal."
    success = speak(test_text, interrupt=True)
    print(f"Result: {'✓ SUCCESS' if success else '✗ FAILED'}")
    
    print("\n[4/4] Microphone test (optional):")
    print("  Say something within 5 seconds...")
    result = listen(timeout=5, phrase_time_limit=8)
    
    if result and result != 'none':
        print(f"  Recognized: '{result}'")
    else:
        print("  No speech detected or recognition failed")
    
    print("\n" + "="*70)
    print("DIAGNOSTIC COMPLETE")
    print("="*70)
    
    if status == 'ready' and success:
        print("\n✓ Voice system is fully operational")
    else:
        print("\n⚠ Voice system has limitations:")
        if status != 'ready':
            print("  - TTS engine failed to initialize")
        if not success:
            print("  - Speech output failed")
        print("\nTroubleshooting:")
        if current_os == 'macos':
            print("  • Ensure 'say' command works in Terminal")
            print("  • Check System Settings → Privacy → Microphone permissions")
        else:
            print("  • Install required packages: pip install pyttsx3 pyaudio SpeechRecognition")
            print("  • Linux: May need espeak and portaudio: sudo apt install espeak portaudio19-dev")
    
    print("="*70 + "\n")
