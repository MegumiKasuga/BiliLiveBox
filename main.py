from config.i18n.locals import I18nManager
from config.config import Config

if __name__ == '__main__':

    cfg = Config(config_path="config.json")
    i18n = I18nManager(locals_dir="locals", default_lang="en_us")