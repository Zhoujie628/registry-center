# agent_registry/start.py
import sys

import uvicorn

from agent_registry.server import app
from common.cert.CertValidater import CertValidator
from common.util.ConfUtil import conf_singleton_obj, load_cert_password


def main():
    # 校验配置
    conf_obj = conf_singleton_obj
    result = CertValidator(conf_obj).validate()
    if not result.is_valid:
        sys.exit(result.message)
    uvicorn.run(app, host=conf_obj.ip, port=conf_obj.port, log_config=None,
                # 身份证书路径
                ssl_certfile=conf_obj.ssl_certfile,
                # 私钥路径
                ssl_keyfile=conf_obj.ssl_keyfile,
                # 私钥密码
                ssl_keyfile_password=load_cert_password(conf_obj.ssl_keyfile_password),
                # 信任证书
                ssl_ca_certs=conf_obj.ssl_ca_certs,
                # 是否校验客户端证书，填了如果浏览器没证书就没法访问了
                ssl_cert_reqs=conf_obj.verify_client
                )


if __name__ == "__main__":
    main()
