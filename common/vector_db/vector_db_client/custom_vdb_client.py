# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# All Rights Reserved.
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
from common.vector_db.vector_db_client.config.vector_db_client import VectorDBClient
from common.vector_db.vector_db_client.config.vector_db_client_registry import vectordb_tool_register
from common.vector_db.vector_db_client.config.vector_db_config import VectorDBType

@vectordb_tool_register(VectorDBType.CustomVDB)
class CustomVDBClient(VectorDBClient):
    def __init__(self, config: dict):
        super().__init__(config)
        client_uri = config["uri"]

    def create_collection(self, data):
        # todo To be customized by the customer
        return None

    def insert_entity(self, data):
        # todo To be customized by the customer
        return False

    def delete_entity(self, data):
        # todo To be customized by the customer
        return False

    def update_entity(self, data):
        # todo To be customized by the customer
        return False

    def retrieve_entity(self, data):
        # todo To be customized by the customer
        return []

    def query_by_key(self, data):
        # todo To be customized by the customer
        return []

    def get_all_entities(self, data):
        # todo To be customized by the customer
        return []
