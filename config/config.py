import os, json
from abc import ABC, abstractmethod
from typing import TypeVar


T = TypeVar("T", any, object)


class ConfigItem(ABC):

    def __init__(self, name: str, default_value: T, description: str):
        self.name = name
        self.default_value = default_value
        self.description = description
        self.value = default_value

    @abstractmethod
    def __encode__(self, value: T, json_obj: dict) -> None:
        pass

    @abstractmethod
    def __decode__(self, json_obj: dict) -> T:
        pass

    def __getvalue__(self):
        return self.value

class BooleanConfigItem(ConfigItem):

    def __encode__(self, value: bool, json_obj: dict):
        json_obj['value'] = bool(value)

    def __decode__(self, json_obj: dict) -> bool:
        obj = json_obj.get('value', self.default_value)
        if isinstance(obj, bool):
            return obj
        elif isinstance(obj, str):
            return obj.lower() in ["true", "1"]
        elif isinstance(obj, int):
            return obj != 0
        return self.default_value


class StringConfigItem(ConfigItem):

    def __encode__(self, value: str, json_obj: dict):
        json_obj['value'] = value

    def __decode__(self, json_obj: dict) -> str:
        obj = json_obj.get('value', self.default_value)
        if isinstance(obj, str):
            return obj
        return str(obj)


class IntConfigItem(ConfigItem):

    def __encode__(self, value: int, json_obj: dict):
        json_obj['value'] = int(value)

    def __decode__(self, json_obj: dict) -> int:
        obj = json_obj.get('value', self.default_value)
        if isinstance(obj, int):
            return obj
        elif isinstance(obj, str):
            try:
                return int(obj)
            except:
                return self.default_value
        return self.default_value


class ListConfigItem(ConfigItem):

    def __encode__(self, value: list, json_obj: dict):
        json_obj['value'] = value

    def __decode__(self, json_obj: dict) -> list:
        obj = json_obj.get('value', self.default_value)
        if isinstance(obj, list):
            return obj
        return self.default_value


class DictConfigItem(ConfigItem):

    def __encode__(self, value: dict, json_obj: dict):
        json_obj['value'] = value

    def __decode__(self, json_obj: dict) -> dict:
        obj = json_obj.get('value', self.default_value)
        if isinstance(obj, dict):
            return obj
        return self.default_value


class TupleConfigItem(ConfigItem):

    def __encode__(self, value: tuple, json_obj: dict):
        json_obj['value'] = list(value)

    def __decode__(self, json_obj: dict) -> tuple:
        obj = json_obj.get('value', self.default_value)
        if isinstance(obj, list):
            return tuple(obj)
        return self.default_value


class Config:

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config_items: dict[str, ConfigItem] = {}

    def register_config_item(self, value: ConfigItem):
        self.config_items[value.name] = value

    def register_basic_config_item(self, name: str, type_: type, default_value: T, description: str):
        if type_ == bool:
            item = BooleanConfigItem(name, default_value, description)
        elif type_ == str:
            item = StringConfigItem(name, default_value, description)
        elif type_ == int:
            item = IntConfigItem(name, default_value, description)
        elif type_ == list:
            item = ListConfigItem(name, default_value, description)
        elif type_ == dict:
            item = DictConfigItem(name, default_value, description)
        elif type_ == tuple:
            item = TupleConfigItem(name, default_value, description)
        else:
            raise Exception(f"Unsupported config item type: {type_}")
        self.register_config_item(item)

    def load(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                json_obj = json.load(f)
                for name, item in self.config_items.items():
                    if json_obj.keys().__contains__(name):
                        item_obj = dict(json_obj[name])
                        item.value = item.__decode__(item_obj)
        else:
            self.save()

    def save(self):
        json_obj = {}
        for name, item in self.config_items.items():
            item_obj = {
                'description': item.description,
                'default_value': item.default_value
            }
            item.__encode__(item.value, item_obj)
            json_obj[name] = item_obj
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(json_obj, f, indent=4, ensure_ascii=False)

    def get_config_value(self, name: str) -> T:
        if self.config_items.keys().__contains__(name):
            return self.config_items[name].__getvalue__()
        raise Exception(f"Config item not found: {name}")