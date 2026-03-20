# agent_registry/start.py
import os
import ssl
import sys

import uvicorn

from agent_registry.server import app
from common.cert.CertValidater import CertValidator
from common.util.ConfUtil import conf_singleton_obj, load_cert_password
from common.util.config_util import get_conf

from uvicorn import config

def my_create_ssl_context(
        certfile: str | os.PathLike[str],
        keyfile: str | os.PathLike[str] | None,
        password: str | None,
        ssl_version: int,
        cert_reqs: int,
        ca_certs: str | os.PathLike[str] | None,
        ciphers: str | None,
) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl_version)
    get_password = (lambda: password) if password else None
    ctx.load_cert_chain(certfile, keyfile, get_password)
    ctx.verify_mode = ssl.VerifyMode(cert_reqs)
    if ca_certs:
        ctx.load_verify_locations(ca_certs)
        if len(conf_singleton_obj.get_crl_list()) > 0:
            # 如果有CRL的场景，追加CRL
            ctx.load_verify_locations(conf_singleton_obj.ssl_crl_file)
            # 配置为校验CRL模式
            ctx.verify_flags |= ssl.VERIFY_CRL_CHECK_LEAF
    if ciphers:
        ctx.set_ciphers(ciphers)

    return ctx

# 由于原版config不支持加载crl，因此扩展crl支持
config.create_ssl_context = my_create_ssl_context


class CustomUvicornServer:
    """Customized Uvicorn server, which is used to add additional security configurations."""

    def __init__(self, server_config, conf_obj):
        self.server_config = server_config
        self.conf_obj = conf_obj

    def run(self):
        config = uvicorn.Config(
            app=app,
            host=self.server_config.get("ip", "127.0.0.1"),
            port=int(self.server_config.get("port", 8888)),
            ssl_certfile=self.conf_obj.ssl_certfile,
            # 私钥路径
            ssl_keyfile=self.conf_obj.ssl_keyfile,
            # 私钥密码
            ssl_keyfile_password=load_cert_password(self.conf_obj.ssl_keyfile_password),
            # 信任证书
            ssl_ca_certs=self.conf_obj.ssl_ca_certs,
            # 是否校验客户端证书，填了如果浏览器没证书就没法访问了
            ssl_cert_reqs=self.conf_obj.verify_client,
            timeout_keep_alive=0,
            timeout_graceful_shutdown=int(self.server_config.get("connection.timeout", 30)),
            log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()


def main():
    # 校验配置
    conf_obj = conf_singleton_obj
    result = CertValidator(conf_obj).validate()
    if not result.is_valid:
        sys.exit(result.message)
    server_config = get_conf()
    # 创建并启动服务器
    server = CustomUvicornServer(server_config, conf_obj)
    server.run()


if __name__ == "__main__":
    main()
