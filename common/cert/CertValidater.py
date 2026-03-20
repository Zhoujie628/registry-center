import datetime
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, ec

from common.cert import CertParser
from common.cert.X509Obj import X509Obj
from common.util.ConfObj import ConfObj
from common.util.ConfUtil import load_cert_password
from common.util.Constant import CONFIG_FILE_PATH
from common.util.ValidationResult import ValidationResult


class PathValidator:
    def __init__(self, cert_path: str, suffix:str, is_required=True, conf_tip=""):
        self.cert_path = cert_path
        self.suffix = suffix.lower()
        self.is_required = is_required
        new_conf_tip = f'"{conf_tip}"' if conf_tip is not None and conf_tip != "" else ""
        self.conf_tip = f"Please check {new_conf_tip} config in \"etc/conf/server.conf\" file and try again."

    def is_support_format(self, file_extension: str) -> bool:
        if self.suffix == "":
            # 没后缀的不校验
            return True
        return self.suffix == file_extension.lower()

    def validate(self) -> ValidationResult:
        if self.cert_path is None or self.cert_path == '':
            if not self.is_required:
                return ValidationResult(True, "Not config! ")
            return ValidationResult(False, f"Cert file path is empty! {self.conf_tip}")
        # 到这里就是填了，填了就校验
        cert_path_obj = Path(self.cert_path)
        if not cert_path_obj.exists():
            return ValidationResult(False, f"Cert file not exist：{self.cert_path}. {self.conf_tip}")
        file_extension = cert_path_obj.suffix.lower()
        if not self.is_support_format(file_extension):
            return ValidationResult(False, f"Cert file extension is not support!  {self.conf_tip}")
        return ValidationResult(True, "")

class AbstractValidatorLink:
    def __init__(self, conf_obj: ConfObj):
        self.conf_obj = conf_obj
        self.link = self.build_link()

    def build_link(self):
        pass

    def validate(self) -> ValidationResult:
        for link in self.link:
            result = link.validate()
            if not result.is_valid:
                return result
        return ValidationResult(True, "")


class PathValidatorLink(AbstractValidatorLink):

    def build_link(self):
        conf_obj = self.conf_obj
        return [
            PathValidator(conf_obj.ssl_certfile, suffix=".cer", is_required=True, conf_tip="ssl_certfile"),
            PathValidator(conf_obj.ssl_keyfile, suffix=".pem", is_required=True, conf_tip="ssl_keyfile"),
            PathValidator(conf_obj.ssl_keyfile_password, suffix="", is_required=True, conf_tip="ssl_keyfile_password"),
            PathValidator(conf_obj.ssl_ca_certs, suffix=".cer", is_required=True, conf_tip="ssl_ca_certs"),
            PathValidator(conf_obj.ssl_crl_file, suffix=".crl", is_required=False, conf_tip="ssl_crl_file")
        ]


class CommonContentValidator:
    def __init__(self, cert_path: str, conf_tip=""):
        self.cert_path = cert_path
        new_conf_tip = f'"{conf_tip}"' if conf_tip is not None and conf_tip != "" else ""
        self.conf_tip = f"Please check {new_conf_tip} config in \"etc/conf/server.conf\" file and try again."

    def validate_public_key_length(self, public_key) -> bool:
        """验证密钥算法和长度"""
        if isinstance(public_key, rsa.RSAPublicKey):
            return public_key.key_size >= 3072
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            # 256位及以上
            return public_key.key_size >= 256
        return False

    def validate_private_key_length(self, private_key) -> bool:
        """验证密钥算法和长度"""
        if isinstance(private_key, rsa.RSAPrivateKey):
            return private_key.key_size >= 3072
        if isinstance(private_key, ec.EllipticCurvePrivateKey):
            # 256位及以上
            return private_key.key_size >= 256
        return False

    def validate_certificate_validity(self, x509_obj: X509Obj) -> bool:
        """验证证书有效期"""
        current_time = datetime.datetime.now(datetime.UTC)
        for cert_obj in x509_obj.cert_list:
            try:
                valid_from = datetime.datetime.fromisoformat(cert_obj.valid_from.replace('Z', '+00:00'))
                valid_to = datetime.datetime.fromisoformat(cert_obj.valid_to.replace('Z', '+00:00'))
                if current_time < valid_from or current_time > valid_to:
                    return False
            except (ValueError, TypeError):
                return False
        # 每本证书的有效期都要校验对
        return True

    def validate(self) -> ValidationResult:
        pass


class CerContentValidator(CommonContentValidator):

    def validate(self) -> ValidationResult:
        # 读取cer证书
        try:
            x509_obj = CertParser.parse_cer_certificate(self.cert_path)
            if len(x509_obj.cert_list) == 0:
                return ValidationResult(False, f"No certificate found! {self.conf_tip}")
            # 校验X.509v3格式，校验公钥算法及长度，校验有效期
            for cert_obj in x509_obj.cert_list:
                # 1. 证书格式校验：X.509v3
                if cert_obj.version != x509.Version.v3:
                    return ValidationResult(False, f"Certificate format is not X.509v3. {self.conf_tip}")
                # 2. 密钥算法、长度校验，cer只校验公钥，因为没有私钥
                if not self.validate_public_key_length(cert_obj.public_key):
                    return ValidationResult(False, f"Certificate key algorithm or length does not meet requirements. {self.conf_tip}")

            # 3. 有效期校验，单独跑一把，确保每本证书的有效期对比的currentTime是一个
            if not self.validate_certificate_validity(x509_obj):
                return ValidationResult(False, f"Certificate is not valid at current time. {self.conf_tip}")

            return ValidationResult(True, f"CER certificate validation passed! {self.cert_path}")
        except Exception as e:
            return ValidationResult(False, f"{e} {self.conf_tip}")


