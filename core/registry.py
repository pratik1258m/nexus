import os
import importlib.util
import inspect
from typing import Dict, List, Any, Callable
from .skill import Skill
from .logger import get_logger

logger=get_logger(__name__)

class SkillRegistry:

    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.skill_classes: Dict[str, tuple] = {}  # module_name -> (class_obj, context)
        self.tools_schema: List[Dict[str, Any]] = []
        self.functions: Dict[str, Callable] = {}
        self._loaded_modules = set()

    def load_skills(self, skills_dir: str, context: Dict[str, Any]=None):
        if not os.path.exists(skills_dir):
            logger.error(f'Skills directory not found: {skills_dir}')
            return
        
        logger.info(f"Loading skills from: {skills_dir}")
        for filename in os.listdir(skills_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name=filename[:-3]
                file_path=os.path.join(skills_dir, filename)
                self._load_skill_from_file(module_name, file_path, context)

    def _load_skill_from_file(self, module_name: str, file_path: str,
        context: Dict[str, Any]=None):
        spec=importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            try:
                module=importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, Skill
                        ) and obj is not Skill:
                        # Extract tools schema without instantiating
                        temp_instance = obj()
                        self.tools_schema.extend(temp_instance.get_tools())
                        
                        # Store class for lazy instantiation
                        self.skill_classes[temp_instance.name] = (obj, context)
                        
                        # Map functions to a lazy-loading wrapper
                        for func_name in temp_instance.get_functions().keys():
                            self.functions[func_name] = self._make_lazy_wrapper(temp_instance.name, func_name)
                        
                        logger.info(f'📦 Registered lazy skill: {temp_instance.name}')
            except Exception as e:
                logger.error(f'✗ Failed to register skill from {module_name}: {e}', exc_info=True)

    def _make_lazy_wrapper(self, skill_name: str, func_name: str) -> Callable:
        def wrapper(*args, **kwargs):
            if skill_name not in self.skills:
                logger.info(f"🚀 Lazy loading skill: {skill_name}")
                cls, context = self.skill_classes[skill_name]
                instance = cls()
                if context:
                    instance.initialize(context)
                self.skills[skill_name] = instance
            
            skill_instance = self.skills[skill_name]
            actual_func = skill_instance.get_functions()[func_name]
            return actual_func(*args, **kwargs)
        return wrapper

    def register_skill(self, skill: Skill):
        self.skills[skill.name] = skill
        self.tools_schema.extend(skill.get_tools())
        self.functions.update(skill.get_functions())

    def get_tools_schema(self) ->List[Dict[str, Any]]:
        return self.tools_schema

    def get_function(self, name: str) ->Callable:
        return self.functions.get(name)
