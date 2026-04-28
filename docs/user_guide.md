# 注册中心用户手册

## 1 注册中心功能简介
注册中心是一个专注于Agent统一管理的服务，支持用户将来自不同厂商的Agent进行集中注册与管理，实现多源Agent的可控接入与维护。主要功能包括：

- **Agent注册**：支持将不同厂商的Agent注册到中心，统一纳管。
- **批量查询**：根据指定条件查询符合条件的Agent列表。
- **语义检索**：根据自然语言语义检索相匹配的Agent，提升查找灵活性。
- **唯一查找**：按 Agent 名称精确查找唯一的Agent实例。
- **Agent修改**：支持按名称修改已注册Agent的配置或元信息。
- **注销Agent**：按名称注销不再使用的Agent。

通过这些功能，注册中心帮助用户高效整合、维护与发现各类 Agent，为上层编排与协同提供基础能力。

## 2 组件交互接口定义

### 2.1 Agent注册

#### 2.1.1 典型场景

运营商或设备厂商需要注册新AgentCard时，可通过调用该接口在注册中心组件中创建新的AgentCard信息

#### 2.1.2 接口功能

- 注册指定AgentCard信息到注册中心

#### 2.1.3 接口约束

- 单次注册AgentCard信息报文大小不得超过1024K
- 单实例上该接口最大并发数为50

#### 2.1.4 调用方法

POST

#### 2.1.5 URI

/rest/a2a-t/v1/agents/register

#### 2.1.6 请求参数

- body参数列表 详细请参见表：provider对象的参数列表

AgentCard结构说明：

| 字段路径                    | 类型                        | 必填 | 说明                                                                               |
|:------------------------|:--------------------------|:---|:---------------------------------------------------------------------------------|
| `name`                  | string                    | 是  | 最大长度：100 字符；格式要求：仅允许字母、数字、下划线（_）和空格；正则表达式：`^[a-zA-Z0-9_]+(?:\s+[a-zA-Z0-9_]+)*$` |
| `description`           | string                    | 是  | 最大长度：1000 字符                                                                     |
| `supported_interfaces`  | list[AgentInterface]      | 是  |                                                                                  |
| `version`               | string                    | 是  | 最大长度：50 字符                                                                       |
| `provider`              | AgentProvider             | 是  |                                                                                  |
| `capabilities`          | AgentCapabilities         | 是  |                                                                                  |
| `skills`                | list[AgentSkill]          | 是  | 最大数量：100 个技能；每个技能的 JSON 序列化后最大长度：4096 字符                                         |
| `default_input_modes`   | list[str]                 | 否  | 最大数量：100 个                                                                       |
| `default_output_modes`  | list[str]                 | 否  | 最大数量：100 个                                                                       |
| `documentation_url`     | string                    | 否  |                                                                                  |
| `icon_url`              | string                    | 否  |                                                                                  |
| `security_schemes`      | map(str, SecurityScheme)  | 否  |                                                                                  |
| `security_requirements` | list[SecurityRequirement] | 否  | 操作所需的认证要求列表                                                                      |
| `signatures`            | list[AgentCardSignature]  | 否  | 用于验证的加密签名                                                                        

**AgentInterface结构说明：**

| 字段名                | 类型     | 必填 | 说明                                                                           |
|:-------------------|:-------|:---|:-----------------------------------------------------------------------------|
| `url`              | string | 是  | 接口的基础 URL 地址；最大长度：1024 字符；必须为有效的 Web URL 格式                                  |
| `protocol_binding` | string | 是  | 协议绑定标识，表示该接口使用的传输协议（如 `"JSONRPC"`、`"GRPC"`、`HTTP+JSON`/`"REST"`）；最大长度：100 字符 |
| `protocol_version` | string | 否  | A2A 协议版本号，表示该接口支持的 A2A 协议版本（如 `"1.0"` 或 `"1.0.0"`）；                          |
| `tenant`           | string | 否  | 多租户场景下的租户标识符，用于在调用 Agent 时设置租户信息；                                            |

**AgentProvider结构说明：**

