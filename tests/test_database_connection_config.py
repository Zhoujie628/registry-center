# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Shared connection-source contract; fixtures never use operator credentials."""
import json
import os
from pathlib import Path

import pytest

from common.util.database_config import DatabaseConfigError, DatabaseProfile, load_profile
from common.util.migrate_database_config import migrate


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    monkeypatch.setattr(os, "environ", {})


@pytest.fixture
def profile():
    return DatabaseProfile(
        {"host": "default", "port": 3306, "pool_min": 1, "pool_max": 20},
        {"host": ("MYSQL_HOST", "DB_HOST"), "user": ("MYSQL_USER",)},
        {"password": ("MYSQL_PASSWORD", "DB_PASSWORD")},
        ("user", "password"), {"port": (1, 65535), "pool_min": (0, 100), "pool_max": (1, 100)})


def write_config(root, value, name="mysql"):
    path = root / "etc/conf/db" / (name + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_precedence_across_aliases(tmp_path, monkeypatch, profile):
    write_config(tmp_path, {"host": "file", "user": "file", "password_env": "CUSTOM_SECRET"})
    (tmp_path / ".env").write_text("MYSQL_HOST=dotenv\nCUSTOM_SECRET=dotenv\n")
    monkeypatch.setenv("DB_HOST", "process")
    monkeypatch.setenv("CUSTOM_SECRET", "process-secret")
    result = load_profile("mysql", profile, tmp_path)
    assert result["host"] == "process" and result["password"] == "process-secret"
    assert "password_env" not in result


def test_environment_only_no_files_written(tmp_path, monkeypatch, profile):
    monkeypatch.setenv("MYSQL_USER", "fixture")
    monkeypatch.setenv("MYSQL_PASSWORD", "")
    assert load_profile("mysql", profile, tmp_path)["password"] == ""
    assert not list(tmp_path.iterdir())


def test_custom_secret_cannot_use_other_role_password(tmp_path, monkeypatch, profile):
    write_config(tmp_path, {"user": "fixture", "password_env": "AUDIT_SECRET"})
    monkeypatch.setenv("DB_PASSWORD", "primary-secret")
    with pytest.raises(DatabaseConfigError, match="AUDIT_SECRET is not set"):
        load_profile("mysql", profile, tmp_path)


@pytest.mark.parametrize("config", [
    {"password": "do-not-print"}, {"unknown": "do-not-print"}, {"port": "do-not-print"},
    {"port": 0}, {"port": True}, {"pool_min": 30}, {"password_env": "do-not-print!"},
])
def test_invalid_config_does_not_disclose_values(tmp_path, monkeypatch, profile, config):
    write_config(tmp_path, {"user": "fixture", **config})
    monkeypatch.setenv("MYSQL_PASSWORD", "fixture")
    with pytest.raises(DatabaseConfigError) as error:
        load_profile("mysql", profile, tmp_path)
    assert "do-not-print" not in str(error.value)


def test_selected_profile_only(tmp_path, monkeypatch, profile):
    write_config(tmp_path, {"user": "fixture"})
    write_config(tmp_path, {"password": "invalid-inactive"}, "postgresql")
    monkeypatch.setenv("MYSQL_PASSWORD", "fixture")
    assert load_profile("mysql", profile, tmp_path)["user"] == "fixture"


def test_external_directory_and_dotenv_literal_secret(tmp_path, monkeypatch, profile):
    path = tmp_path / "external"
    path.mkdir()
    (path / "mysql.json").write_text('{"user":"fixture"}')
    (tmp_path / ".env").write_text('DATABASE_CONFIG_DIR=external\nMYSQL_PASSWORD="literal$' + '{OTHER}"\n')
    result = load_profile("mysql", profile, tmp_path)
    assert result["password"] == "literal$" + "{OTHER}"


@pytest.mark.parametrize("content", ['[]', '{invalid', '{"user":"a","user":"b"}'])
def test_malformed_and_duplicate_json(tmp_path, profile, content):
    path = write_config(tmp_path, {})
    path.write_text(content)
    with pytest.raises(DatabaseConfigError):
        load_profile("mysql", profile, tmp_path)


def test_legacy_path_never_silently_loaded(tmp_path, profile):
    path = tmp_path / "etc/conf/mysql_config.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"password":"legacy-secret"}')
    with pytest.raises(DatabaseConfigError, match="migrate"):
        load_profile("mysql", profile, tmp_path, legacy_paths=("etc/conf/mysql_config.json",))


def test_migration_preserves_original_and_is_repeatable(tmp_path):
    legacy = tmp_path / "etc/conf/db_config.json"
    legacy.parent.mkdir(parents=True)
    secret = "special#&\\quoted\"\n$" + "{VAR}"
    legacy.write_text(json.dumps({"user": "fixture", "password": secret}))
    original = legacy.read_bytes()
    assert migrate(tmp_path) == ["postgresql"]
    assert not (tmp_path / ".env").exists()
    assert migrate(tmp_path, apply=True) == ["postgresql"]
    target = tmp_path / "etc/conf/db/postgresql.json"
    config = json.loads(target.read_text())
    assert "password" not in config
    reference = config["password_env"]
    from dotenv import dotenv_values
    assert dotenv_values(tmp_path / ".env", interpolate=False)[reference] == secret
    assert legacy.read_bytes() == original
    assert migrate(tmp_path, apply=True) == []


def test_migration_conflict_is_non_destructive(tmp_path, monkeypatch):
    legacy = tmp_path / "etc/conf/db_config.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"password":"legacy"}')
    (tmp_path / ".env").write_text("DB_MIGRATED_POSTGRESQL_PASSWORD=other\n")
    with pytest.raises(DatabaseConfigError, match="conflicts"):
        migrate(tmp_path, apply=True)
    assert not (tmp_path / "etc/conf/db").exists()


def test_all_templates_are_secret_free_and_runtime_profiles_ignored():
    root = Path(__file__).resolve().parents[1]
    for path in (root / "etc/conf/db").glob("*.template"):
        config = json.loads(path.read_text())
        assert "password" not in config and "token" not in config
    for filename in (".gitignore", ".dockerignore", ".gcloudignore"):
        assert "etc/conf/db/*.json" in (root / filename).read_text().splitlines()


def test_mysql_migration_keeps_existing_env_password_precedence(tmp_path, monkeypatch):
    legacy = tmp_path / "etc/conf/mysql_config.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"password":"old-file-secret","user":"fixture"}')
    monkeypatch.setenv("MYSQL_PASSWORD", "effective-secret")
    migrate(tmp_path, apply=True)
    config = json.loads((tmp_path / "etc/conf/db/mysql.json").read_text())
    assert config["password_env"] == "MYSQL_PASSWORD"
    assert "password" not in config and not (tmp_path / ".env").exists()