class PrivateKeyValidator(CommonContentValidator):
    def __init__(self, cert_path: str, password:str = None, conf_tip=""):
        super().__init__(cert_path=cert_path, conf_tip=conf_tip)
        self.password = password

    def validate(self) -> ValidationResult:
        try:
            # 读取cer证书，验证密码是否有效
            private_key = CertParser.parse_pem_files(self.cert_path, self.password)
            # 校验私钥算法及长度
            if not self.validate_private_key_length(private_key):
                return ValidationResult(False,
                                        f"Certificate key algorithm or length does not meet requirements. {self.conf_tip}")
            return ValidationResult(True, f"PEM privatekey validation passed! {self.cert_path}")
        except Exception as e:
            return ValidationResult(False, f"{e} {self.conf_tip}")


class CRLValidator(CommonContentValidator):
    crl_list_data = None

    def validate_crl_validity(self, crl_list: x509.CertificateRevocationList) -> bool:
        """验证CRL有效期"""
        current_time = datetime.datetime.now(datetime.UTC)
        return crl_list.last_update_utc <= current_time <= crl_list.next_update_utc

    def validate(self) -> ValidationResult:
        try:
            if self.cert_path is None or self.cert_path == '':
                # 非必填，没填就不校验
                return ValidationResult(True, "CRL not config! ")
            # 到这里就是填了，填了就校验
            cert_path_obj = Path(self.cert_path)
            if not cert_path_obj.exists():
                return ValidationResult(False, f"CRL file not exist：{self.cert_path}. {self.conf_tip}")
            # 读取CRL
            crl_list = CertParser.parse_crl_list(self.cert_path)
            self.crl_list_data = crl_list
            # 1. 校验CRL格式：X.509v2，有扩展的是v2，没有扩展的是v1
            is_v2 = len(crl_list.extensions) > 0
            if not is_v2:
                return ValidationResult(False, f"CRL format is not X.509v2. {self.conf_tip}")
            # 2. 校验有效期：当前时间有效
            if not self.validate_crl_validity(crl_list):
                return ValidationResult(False, f"CRL is not valid at current time. {self.conf_tip}")
            return ValidationResult(True, f"CRL validation passed! {self.cert_path}")
        except Exception as e:
            return ValidationResult(False, f"{e} {self.conf_tip}")


class CerContentValidatorLink(AbstractValidatorLink):

    def build_link(self):
        conf_obj = self.conf_obj
        return [
            CerContentValidator(conf_obj.ssl_certfile, conf_tip="ssl_certfile"),
            CerContentValidator(conf_obj.ssl_ca_certs, conf_tip="ssl_ca_certs")
        ]


class CertValidator:

    def __init__(self, conf_obj: ConfObj):
        self.conf_obj = conf_obj

    def validate(self) -> ValidationResult:
        """
        pem私钥校验以下内容：
            - 证书私钥密钥算法、密钥长度：RSA(≥3072 bits)，ECDSA(≥256 bits)，不满足则退出进程启动
            - 有效期：当前时间有效，不满足则退出进程启动
            - 是否加密私钥：是否有口令、口令复杂度，不满足则给出日志打印
            - 私钥口令与私钥匹配性：不满足则退出进程启动
            - 私钥与公钥的匹配性：不满足则退出进程启动
        cer校验以下内容:
            - 校验证书格式：X.509v3
            - 证书公钥算法、密钥长度：RSA(≥3072 bits)，ECDSA(≥256 bits)，不满足则退出进程启动
            - 校验有效期：当前时间有效
            - 密钥算法、长度
        crl校验以下内容:
            - 校验证书格式：X.509v2
            - 校验有效期：当前时间有效
        :return: ValidationResult
        """
        # 1. 基础校验，校验路径是否存在，文件名格式是否符合要求
        if not os.path.exists(CONFIG_FILE_PATH):
            return ValidationResult(False,
                                    "Config file not exists! Please config \"etc/conf/server.conf\" "
                                    "file and try again.")
        result = PathValidatorLink(self.conf_obj).validate()
        if not result.is_valid:
            return result
        # 2. 读取证书，校验X.509v3格式，校验公钥算法及长度，校验有效期
        result = CerContentValidatorLink(self.conf_obj).validate()
        if not result.is_valid:
            return result

        # 3. 读取私钥，验证密码是否有效，校验私钥算法及长度
        key_path = self.conf_obj.ssl_keyfile
        password = load_cert_password(self.conf_obj.ssl_keyfile_password)
        result = PrivateKeyValidator(cert_path=key_path, password=password, conf_tip="ssl_keyfile").validate()
        if not result.is_valid:
            return result
        # 4. 读取crl，验证crl格式和有效期
        crl_validator = CRLValidator(cert_path=self.conf_obj.ssl_crl_file, conf_tip="ssl_crl_file")
        result = crl_validator.validate()
        if result.is_valid:
            # 校验通过后把单例的吊销列表缓存起来
            self.conf_obj.crl_list_data = crl_validator.crl_list_data
        return result