| 字段名            | 类型     | 必填 | 说明                                                                         |
|:---------------|:-------|:---|:---------------------------------------------------------------------------|
| `organization` | string | 是  | Agent 提供商的组织名称；最大长度：100 字符；不能为空；禁止包含危险字符（如 `<`、`>`、`&` 等注入风险字符）            |
| `url`          | string | 否  | Agent 提供商组织的官方网站链接；最大长度：1024 字符；必须为有效的 Web URL 格式（如 `https://example.com`） |

**AgentCapabilities结构说明：**

| 字段名                  | 类型                   | 必填 | 说明                                                                                            |
|:---------------------|:---------------------|:---|:----------------------------------------------------------------------------------------------|
| `streaming`          | boolean              | 否  | 是否支持流式传输。如果为 `true`，Agent 能够通过 Server-Sent Events (SSE) 实时返回响应内容；如果为 `false` 或未提供，则仅支持一次性同步响应 |
| `push_notifications` | boolean              | 否  | 是否支持推送通知。如果为 `true`，Agent 能够主动向客户端发送任务状态更新和产物通知；需要配合 `PushNotificationConfig` 进行配置            |
| `state_partial`      | boolean              | 否  | 是否支持部分状态更新。如果为 `true`，Agent 能够在任务执行过程中返回中间状态，而不仅仅是最终结果 (final)；适用于长耗时任务的进度展示                  |
| `interruptible`      | boolean              | 否  | 是否支持任务中断。如果为 `true`，客户端可以发送取消请求来终止正在执行的任务；如果为 `false`，任务一旦启动将无法被取消                            |
| `extensions`         | list[AgentExtension] | 否  | 支持的扩展能力列表。用于声明 Agent 实现的 A2A 协议扩展特性；最大数量：10 个扩展；每个扩展的 JSON 序列化后最大长度：512 字符                    |

**AgentExtension结构说明：**

| 字段名           | 类型      | 必填    | 说明                                                                                     |
|:--------------|:--------|:------|:---------------------------------------------------------------------------------------|
| `uri`         | string  | **是** | 扩展的唯一标识符，必须是版本化的 URI 格式（如 `https://example.com/ext/my-extension/v1`），用于全局唯一标识该扩展；      |
| `description` | string  | 否     | 扩展功能的人类可读说明，描述 Agent 如何使用此扩展；**最大长度：1000 字符** [citation:2][citation:10]                |
| `required`    | boolean | 否     | 表示客户端是否必须支持此扩展。如果为 `true`，客户端**必须**理解并激活该扩展，否则 Agent 将拒绝处理请求；如果为 `false` 或未提供，该扩展为可选能力 |
| `params`      | object  | 否     | 扩展的特定配置参数或发现参数，用于传递扩展初始化所需的额外信息；具体结构由扩展 URI 定义的规范决定；                                   |

**AgentSkill结构说明：**

| 字段名            | 类型           | 必填 | 说明                                                         |
|:---------------|:-------------|:---|:-----------------------------------------------------------|
| `id`           | string       | 是  | 技能的唯⼀标识符，⽤于在 AgentCard 中区分不同技能                             |
| `name`         | string       | 是  | 技能的⼈类可读名称，展示给最终用户的技能标题                                     |
| `description`  | string       | 是  | 技能的详细功能说明，帮助客户理解该技能的具体作用和适用场景                              |
| `tags`         | list[string] | 是  | ⽤于分类和发现的关键词标签，便于客户端按类别检索和匹配技能                              |
| `examples`     | list[string] | 否  | 示例提示或⽤例说明，帮助用户或客户端理解如何使用该技能                                |
| `input_modes`  | list[string] | 否  | ⽀持的输⼊媒体类型列表（MIME 类型），如 `"text/plain"`、`"application/json"` |
| `output_modes` | list[string] | 否  | ⽀持的输出媒体类型列表（MIME 类型），如 `"text/plain"`、`"application/json"` |

#### 2.1.7 请求示例

POST /rest/a2a-t/v1/agents/register HTTP/1.1

Host： your-domain.com

Content-Type： application/json

body体：

