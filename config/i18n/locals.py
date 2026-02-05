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

    def translate(self, key: str, **kwargs) -> str:
        """
        从本地化文件钟读取键对应的字符串的翻译，如果找不到对应语言的翻译，会去找默认语言的翻译，若仍然找不到，则返回传入的键名
        :param key:      传入的本地化键名
        :param kwargs:   用于格式化字符串的关键字参数(可以在翻译字符串中使用形如 {abc} 的形式引用)
        :return:         翻译后的字符串
        """
        locale_file = self.locales.get(self.lang, self.locales.get(self.default_lang))
        result = key
        if locale_file and key in locale_file:
            result = locale_file[key]
        result = result.format(**kwargs)
        return result