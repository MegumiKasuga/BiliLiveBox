import os, json
from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar("T", any, object)

class ConfigItem(ABC):

    def __init__(self, name: str, default_value: T, description: str):
        self.name = name
        self.default_value = default_value
        self.description = description

    @abstractmethod
    def __encode__(self, value: T, json_obj: dict) -> None:
        pass

    @abstractmethod
    def __decode__(self, json_obj: dict) -> T:
        pass

class BooleanConfigItem(ConfigItem):

    def __encode__(self, value: bool, json_obj: dict):
        json_obj[self.name] = bool(value)

    def __decode__(self, json_obj: dict) -> bool:
        if json_obj.keys().__contains__(self.name):
            obj = json_obj[self.name]
            if isinstance(obj, bool):
                return obj
            elif isinstance(obj, str):
                return obj.lower() in ["true", "1"]
            elif isinstance(obj, int):
                return obj != 0
        return self.default_value

class StringConfigItem(ConfigItem):

    def __encode__(self, value: str, json_obj: dict):
        json_obj[self.name] = value

    def __decode__(self, json_obj: dict) -> str:
        if json_obj.keys().__contains__(self.name):
            obj = json_obj[self.name]
            if isinstance(obj, str):
                return obj
            return str(obj)
        return self.default_value