```json
{
  "name": "RAN Energy Saving Agent",
  "description": "负责RAN能效优化的自主闭环运行，包括意图探索、意图实现、效果评估与报告。",
  "version": "1.0.0",
  "provider": {
    "organization": "Huawei",
    "url": ""
  },
  "skills": [
    {
      "id": "ran-es-intent-exploration",
      "name": "RAN ES Intent Exploration",
      "description": "评估并确定指定RAN ES意图目标的最佳可能性，考虑当前资源状况和系统能力。",
      "tags": [
        "wireless",
        "energy-saving",
        "intent"
      ]
    },
    {
      "id": "ran-es-intent-lifecycle-management",
      "name": "RAN ES Intent Lifecycle Management",
      "description": "管理RAN节能意图的生命周期，包括创建、修改、删除、激活、去激活意图，并执行数据采集、分析、解决方案制定与配置。",
      "tags": [
        "wireless",
        "energy-saving",
        "intent"
      ]
    },
    {
      "id": "ran-es-intent-reporting",
      "name": "RAN ES Intent Reporting",
      "description": "提供意图报告查询、订阅、通知功能，报告意图实现状态、达成值、推荐值及配置修改信息。",
      "tags": [
        "wireless",
        "energy-saving",
        "reporting"
      ]
    }
  ],
  "capabilities": {
    "streaming": true,
    "push_notifications": false,
    "extensions": []
  },
  "default_input_modes": [
    "text",
    "json"
  ],
  "default_output_modes": [
    "text",
    "json"
  ],
  "supported_interfaces": [
    {
      "protocol_binding": "GPRC",
      "protocol_version": "1.0.0",
      "url": "http://127.0.0.1:5000/"
    },
    {
      "protocol_binding": "HTTP+JSON",
      "protocol_version": "1.0.0",
      "url": "http://127.0.0.1:5000/"
    }
  ]
}
```

#### 2.1.8 响应参数

| 参数名称 | 类型      | 参数值域 | 默认值 | 参数说明 | 参数示例 |
|------|---------|------|-----|------|------|
| -    | boolean | true | -   | xxx  | true |

#### 2.1.9 响应示例

- 返回状态码201：创建成功

```json
true
```

- 返回状态码422：创建失败

```json
{
  "detail": "The agent description can contain a maximum of 1000 characters."
}
```

- 返回状态码409：创建失败

```json
{
  "detail": "Agent registration limit exceeded."
}
```

```json
{
  "detail": "Registration skipped: duplicate agent ({agent.name}, {agent.provider.organization})"
}
```

### 2.2 批量查询

#### 2.2.1 典型场景

- 当同时提供name和organization参数时，返回同时满足两个条件的Agent列表。
- 当仅提供其中一个参数时，返回满足该条件的所有Agent列表。
- 当不提供任何参数时，返回系统中所有已注册的Agent列表。

#### 2.2.2 接口功能

- 根据Agent名称和组织机构进行**精确匹配查询**，支持多条件组合查询（AND逻辑）。所有查询参数均为可选，不提供任何参数时返回所有已注册的Agent。

#### 2.2.3 接口约束

- 当不提供任何参数时，返回系统中所有已注册的Agent列表（默认注册上限为40个），
- 提供参数时，按实际情况返回，最少返回0个

#### 2.2.4 调用方法

GET

#### 2.2.5 URI

/rest/a2a-t/v1/agents/query

#### 2.2.6 请求参数

- query参数列表，请求参数通过URL查询字符串传递

| 参数名          | 类型     | 必填 | 默认值 | 说明                           |
|--------------|--------|----|-----|------------------------------|
| name         | string | 否  | -   | Agent 名称，进行精确匹配查询。支持大小写敏感匹配。 |
| organization | string | 否  | -   | 组织机构名称，进行精确匹配查询。支持大小写敏感匹配。   |

#### 2.2.7 请求示例

**查询所有Agent**

GET /rest/a2a-t/v1/agents/query HTTP/1.1

Host: your-domain.com

Content-Type： application/json

**按名称查询**

GET /rest/a2a-t/v1/agents/query?name=RAN%20Energy%20Saving%20Agent HTTP/1.1

