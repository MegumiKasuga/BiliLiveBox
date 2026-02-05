import locale
import os, json

class LocaleI18nFile:

    def __init__(self, langs: str, path: str):
        self.path = path
        self.langs = langs
        with open(os.path.join(self.path, f"{self.langs}.json"), "r", encoding="utf-8") as f:
            translations = json.load(f)

        self.translation_key_pairs = {}
        for key, value in translations.items():
            self.translation_key_pairs[key.lower()] = value

    def __contains__(self, key: str) -> bool:
        return key.lower() in self.translation_key_pairs

    def __getitem__(self, key: str) -> str:
        return self.translation_key_pairs.get(key.lower(), key)

    def __get_or_default__(self, key: str, default: str) -> str:
        return self.translation_key_pairs.get(key.lower(), default)


class I18nManager:

    def __init__(self, locals_dir: str, default_lang: str = "en_us"):
        self.lang = locale.getdefaultlocale()[0].lower()
        if not self.lang:
            self.lang = default_lang
        self.default_lang = default_lang
        self.locals_dir = locals_dir
        self.locales = {}

        for root, dirs, files in os.walk(self.locals_dir):
            for file in files:
                if file.endswith(".json"):
                    langs = file[:-5]
                    self.locales[langs] = LocaleI18nFile(langs, self.locals_dir)

    def translate(self, key: str) -> str:
        locale_file = self.locales.get(self.lang, self.locales.get(self.default_lang))
        if locale_file and key in locale_file:
            return locale_file[key]
        return key