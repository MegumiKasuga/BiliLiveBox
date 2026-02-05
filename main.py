import os.path

from config.i18n.locals import I18nManager
from config.config import Config
from bili import login

session_saving_path = 'usr/session.json'

if __name__ == '__main__':

    cfg = Config(config_path="config.json")

    cfg.register_basic_config_item("ForceLogin", bool, False, "Whether to force login via QR code, ignoring saved session")
    cfg.load()
    i18n = I18nManager(locals_dir="lang", default_lang="en_us")

    session = None
    need_to_login = True

    if (not bool(cfg.get_config_value('ForceLogin')) and
            os.path.exists(session_saving_path)):
        session = login.login_by_session_file(session_saving_path)
        need_to_refresh = session.cookie_need_to_refresh()
        if need_to_refresh['logged_in']:
            if need_to_refresh['need_to_refresh']:
                if session.refresh_cookies(need_to_refresh['timestamp']):
                    session.save_session(session_saving_path)
                    need_to_login = False
            else:
                need_to_login = False

    if need_to_login:
        session = login.login_by_qrcode(sleep_time=5, timeout=600,
                                        qrcode_display_func=lambda img_bytes: login.show_qrcode_image(img_bytes),
                                        login_successful_func=lambda status: print(i18n.translate("login_succeed")),
                                        not_scanned_func=lambda status: print(i18n.translate("scan_the_qrcode")),
                                        not_confirmed_func=lambda status: print(i18n.translate("qrcode_scanned_please_confirm")),
                                        force_break_loop_func=lambda status: False,
                                        should_regen_qrcode_func=lambda status: True,
                                        login_failed_func=lambda status: print(i18n.translate("login_failed")),)
        session.save_session(session_saving_path)
    else:
        print(i18n.translate("session_loaded_successfully"))