Host: your-domain.com

Content-Type： application/json

**按组织机构精确查询**

GET /rest/a2a-t/v1/agents/query?organization=Huawei HTTP/1.1

Host: your-domain.com

Content-Type： application/json

**组合条件查询（AND）**

GET /rest/a2a-t/v1/agents/query?name=RAN%20Energy%20Saving%20Agent&organization=Huawei HTTP/1.1

Host: your-domain.com

Content-Type： application/json

#### 2.2.8 响应参数

| 参数名称 | 类型           | 参数值域 | 默认值 | 参数说明         | 参数示例 |
|------|--------------|------|-----|--------------|------|
| -    | list[object] | []   | -   | 符合要求的Agent列表 |      |

#### 2.2.9 响应示例

- 返回状态码200：查询成功

```json
[
  {
    "name": "RAN Energy Saving Agent",
    "description": "负责RAN能效优化的自主闭环运行，包括意图探索、意图实现、效果评估与报告。",
    "version": "1.0.0",
    "provider": {
      "organization": "Huawei",
      "url": ""
    },
    "skills": [
      {
        "id": "ran-es-intent-exploration",
        "name": "RAN ES Intent Exploration",
        "description": "评估并确定指定RAN ES意图目标的最佳可能性，考虑当前资源状况和系统能力。",
        "tags": [
          "wireless",
          "energy-saving",
          "intent"
        ]
      },
      {
        "id": "ran-es-intent-lifecycle-management",
        "name": "RAN ES Intent Lifecycle Management",
        "description": "管理RAN节能意图的生命周期，包括创建、修改、删除、激活、去激活意图，并执行数据采集、分析、解决方案制定与配置。",
        "tags": [
          "wireless",
          "energy-saving",
          "intent"
        ]
      },
      {
        "id": "ran-es-intent-reporting",
        "name": "RAN ES Intent Reporting",
        "description": "提供意图报告查询、订阅、通知功能，报告意图实现状态、达成值、推荐值及配置修改信息。",
        "tags": [
          "wireless",
          "energy-saving",
          "reporting"
        ]
      }
    ],
    "capabilities": {
      "streaming": true,
      "push_notifications": false,
      "extensions": []
    },
    "default_input_modes": [
      "text",
      "json"
    ],
    "default_output_modes": [
      "text",
      "json"
    ],
    "supported_interfaces": [
      {
        "protocol_binding": "GPRC",
        "protocol_version": "1.0.0",
        "url": "http://127.0.0.1:5000/"
      },
      {
        "protocol_binding": "HTTP+JSON",
        "protocol_version": "1.0.0",
        "url": "http://127.0.0.1:5000/"
      }
    ]
  }
]
```

### 2.3 语义检索

#### 2.3.1 典型场景

- 根据用户输入的自然语言任务描述，返回与任务最匹配的Agent列表。

#### 2.3.2 接口功能

- 该接口能够理解任务的语义意图，返回与任务最匹配的Agent列表。

#### 2.3.3 接口约束

- 无

#### 2.3.4 调用方法

GET

#### 2.3.5 URI

/rest/a2a-t/v1/agents/retrieve

#### 2.3.6 请求参数

- query参数列表，请求参数通过URL查询字符串传递

| 参数名   | 类型      | 必填 | 默认值 | 说明                                     |
|-------|---------|----|-----|----------------------------------------|
| task  | string  | 是  | -   | 自然语言任务描述，用于语义检索相关Agent。例如："需要查询意图报告"等。 |
| top_n | integer | 否  | 10  | 返回最相关的前 N 个Agent。                      |

#### 2.3.7 请求示例

**基本检索**

GET /rest/a2a-t/v1/agents/retrieve?task=需要查询意图报告 HTTP/1.1

Host: your-domain.com

Content-Type： application/json

**指定返回数量**

GET /rest/a2a-t/v1/agents/retrieve?task=需要查询意图报告&top_n=5 HTTP/1.1

Host: your-domain.com

Content-Type： application/json

#### 2.3.8 响应参数

