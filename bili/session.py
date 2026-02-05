import time, json

class Session:

    def __init__(self, login_time: str, cookies: dict):
        self.login_time = login_time
        self.cookies = cookies
        self.session_data = cookies['SESSDATA']
        self.jct = cookies['bili_jct']
        self.uid = cookies['DedeUserID']
        self.md5 = cookies['DedeUserID__ckMd5']
        self.session_id = cookies['sid']
        self.sec_ck = cookies["sec_ck"]


    def save_session(self, filepath: str) -> None:
        """
        保存Cookies到本地文件
        :param filepath: 保存的文件路径
        """
        json_obj = {
            'login_time': self.login_time,
            'cookies': self.cookies
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_obj, f, ensure_ascii=False, indent=4)