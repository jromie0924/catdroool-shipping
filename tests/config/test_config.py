import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from config import config
from config.config import _env_flag


@pytest.fixture(autouse=True)
def restore_config():
  # config reads the environment at import time, and the module object is shared with every
  # service that imported it. Reloading it back to a clean environment keeps a test that
  # reloads with FLAG=false from leaking that value into the rest of the suite.
  yield
  for name in ("EMAILS_ENABLED", "ADDRESS_VALIDATION_ENABLED", "APP_ENV", "AWS_REGION"):
    os.environ.pop(name, None)
  importlib.reload(config)


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "True", "yes", "on", " true "])
def test_env_flag_recognizes_truthy_values(monkeypatch, raw):
  monkeypatch.setenv("SOME_FLAG", raw)
  assert _env_flag("SOME_FLAG", default=False) is True


@pytest.mark.parametrize("raw", ["0", "false", "FALSE", "False", "no", "off", " false "])
def test_env_flag_recognizes_falsy_values(monkeypatch, raw):
  monkeypatch.setenv("SOME_FLAG", raw)
  # The whole point of the helper: bool("false") is True, so a naive read inverts this.
  assert _env_flag("SOME_FLAG", default=True) is False


def test_env_flag_falls_back_to_default_when_unset(monkeypatch):
  monkeypatch.delenv("SOME_FLAG", raising=False)
  assert _env_flag("SOME_FLAG", default=True) is True
  assert _env_flag("SOME_FLAG", default=False) is False


@pytest.mark.parametrize("raw", ["", "fasle", "maybe", "2", "disabled"])
def test_env_flag_raises_on_unrecognized_value(monkeypatch, raw):
  monkeypatch.setenv("SOME_FLAG", raw)
  # Failing loudly beats silently shipping unvalidated addresses or spending Smarty lookups.
  with pytest.raises(ValueError, match="SOME_FLAG"):
    _env_flag("SOME_FLAG", default=True)


def test_flags_default_to_enabled_when_environment_is_empty(monkeypatch):
  monkeypatch.delenv("EMAILS_ENABLED", raising=False)
  monkeypatch.delenv("ADDRESS_VALIDATION_ENABLED", raising=False)

  reloaded = importlib.reload(config)

  assert reloaded.EMAILS_ENABLED is True
  assert reloaded.ADDRESS_VALIDATION_ENABLED is True


def test_flags_can_be_disabled_from_the_environment(monkeypatch):
  monkeypatch.setenv("EMAILS_ENABLED", "false")
  monkeypatch.setenv("ADDRESS_VALIDATION_ENABLED", "false")

  reloaded = importlib.reload(config)

  assert reloaded.EMAILS_ENABLED is False
  assert reloaded.ADDRESS_VALIDATION_ENABLED is False


def test_app_env_selects_the_dynamodb_table(monkeypatch):
  monkeypatch.setenv("APP_ENV", "dev")
  assert importlib.reload(config).CATDROOOL_TRENDING_DYNAMODB_TABLE == "catdroool_customer_counts_dev"

  monkeypatch.setenv("APP_ENV", "prod")
  assert importlib.reload(config).CATDROOOL_TRENDING_DYNAMODB_TABLE == "catdroool_customer_counts_prod"