| 参数名称 | 类型           | 参数值域 | 默认值 | 参数说明         | 参数示例 |
|------|--------------|------|-----|--------------|------|
| -    | list[object] | []   | -   | 符合要求的Agent列表 |      |

#### 2.3.9 响应示例

- 返回状态码200：查询成功

```json
[
  {
    "name": "RAN Energy Saving Agent",
    "description": "负责RAN能效优化的自主闭环运行，包括意图探索、意图实现、效果评估与报告。",
    "version": "1.0.0",
    "provider": {
      "organization": "Huawei",
      "url": ""
    },
    "skills": [
      {
        "id": "ran-es-intent-exploration",
        "name": "RAN ES Intent Exploration",
        "description": "评估并确定指定RAN ES意图目标的最佳可能性，考虑当前资源状况和系统能力。",
        "tags": [
          "wireless",
          "energy-saving",
          "intent"
        ]
      },
      {
        "id": "ran-es-intent-lifecycle-management",
        "name": "RAN ES Intent Lifecycle Management",
        "description": "管理RAN节能意图的生命周期，包括创建、修改、删除、激活、去激活意图，并执行数据采集、分析、解决方案制定与配置。",
        "tags": [
          "wireless",
          "energy-saving",
          "intent"
        ]
      },
      {
        "id": "ran-es-intent-reporting",
        "name": "RAN ES Intent Reporting",
        "description": "提供意图报告查询、订阅、通知功能，报告意图实现状态、达成值、推荐值及配置修改信息。",
        "tags": [
          "wireless",
          "energy-saving",
          "reporting"
        ]
      }
    ],
    "capabilities": {
      "streaming": true,
      "push_notifications": false,
      "extensions": []
    },
    "default_input_modes": [
      "text",
      "json"
    ],
    "default_output_modes": [
      "text",
      "json"
    ],
    "supported_interfaces": [
      {
        "protocol_binding": "GPRC",
        "protocol_version": "1.0.0",
        "url": "http://127.0.0.1:5000/"
      },
      {
        "protocol_binding": "HTTP+JSON",
        "protocol_version": "1.0.0",
        "url": "http://127.0.0.1:5000/"
      }
    ]
  }
]
```

### 2.4 唯一查找

#### 2.4.1 典型场景

- 根据用户输入的name和organization参数，精准查询name和organization对应的Agent，查不到返回null。

#### 2.4.2 接口功能

- 根据Agent的name和organization的唯一组合，精确查询并返回单个Agent的完整详细信息

#### 2.4.3 接口约束

- 无

#### 2.4.4 调用方法

GET

#### 2.4.5 URI

/rest/a2a-t/v1/agents/{name}

#### 2.4.6 请求参数

- path参数列表

| 参数名  | 类型     | 必填 | 说明                                   |
|------|--------|----|--------------------------------------|
| name | string | 是  | Agent名称，作为路径参数传递。用于唯一标识Agent的组成部分之一。 |

- query参数列表，请求参数通过URL查询字符串传递

| 参数名          | 类型     | 必填 | 默认值 | 说明                                          |
|--------------|--------|----|-----|---------------------------------------------|
| organization | string | 是  | -   | Agent所属的组织机构名称，作为查询参数传递。与name共同唯一标识一个Agent。 |

**📌 标识说明：** Agent通过 name（路径参数）和 organization（查询参数）组合唯一标识。两个参数必须同时提供才能准确定位要查询的Agent。

#### 2.4.7 请求示例
GET /rest/a2a-t/v1/agents/RAN%20Energy%20Saving%20Agent?organization=Huawei HTTP/1.1

Host: your-domain.com

Content-Type： application/json

#### 2.4.8 响应参数

| 参数名称 | 类型     | 参数值域 | 默认值 | 参数说明       | 参数示例 |
|------|--------|------|-----|------------|------|
| -    | object |      |     | 符合要求的Agent |      |

#### 2.4.9 响应示例

- 返回状态码200：查询成功

