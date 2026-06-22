# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from typing import Optional, Dict, Any
from loguru import logger
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from cryptography import x509
import json

from a2a.types import AgentCardSignature
from google.protobuf.json_format import MessageToDict


class AgentCardSigner:

    def __init__(
        self,
        private_key_path: str = "",
        cert_path: str = "",
        password_path: Optional[str] = None,
        jku_url: str = "",
        algorithm: str = "RS256",
        sign_enabled: bool = True
    ):
        self.private_key_path = private_key_path
        self.cert_path = cert_path
        self.password_path = password_path
        self.jku_url = jku_url
        self.algorithm = algorithm
        self.sign_enabled = sign_enabled
        self._private_key = None
        self._password = None
        self._kid = None
        self._algorithm_map = {
            "RS256": hashes.SHA256(),
            "RS384": hashes.SHA384(),
            "RS512": hashes.SHA512()
        }

        if self.sign_enabled:
            self._load_credentials()
            self._load_cert()

    def is_enabled(self) -> bool:
        return self.sign_enabled

    def _load_credentials(self):
        try:
            with open(self.private_key_path, 'rb') as f:
                private_key_data = f.read()

            password = None
            if self.password_path:
                with open(self.password_path, 'r') as f:
                    password = f.read().strip().encode('utf-8')

            self._private_key = serialization.load_pem_private_key(
                private_key_data,
                password=password,
                backend=default_backend()
            )

            logger.info("Private key loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            raise

    def _load_cert(self):
        try:
            with open(self.cert_path, 'rb') as f:
                cert_data = f.read()

            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            self._kid = format(cert.serial_number, 'x')

            logger.info(f"Certificate loaded successfully, kid={self._kid}")
        except Exception as e:
            logger.error(f"Failed to load certificate: {e}")
            raise

    def _canonicalize_agent_card(self, agent_card: Dict[str, Any]) -> Dict[str, Any]:
        try:
            canonical = {}
            for key in sorted(agent_card.keys()):
                value = agent_card[key]
                if isinstance(value, dict):
                    canonical[key] = self._canonicalize_agent_card(value)
                elif isinstance(value, list):
                    canonical[key] = self._canonicalize_list(value)
                else:
                    canonical[key] = value
            return canonical
        except Exception as e:
            logger.error(f"Failed to canonicalize agent card: {e}")
            raise

    def _canonicalize_list(self, lst: list) -> list:
        result = []
        for item in lst:
            if isinstance(item, dict):
                result.append(self._canonicalize_agent_card(item))
            elif isinstance(item, list):
                result.append(self._canonicalize_list(item))
            else:
                result.append(item)
        try:
            return sorted(result)
        except TypeError:
            return result

    def _create_jwk_header(self, kid: str) -> Dict[str, str]:
        try:
            public_key = self._private_key.public_key()
            numbers = public_key.public_numbers()

            jwk = {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": self.algorithm,
                "n": self._base64url_encode(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, 'big')),
                "e": self._base64url_encode(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, 'big'))
            }

            return jwk
        except Exception as e:
            logger.error(f"Failed to create JWK header: {e}")
            raise

    def _base64url_encode(self, data: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

    def _create_signature(self, data: str) -> str:
        try:
            data_bytes = data.encode('utf-8')

            signature = self._private_key.sign(
                data_bytes,
                padding.PKCS1v15(),
                self._algorithm_map.get(self.algorithm, hashes.SHA256())
            )

            signature_b64 = self._base64url_encode(signature)
            return signature_b64
        except Exception as e:
            logger.error(f"Failed to create signature: {e}")
            raise

    def sign_agent_card(self, agent_card: Any) -> Any:
        logger.info(f"sign_agent_card called, sign_enabled={self.sign_enabled}")
        if not self.sign_enabled:
            logger.debug("Signing is disabled, returning original agent card")
            return agent_card

        try:
            logger.info(f"sign_agent_card: kid={self._kid}")
            agent_card_dict = MessageToDict(agent_card, preserving_proto_field_name=True)

            canonical_card = self._canonicalize_agent_card(agent_card_dict)
            canonical_json = json.dumps(canonical_card, separators=(',', ':'), sort_keys=True)

            signature = self._create_signature(canonical_json)

            kid = self._kid
            protected_header = self._create_protected_header(kid)

            protected_b64 = self._base64url_encode(json.dumps(protected_header, separators=(',', ':')).encode('utf-8'))

            new_sig = AgentCardSignature()
            new_sig.protected = protected_b64
            new_sig.signature = signature

            logger.info(f"new_sig.protected: {new_sig.protected}")
            logger.info(f"new_sig.signature length: {len(new_sig.signature)}")

            agent_card.signatures.append(new_sig)

            logger.info(f"agent_card.signatures after append: {len(agent_card.signatures)}")
            logger.info(f"Agent card signed successfully, kid={kid}")
            return agent_card

        except Exception as e:
            logger.warning(f"Failed to sign agent card: {e}. Returning original agent card.")
            return agent_card

    def _create_protected_header(self, kid: str) -> Dict[str, Any]:
        """Create protected header for JWS signature"""
        public_key = self._private_key.public_key()
        numbers = public_key.public_numbers()

        return {
            "alg": self.algorithm,
            "typ": "JOSE",
            "kid": kid,
            "jku": self.jku_url,
            "kty": "RSA",
            "use": "sig",
            "n": self._base64url_encode(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, 'big')),
            "e": self._base64url_encode(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, 'big'))
        }