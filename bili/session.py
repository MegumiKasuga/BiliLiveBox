import time, json, requests
from bs4 import BeautifulSoup
from bili import constants
from bili import encrypter

class Session:

    def __init__(self, login_time: str, cookies: dict, refresh_token: str):
        self.__set_data__(login_time, cookies, refresh_token)


    def __set_data__(self, login_time: str, cookies: dict, refresh_token: str) -> None:
        self.login_time = login_time
        self.cookies = cookies
        self.session_data = cookies['SESSDATA']
        self.jct = cookies['bili_jct']
        self.uid = cookies['DedeUserID']
        self.md5 = cookies['DedeUserID__ckMd5']
        self.session_id = cookies['sid']
        self.sec_ck = cookies["sec_ck"]
        self.refresh_token = refresh_token


    def save_session(self, filepath: str) -> None:
        """
        保存Cookies到本地文件
        :param filepath: 保存的文件路径
        """
        json_obj = {
            'login_time': self.login_time,
            'cookies': self.cookies,
            'refresh_token': self.refresh_token
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_obj, f, ensure_ascii=False, indent=4)


    def cookie_need_to_refresh(self) -> dict[str, bool | int]:
        """
        检查Cookies是否需要刷新
        :return: 一个字典，包含以下键值对：
                    - "logged_in": 布尔值，表示当前是否已登录
                    - "need_to_refresh": 布尔值，表示是否需要刷新Cookies
                    - "timestamp": 整数，表示服务器返回的时间戳
        """
        csrf_token = self.jct
        result = requests.get("https://passport.bilibili.com/x/passport-login/web/cookie/info", headers=constants.headers, cookies=self.cookies, params={"csrf": csrf_token})

        json_obj = result.json()
        logged_in = json_obj['code'] == 0
        need_to_refresh = json_obj['data']['refresh']
        timestamp = json_obj['data']['timestamp']

        return {
            "logged_in": logged_in,
            "need_to_refresh": need_to_refresh,
            "timestamp": timestamp
        }


    def refresh_cookies(self, timestamp: int) -> bool:
        """
        刷新Cookies
        :param timestamp: 从session#cookie_need_to_refresh()函数的返回值获取的时间戳
        :return: 刷新是否成功
        """
        try:
            correspond_path = encrypter.get_correspond_path(timestamp)
            url = f'https://www.bilibili.com/correspond/1/{correspond_path}'.encode()
            response = requests.get(url, headers=constants.headers, cookies=self.cookies)
            soup = BeautifulSoup(response.content, 'lxml')
            data = soup.find('body')
            if data is None:
                return False
            key = data.find('div', attrs={'id': '1-name'})
            if key is None:
                return False
            refresh_csrf = key.text

            params = {
                'csrf': self.jct,
                'refresh_csrf': refresh_csrf,
                'source': 'main_web',
                'refresh_token': self.refresh_token
            }
            url = 'https://passport.bilibili.com/x/passport-login/web/cookie/refresh'
            response = requests.post(url, headers=constants.headers, cookies=self.cookies, params=params)

            json_obj = response.json()
            if json_obj['code'] != 0:
                return False

            self.__set_data__(time.gmtime(), response.cookies.get_dict(), json_obj['data']['refresh_token'])

            url = 'https://passport.bilibili.com/x/passport-login/web/confirm/refresh'
            params = {
                'csrf': self.jct,
                'refresh_token': self.refresh_token
            }

            response = requests.post(url, headers=constants.headers, cookies=self.cookies, params=params)
            json_obj = response.json()
            if json_obj['code'] != 0:
                return False
            return True
        except:
            return False