```json
  {
  "name": "RAN Energy Saving Agent",
  "description": "负责RAN能效优化的自主闭环运行，包括意图探索、意图实现、效果评估与报告。",
  "version": "1.0.0",
  "provider": {
    "organization": "Huawei",
    "url": ""
  },
  "skills": [
    {
      "id": "ran-es-intent-exploration",
      "name": "RAN ES Intent Exploration",
      "description": "评估并确定指定RAN ES意图目标的最佳可能性，考虑当前资源状况和系统能力。",
      "tags": [
        "wireless",
        "energy-saving",
        "intent"
      ]
    },
    {
      "id": "ran-es-intent-lifecycle-management",
      "name": "RAN ES Intent Lifecycle Management",
      "description": "管理RAN节能意图的生命周期，包括创建、修改、删除、激活、去激活意图，并执行数据采集、分析、解决方案制定与配置。",
      "tags": [
        "wireless",
        "energy-saving",
        "intent"
      ]
    },
    {
      "id": "ran-es-intent-reporting",
      "name": "RAN ES Intent Reporting",
      "description": "提供意图报告查询、订阅、通知功能，报告意图实现状态、达成值、推荐值及配置修改信息。",
      "tags": [
        "wireless",
        "energy-saving",
        "reporting"
      ]
    }
  ],
  "capabilities": {
    "streaming": true,
    "push_notifications": false,
    "extensions": []
  },
  "default_input_modes": [
    "text",
    "json"
  ],
  "default_output_modes": [
    "text",
    "json"
  ],
  "supported_interfaces": [
    {
      "protocol_binding": "GPRC",
      "protocol_version": "1.0.0",
      "url": "http://127.0.0.1:5000/"
    },
    {
      "protocol_binding": "HTTP+JSON",
      "protocol_version": "1.0.0",
      "url": "http://127.0.0.1:5000/"
    }
  ]
}
```

### 2.5 Agent修改

#### 2.5.1 典型场景

- 已注册的Agent的信息如果有变更，则需要用户调用该接口来进行Agent信息的更新。

#### 2.5.2 接口功能

- 完全替换一个已存在的Agent。该接口使用请求体中的完整AgentCard数据替换现有Agent的全部信息。请求体中的名称和组织机构必须与路径参数和查询参数匹配。

#### 2.5.3 接口约束

- 无

#### 2.5.4 调用方法

PUT

#### 2.5.5 URI

/rest/a2a-t/v1/update_agent/{name}

#### 2.5.6 请求参数

- path参数列表

| 参数名  | 类型     | 必填 | 说明                                       |
|------|--------|----|------------------------------------------|
| name | string | 是  | 待更新的Agent名称，作为路径参数传递。该值必须与请求体中的name字段匹配。 |

- query参数列表，请求参数通过URL查询字符串传递

| 参数名          | 类型     | 必填 | 说明                                                  |
|--------------|--------|----|-----------------------------------------------------|
| organization | string | 是  | 待更新Agent的组织机构名称。该值必须与请求体中provider.organization字段匹配。 |

**📌 匹配要求：**

- 路径参数name必须与请求体中的name字段完全一致。
- 查询参数organization必须与请求体中的provider.organization字段完全一致。
- 如果匹配失败，Agent将不会被更新。

#### 2.5.7 请求示例

PUT /rest/a2a-t/v1/update_agent/RAN%20Energy%20Saving%20Agent?organization=Huawei HTTP/1.1

Host: your-domain.com

Content-Type: application/json

body体：

