import configparser
import os

from common.util import cipher_util
from common.util.conf_obj import ConfObj
from common.util.constant_param import CONFIG_FILE_PATH


def load_conf_as_dict(conf_file: str) -> dict:
    config = configparser.ConfigParser()
    try:
        with open(conf_file, 'r', encoding='utf-8') as f:
            # 读取文件内容
            config.read_string('[DEFAULT]\n' + f.read())
            return dict(config['DEFAULT'])
    except Exception as e:
        return {}


def load_conf_obj(conf_file: str) -> ConfObj:
    config_dict = load_conf_as_dict(conf_file)
    return ConfObj.as_object(config_dict)


def load_cert_password(password_path: str) -> str:
    if not os.path.exists(password_path):
        return ""
    # read password file and decrypt content
    with open(password_path, 'r', encoding='utf-8') as f:
        str_content = f.read()
        return CipherUtil.decrypt(str_content)


# 单例对象
conf_singleton_obj = load_conf_obj(CONFIG_FILE_PATH)
