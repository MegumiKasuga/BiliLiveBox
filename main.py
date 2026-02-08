import asyncio
import os.path

import requests

from config.i18n.locals import I18nManager
from config.config import Config
from bili import login
from bili import session
from bili import encrypter
from bili import constants
from bili import live
import urllib.parse

session_saving_path = 'usr/session.json'

if __name__ == '__main__':

    cfg = Config(config_path="config.json")

    cfg.register_basic_config_item("ForceLogin", bool, False, "Whether to force login via QR code, ignoring saved session")
    cfg.load()
    i18n = I18nManager(locals_dir="lang", default_lang="en_us")

    sessions = None
    need_to_login = True
    user, wbi = None, None

    if (not bool(cfg.get_config_value('ForceLogin')) and
            os.path.exists(session_saving_path)):
        sessions = login.login_by_session_file(session_saving_path)
        need_to_refresh = sessions.cookie_need_to_refresh()
        if need_to_refresh['logged_in']:
            if need_to_refresh['need_to_refresh']:
                if sessions.refresh_cookies(need_to_refresh['timestamp']):
                    sessions.save_session(session_saving_path)
                    user, wbi = sessions.get_user_data('usr/user.json', 'usr/wbi.json')
                    need_to_login = False
            else:
                need_to_login = False
                user, wbi = sessions.get_user_data('usr/user.json', 'usr/wbi.json')

    if need_to_login:
        sessions = login.login_by_qrcode(sleep_time=5, timeout=600,
                                        qrcode_display_func=lambda img_bytes: login.show_qrcode_image(img_bytes),
                                        login_successful_func=lambda status: print(i18n.translate("login_succeed")),
                                        not_scanned_func=lambda status: print(i18n.translate("scan_the_qrcode")),
                                        not_confirmed_func=lambda status: print(i18n.translate("qrcode_scanned_please_confirm")),
                                        force_break_loop_func=lambda status: False,
                                        should_regen_qrcode_func=lambda status: True,
                                        login_failed_func=lambda status: print(i18n.translate("login_failed")),)
        sessions.save_session(session_saving_path)
        user, wbi = sessions.get_user_data('usr/user.json', 'usr/wbi.json')
    else:
        print(i18n.translate("session_loaded_successfully"))

    liveHouse = live.get_live_house(22499290, sessions, wbi)
    loop = asyncio.new_event_loop()
    eventLoop = live.LiveEventLoop(liveHouse, liveHouse.host_list[0], user, 5)

    if loop.is_running():
        task = asyncio.create_task(
            eventLoop.start()
        )
    else:
        loop.run_until_complete(
            eventLoop.start()
        )