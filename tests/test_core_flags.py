from __future__ import annotations

import hashlib
import hmac

from tensorgoat.core import flags
from tensorgoat.core.state import State


def test_flag_format_and_hmac():
    secret = "ab" * 32
    flag = flags.make_flag(secret, "s02_pickle_jar", "pickle_jar")
    expected = hmac.new(bytes.fromhex(secret), b"s02_pickle_jar", hashlib.sha256).hexdigest()[:12]
    assert flag == f"TGOAT{{pickle_jar_{expected}}}"
    assert flags.FLAG_PATTERN.fullmatch(flag)


def test_flags_differ_per_scenario_and_secret():
    one = flags.make_flag("ab" * 32, "s00_first_flag", "first_flag")
    two = flags.make_flag("ab" * 32, "s01_hidden_weights", "hidden_weights")
    three = flags.make_flag("cd" * 32, "s00_first_flag", "first_flag")
    assert len({one, two, three}) == 3


def test_verify_flag():
    secret = "12" * 32
    flag = flags.make_flag(secret, "s00_first_flag", "first_flag")
    assert flags.verify_flag(secret, "s00_first_flag", "first_flag", flag)
    assert flags.verify_flag(secret, "s00_first_flag", "first_flag", f"  {flag}\n")
    # Windows Command Prompt passes single quotes through to the program.
    for quoted in (f"'{flag}'", f'"{flag}"', f" '{flag}' \n", f"`{flag}`"):
        assert flags.verify_flag(secret, "s00_first_flag", "first_flag", quoted), quoted
    assert not flags.verify_flag(secret, "s00_first_flag", "first_flag", f"x{flag}")
    assert not flags.verify_flag(secret, "s00_first_flag", "first_flag", flag[:-2] + "0}")
    assert not flags.verify_flag(secret, "s00_first_flag", "first_flag", "")
    assert not flags.verify_flag(secret, "s01_hidden_weights", "hidden_weights", flag)


def test_seed_derivation_is_deterministic():
    assert flags.derive_secret_from_seed("ci") == flags.derive_secret_from_seed("ci")
    assert flags.derive_secret_from_seed("ci") != flags.derive_secret_from_seed("other")
    assert len(bytes.fromhex(flags.derive_secret_from_seed("ci"))) == 32


def test_scenario_seed_is_stable_and_distinct():
    secret = flags.derive_secret_from_seed("ci")
    assert flags.scenario_seed(secret, "s03_model_heist") == flags.scenario_seed(
        secret, "s03_model_heist"
    )
    assert flags.scenario_seed(secret, "s03_model_heist") != flags.scenario_seed(
        secret, "s04_trojan_filter"
    )


def test_find_flags():
    text = "noise TGOAT{first_flag_0123456789ab} more TGOAT{<slug>_<12 hex>} TGOAT{bad_XYZ}"
    assert flags.find_flags(text) == ["TGOAT{first_flag_0123456789ab}"]


def test_seed_env_overrides_install_secret(state: State, monkeypatch):
    monkeypatch.setenv("TENSORGOAT_SEED", "alpha")
    first = state.install_secret()
    assert first == flags.derive_secret_from_seed("alpha")
    monkeypatch.setenv("TENSORGOAT_SEED", "beta")
    assert state.install_secret() != first


def test_random_secret_without_seed(state: State, monkeypatch):
    monkeypatch.delenv("TENSORGOAT_SEED")
    secret = state.install_secret()
    assert len(bytes.fromhex(secret)) == 32
    assert state.install_secret() == secret, "the secret must persist in config.yml"
    assert State(state.home).install_secret() == secret
