import datetime
import ipaddress
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

"""
本文件用于生成证书文件，生成后运行agent_registry/start.py本地启动
"""

# ========== 配置 ==========
RSA_KEY_SIZE = 3072
CERT_VALID_DAYS = 365
CA_COMMON_NAME = "MyTestCA"
SERVER_COMMON_NAME = "127.0.0.1"
CLIENT_COMMON_NAME = "testclient"
SERVER_KEY_PASSWORD = b"9$Qw#3mKpL&8xRz@2yFbA7!cD"   # 服务端私钥密码
# ==========================

# 1. 生成 CA 根证书（带 basicConstraints CA:TRUE）
ca_key = rsa.generate_private_key(public_exponent=65537, key_size=RSA_KEY_SIZE)
ca_subject = ca_issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"CN"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"MyTestCA"),
    x509.NameAttribute(NameOID.COMMON_NAME, CA_COMMON_NAME),
])
ca_cert = (
    x509.CertificateBuilder()
    .subject_name(ca_subject)
    .issuer_name(ca_issuer)
    .public_key(ca_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
    .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=CERT_VALID_DAYS))
    .add_extension(
        x509.BasicConstraints(ca=True, path_length=None),  # 关键：标记为 CA 证书
        critical=True,
    )
    .add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_encipherment=False,
            key_cert_sign=True,      # 允许签发下级证书
            crl_sign=True,
            content_commitment=False,
            data_encipherment=False,
            key_agreement=False,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    )
    .sign(ca_key, hashes.SHA256())
)

# 保存 CA 根证书 (trust.cer)
with open("../etc/ssl/trust.cer", "wb") as f:
    f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

# 2. 生成服务端证书
server_key = rsa.generate_private_key(public_exponent=65537, key_size=RSA_KEY_SIZE)
server_subject = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"CN"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"MyDevOrg"),
    x509.NameAttribute(NameOID.COMMON_NAME, SERVER_COMMON_NAME),
])
server_cert = (
    x509.CertificateBuilder()
    .subject_name(server_subject)
    .issuer_name(ca_subject)
    .public_key(server_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
    .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=CERT_VALID_DAYS))
    .add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    )
    .add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_encipherment=True,
            key_cert_sign=False,
            crl_sign=False,
            content_commitment=False,
            data_encipherment=False,
            key_agreement=False,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    )
    .add_extension(
        x509.ExtendedKeyUsage([x509.ExtendedKeyUsageOID.SERVER_AUTH]),
        critical=False,
    )
    .sign(ca_key, hashes.SHA256())
)

# 保存服务端证书 (server.cer) 和加密的私钥 (server_key.pem)
with open("../etc/ssl/server.cer", "wb") as f:
    f.write(server_cert.public_bytes(serialization.Encoding.PEM))
with open("../etc/ssl/server_key.pem", "wb") as f:
    f.write(server_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(SERVER_KEY_PASSWORD),
    ))

# 3. 生成客户端证书
client_key = rsa.generate_private_key(public_exponent=65537, key_size=RSA_KEY_SIZE)
client_subject = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"CN"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"MyDevOrg"),
    x509.NameAttribute(NameOID.COMMON_NAME, CLIENT_COMMON_NAME),
])
client_cert = (
    x509.CertificateBuilder()
    .subject_name(client_subject)
    .issuer_name(ca_subject)
    .public_key(client_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
    .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=CERT_VALID_DAYS))
    .add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_encipherment=False,
            key_cert_sign=False,
            crl_sign=False,
            content_commitment=False,
            data_encipherment=False,
            key_agreement=False,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    )
    .add_extension(
        x509.ExtendedKeyUsage([x509.ExtendedKeyUsageOID.CLIENT_AUTH]),
        critical=False,
    )
    .sign(ca_key, hashes.SHA256())
)

# 保存客户端证书 (client.cer) 和未加密的私钥 (client_key.pem)
with open("../etc/ssl/client.cer", "wb") as f:
    f.write(client_cert.public_bytes(serialization.Encoding.PEM))
with open("../etc/ssl/client_key.pem", "wb") as f:
    f.write(client_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))

print("✅ 生成完成！文件列表：")
print("  trust.cer        - CA 根证书（配置到 ssl_ca_certs）")
print("  server.cer       - 服务端证书（ssl_certfile）")
print("  server_key.pem   - 服务端私钥（ssl_keyfile，已加密）")
print("  client.cer       - 客户端证书（供 Postman 使用）")
print("  client_key.pem   - 客户端私钥（供 Postman 使用）")
print(f"\n服务端私钥密码: {SERVER_KEY_PASSWORD.decode()}")