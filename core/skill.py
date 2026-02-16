from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable


class Skill(ABC):

    @abstractmethod
    def get_tools(self) ->List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_functions(self) ->Dict[str, Callable]:
        pass

    def initialize(self, context: Dict[str, Any]):
        pass

    @property
    @abstractmethod
    def name(self) ->str:
        pass
