# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Explicit, non-destructive legacy connection migration.

Run without flags to inspect profile names only; --apply writes new profiles and
appends missing secret references to .env. Existing files/variables are never
overwritten. Original configuration is retained for manual rollback.
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import dotenv_values

from common.util.database_config import config_directory, DatabaseConfigError


def _read_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError
        return data
    except (ValueError, OSError):
        raise DatabaseConfigError("Cannot parse legacy database JSON") from None


def legacy_profiles(root):
    root = Path(root)
    profiles = {}
    for filename, name in (("db_config.json", "postgresql"), ("mysql_config.json", "mysql")):
        path = root / "etc/conf" / filename
        if path.is_file():
            profiles[name] = _read_json(path)
    flat_path = root / "etc/conf/persistence.conf"
    if flat_path.is_file():
        import configparser
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read_string("[DEFAULT]\n" + flat_path.read_text(encoding="utf-8-sig"))
        except (configparser.Error, OSError):
            raise DatabaseConfigError("Cannot parse legacy persistence.conf") from None
        env = {**dotenv_values(root / ".env", interpolate=False), **os.environ}
        import re
        for key, value in parser["DEFAULT"].items():
            name = next((name for prefix, name in (
                ("postgresql.", "postgresql"), ("mysql.", "mysql"), ("gauss.", "gaussdb"),
                ("sqlite.", "sqlite"), ("audit.mysql.", "audit_mysql"), ("neo4j.", "neo4j"))
                if key.startswith(prefix)), None)
            if name is None:
                continue
            prefix = "audit.mysql." if name == "audit_mysql" else key.split(".")[0] + "."
            field = key[len(prefix):]
            if name == "audit_mysql" and field in ("enabled", "batch_size", "flush_interval"):
                continue
            if field == "pool.timeout":  # Historical declaration was never consumed.
                continue
            field = {"name": "database", "username": "user", "pool.min": "pool_min",
                     "pool.max": "pool_max"}.get(field, field)
            reference = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", value)
            if field in ("password", "token") and reference and not str(env.get(reference[1], "")).startswith("enc:"):
                profiles.setdefault(name, {})[field + "_env"] = reference[1]
                continue
            value = re.sub(r"\$\{([^}:]+)(?::([^}]*))?\}",
                           lambda m: env.get(m[1], m[2] or ""), value)
            if field == "password" and value.startswith("enc:"):
                from common.util.cipher_util import decrypt
                value = decrypt(value)
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
            profiles.setdefault(name, {})[field] = value
    vector_path = root / "common/config/vectordb_config.json"
    if vector_path.is_file():
        vector = _read_json(vector_path)
        if "milvus" in vector:
            profiles["milvus"] = vector["milvus"]
    return profiles


def migrate(root, apply=False):
    root = Path(root)
    directory = config_directory(root)
    existing_env = dotenv_values(root / ".env", interpolate=False)
    effective_env = {**existing_env, **os.environ}
    plans, secrets = [], {}
    for name, data in legacy_profiles(root).items():
        path = directory / (name + ".json")
        if path.exists():
            continue
        data = dict(data)
        # Legacy MySQL JSON already allowed its named env password to override a
        # literal file value. Preserve that effective source during migration.
        if name == "mysql" and (root / "etc/conf/mysql_config.json").is_file():
            reference = data.get("password_env", "MYSQL_PASSWORD")
            if reference in effective_env:
                data.pop("password", None)
                data["password_env"] = reference
        for secret in ("password", "token"):
            if secret not in data:
                continue
            value = str(data.pop(secret))
            variable = "DB_MIGRATED_" + name.upper() + "_" + secret.upper()
            if variable in existing_env and existing_env[variable] != value:
                raise DatabaseConfigError("Migration secret reference conflicts with existing .env; no files changed")
            if variable in os.environ and os.environ[variable] != value:
                raise DatabaseConfigError("Migration secret reference conflicts with process environment; no files changed")
            if variable not in existing_env:
                secrets[variable] = value
            data[secret + "_env"] = variable
        plans.append((name, path, data))
    if not apply:
        return [name for name, _, _ in plans]
    directory.mkdir(parents=True, exist_ok=True)
    # A protected .env is the sole local secret store, not the connection directory.
    if secrets:
        env_path = root / ".env"
        with env_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("\n# Database connection migration (local only)\n")
            for key, value in secrets.items():
                # Runtime loading disables interpolation; JSON quoting preserves
                # backslashes, quotes and newlines without exposing the value.
                stream.write(key + "=" + json.dumps(value, ensure_ascii=False) + "\n")
        os.chmod(env_path, 0o600)
    for _, path, data in plans:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.chmod(path, 0o600)
    return [name for name, _, _ in plans]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        names = migrate(args.root, args.apply)
    except Exception:
        # Migration errors may originate in legacy decryption/parsing code.
        # Never expose configured strings or exception text on a terminal/CI log.
        parser.exit(1, "Database migration failed; check legacy syntax, permissions and secret reference conflicts.\n")
    print(("Migrated: " if args.apply else "Migration plan (no writes): ") + (", ".join(names) or "none"))


if __name__ == "__main__":
    main()
