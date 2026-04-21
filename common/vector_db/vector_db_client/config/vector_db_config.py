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

from enum import Enum

from common.llm.config.config_reader import read_config_as_json


class VectorDBType(Enum):
    CustomVDB = 'custom_vector_db'

def convert_vectordb_type(vectordb_type:str)->VectorDBType:
    for member in VectorDBType:
        if member.value == vectordb_type:
            return member
    return VectorDBType.CustomVDB

class VectorDBConfig:
    vectordb_type:VectorDBType
    description:str
    uri:str
    version:str

    def __init__(self,vectordb_type:str,config:dict):
        self.vectordb_type = convert_vectordb_type(vectordb_type)
        self.description = config['description']
        self.uri = config['uri']
        self.version = config['version']

def get_vectordb_config() -> {str, VectorDBConfig}:
    config: dict[str,dict] = read_config_as_json("../../config/vectordb_config.json")
    vectordb_config_item = {}
    for key, value_list in config.items():
        vectordb_config_item[key] = VectorDBConfig(key, value_list)
    return vectordb_config_item

vectordb_config = get_vectordb_config()

def get_vectordb_config_by_type(vectordb_type: VectorDBType) -> VectorDBConfig:
    return vectordb_config[vectordb_type.value] if vectordb_type.value in vectordb_config else None