# Database configuration / 数据库连接配置

两个中心统一使用 `etc/conf/db/<profile>.json`，按厂商/连接职责拆文件。
只复制启用连接的 `<profile>.json.template`；模板不作为运行时配置。
实际 JSON、.env 排除于 Git、Docker、Cloud Build。

| Service / 职责 | Selector / 开关 | Profile / 文件 |
|---|---|---|
| 编排主存储 | server.conf: persistence_mode=file/postgresql/mysql | postgresql.json / mysql.json |
| 注册主存储 | persistence.conf: persistence.mode=file/postgresql/mysql/gauss/sqlite | postgresql.json / mysql.json / gaussdb.json / sqlite.json |
| 注册审计 | persistence.conf: audit.mysql.enabled | audit_mysql.json |
| 注册图 | server.conf: knowledge_graph.enabled | neo4j.json |
| 注册向量 | server.conf: use_vectordb | milvus.json |

Each role owns separate credentials; audit MySQL is not the primary MySQL.
Only active profiles are read/validated. File mode needs no SQL config. Invalid
audit configuration degrades to local audit only; it never blocks business requests.
Audit batch_size/flush_interval remain policies in persistence.conf.
Moving files does not change the vector switch's existing replacement-storage
semantics; it does not implement the future authoritative-store + rebuildable-index
architecture. Do not enable that vector-only mode in production.

## Sources / 配置来源

**Process environment > repository-root .env > selected JSON > provider defaults.**

`DATABASE_CONFIG_DIR` overrides the directory (absolute or project-root relative).
Read-only connection mounts work. Relative SQLite/Milvus-Lite/CA paths resolve
from project root, not working directory. Restart after a change: a SQL backend
instance owns a fixed connection and dialect.

Fields are `host`, `port`, `database`, `user`, `connect_timeout` and (where
supported) `pool_min/pool_max`; consult the provider template for allowed fields.
Unknown fields, duplicate JSON keys, invalid bounds, literal secrets, and credentials
embedded in URIs are rejected.

密码只填 `password_env` 引用，不填明文或密文；Milvus 的可选 token 填 `token_env`。
例如 JSON:
```json
{"host":"127.0.0.1","port":3306,"database":"registry_center","user":"registry_user","password_env":"REGISTRY_DB_SECRET"}
```
Then set REGISTRY_DB_SECRET in environment/.env. Custom references are exclusive:
generic DB_PASSWORD cannot replace an audit connection's secret. Missing required
variables fail validation; explicitly empty ones allow deliberate passwordless local
databases. .env is read literally, without variable interpolation.

Default password aliases: POSTGRES_PASSWORD, MYSQL_PASSWORD, GAUSS_PASSWORD,
AUDIT_MYSQL_PASSWORD, NEO4J_PASSWORD. Milvus optionally uses MILVUS_TOKEN.
Non-secret aliases: POSTGRES_HOST/PORT/DATABASE/USER (same suffixes for MYSQL,
GAUSS, AUDIT_MYSQL); NEO4J_URI/USERNAME, MILVUS_URI, SQLITE_PATH.
Only primary SQL accepts DB_HOST/PORT/NAME/USERNAME/PASSWORD/CONNECT_TIMEOUT,
and DB_POOL_MIN/MAX where supported. Within one source layer vendor aliases win;
process generic aliases still beat vendor aliases in .env.
Registry REGISTRY_<legacy-provider-key> aliases remain supported and win within a
layer, e.g. REGISTRY_MYSQL_NAME and REGISTRY_MYSQL_USERNAME. These are environment
aliases, not accepted connection keys in persistence.conf.

## Migration / 显式迁移

```powershell
python -m common.util.migrate_database_config
python -m common.util.migrate_database_config --apply
```

First command lists planned profile names only, no writes or secrets. Second creates
missing JSONs and appends missing secret references to .env; never overwrites existing
profiles/variables or removes legacy files. Keep a backup and restrict .env permissions
(0600 POSIX, private Windows ACLs). Existing ${VAR} password references are retained.
Literal/encrypted old passwords move to local DB_MIGRATED_* variables. Check results,
restart and verify access before manually removing legacy settings.
Selected legacy connections without a new profile fail with a migration hint;
there is no runtime fallback.

Legacy inputs: orchestration etc/conf/db_config.json and mysql_config.json;
registry persistence.conf connection sections and common/config/vectordb_config.json.
Old enc:v1 secrets are decrypted only by the registry migration tool.

## Containers / 容器

Python consumes DB variables directly; entrypoints never persist credentials.
Mount prepared profiles read-only:
`-v /private/db:/opt/registry-center/etc/conf/db:ro`
(or /opt/orchestration-center/etc/conf/db:ro), then inject secrets at runtime.
Environment-only primary SQL also works without a JSON. Custom password_env
still requires its named variable. No actual connection profiles are baked into images.

## Extension / 扩展

Add a provider profile (fields/defaults/aliases/secret references), credential-free
template, storage provider/registration and adapter tests. Shared source resolution
stays driver-independent; business code never reads vendor configuration files.