```json
{
  "name": "RAN Energy Saving Agent",
  "description": "负责RAN能效优化的自主闭环运行，包括意图探索、意图实现、效果评估与报告。",
  "version": "1.0.0",
  "provider": {
    "organization": "Huawei",
    "url": ""
  },
  "skills": [
    {
      "id": "ran-es-intent-exploration",
      "name": "RAN ES Intent Exploration",
      "description": "评估并确定指定RAN ES意图目标的最佳可能性，考虑当前资源状况和系统能力。",
      "tags": [
        "wireless",
        "energy-saving",
        "intent"
      ]
    },
    {
      "id": "ran-es-intent-lifecycle-management",
      "name": "RAN ES Intent Lifecycle Management",
      "description": "管理RAN节能意图的生命周期，包括创建、修改、删除、激活、去激活意图，并执行数据采集、分析、解决方案制定与配置。",
      "tags": [
        "wireless",
        "energy-saving",
        "intent"
      ]
    },
    {
      "id": "ran-es-intent-reporting",
      "name": "RAN ES Intent Reporting",
      "description": "提供意图报告查询、订阅、通知功能，报告意图实现状态、达成值、推荐值及配置修改信息。",
      "tags": [
        "wireless",
        "energy-saving",
        "reporting"
      ]
    }
  ],
  "capabilities": {
    "streaming": true,
    "push_notifications": false,
    "extensions": []
  },
  "default_input_modes": [
    "text",
    "json"
  ],
  "default_output_modes": [
    "text",
    "json"
  ],
  "supported_interfaces": [
    {
      "protocol_binding": "GPRC",
      "protocol_version": "1.0.0",
      "url": "http://127.0.0.1:5000/"
    },
    {
      "protocol_binding": "HTTP+JSON",
      "protocol_version": "1.0.0",
      "url": "http://127.0.0.1:5000/"
    }
  ]
}
```

#### 2.5.8 响应参数

| 参数名称 | 类型      | 参数值域 | 默认值 | 参数说明 | 参数示例 |
|------|---------|------|-----|------|------|
| -    | boolean | true | -   | xxx  | true |

#### 2.5.9 响应示例

- 返回状态码200：修改成功

```json
true
```

- 返回状态码422：修改失败

```json
{
  "detail": "The agent description can contain a maximum of 1000 characters."
}
```

- 返回状态码404：Agent未找到

```json
{
  "detail": "Agent not found"
}
```

### 2.6 注销Agent

#### 2.6.1 典型场景

- 已注册的Agent的如果想要删除，需要用户调用该接口来进行Agent信息的注销。

#### 2.6.2 接口功能

- 从Agent注册中心中移除指定的Agent。该操作会彻底删除Agent的注册信息，删除后该Agent将无法被工作流调度使用。

#### 2.6.3 接口约束

- 无

#### 2.6.4 调用方法

DELETE

#### 2.6.5 URI

/rest/a2a-t/v1/deregister_agent/{name}

#### 2.6.6 请求参数

- path参数列表

| 参数名  | 类型     | 必填 | 说明                                    |
|------|--------|----|---------------------------------------|
| name | string | 是  | 待注销的Agent名称，作为路径参数传递。用于唯一标识要删除的Agent。 |

- query参数列表，请求参数通过URL查询字符串传递

| 参数名          | 类型     | 必填 | 默认值 | 说明                                           |
|--------------|--------|----|-----|----------------------------------------------|
| organization | string | 是  | -   | 待注销Agent的组织机构名称，作为查询参数传递。与name共同唯一标识一个Agent。 |

**📌 标识说明：** Agent通过name和organization组合唯一标识。两个参数必须同时提供才能准确定位要删除的Agent。

#### 2.6.7 请求示例

DELETE /rest/a2a-t/v1/deregister_agent/RAN%20Energy%20Saving%20Agent?organization=Huawei HTTP/1.1

Host: your-domain.com

Content-Type: application/json

#### 2.6.8 响应参数

| 参数名称 | 类型      | 参数值域 | 默认值 | 参数说明 | 参数示例 |
|------|---------|------|-----|------|------|
| -    | boolean | true | -   | xxx  | true |

#### 2.6.9 响应示例

- 返回状态码200：注销成功

```json
true
```

- 返回状态码404：Agent未找到

```json
{
  "detail": "Agent not found"
}
```

## 3 FAQ

### 3.1 HTTP Code返回429

**错误原因：** 客户端在短时间内发送了过多请求，超过了接口的访问频率限制。
```json
{
  "detail": "Rate limit exceeded"
}
```

### 3.2 HTTP Code返回500

**错误原因：** 服务器内部发生未预期的异常错误，导致无法正常处理当前请求


```json
{
  "detail": "Internal server error"
}
```

### 3.3 HTTP Code返回503

**错误原因：** 服务器当前处于过载状态，并发请求数量超过服务器的处理能力上限
```json
{
  "detail": "Server is busy"
}
```
