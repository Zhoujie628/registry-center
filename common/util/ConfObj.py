import os
import ssl

from common.util.Constant import ROOT_PATH

DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = 5000
DEFAULT_SSL_CERT_FILE = "etc/ssl/server.cer"
DEFAULT_SSL_KEYFILE = "etc/ssl/server_key.pem"
DEFAULT_KEY_PASSWORD = "etc/ssl/cert_pwd"
DEFAULT_SSL_CA_CERTS = "etc/ssl/trust.cer"
DEFAULT_SSL_CRLFILE = "etc/ssl/revocationlist.crl"
DEFAULT_VERIFY_CLIENT = ssl.CERT_REQUIRED


def as_absolute_path(path):
    new_path = path
    if path.startswith("etc/"):
        new_path = os.path.join(ROOT_PATH, path)
    new_path = os.path.normpath(new_path)
    return new_path

class ConfObj:
    ip = DEFAULT_IP
    port = DEFAULT_PORT
    ssl_certfile = DEFAULT_SSL_CERT_FILE
    ssl_keyfile = DEFAULT_SSL_KEYFILE
    ssl_keyfile_password = DEFAULT_KEY_PASSWORD
    ssl_ca_certs = DEFAULT_SSL_CA_CERTS
    ssl_crl_file = DEFAULT_SSL_CRLFILE
    verify_client = DEFAULT_VERIFY_CLIENT

    @classmethod
    def as_object(cls, in_dict:dict):
        obj = cls()

        obj.ip = in_dict.get("ip", DEFAULT_IP)
        # 字符串要转成int
        port = in_dict.get("port", DEFAULT_PORT)
        if isinstance(port, str):
            port = int(port)
        obj.port = port
        # 相对路径要变成绝对路径
        obj.ssl_certfile = as_absolute_path(in_dict.get("ssl_certfile", DEFAULT_SSL_CERT_FILE))
        obj.ssl_keyfile = as_absolute_path(in_dict.get("ssl_keyfile", DEFAULT_SSL_KEYFILE))
        obj.ssl_keyfile_password = as_absolute_path(in_dict.get("ssl_keyfile_password", DEFAULT_KEY_PASSWORD))
        obj.ssl_ca_certs = as_absolute_path(in_dict.get("ssl_ca_certs", DEFAULT_SSL_CA_CERTS))
        obj.ssl_crl_file = as_absolute_path(in_dict.get("ssl_crl_file", DEFAULT_SSL_CRLFILE))

        # 大部分场景都是校验
        not_verified = in_dict.get("verify_client", "").lower() == "false"
        obj.verify_client = ssl.CERT_NONE if not_verified else ssl.CERT_REQUIRED
        return obj


