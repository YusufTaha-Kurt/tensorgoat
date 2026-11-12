from __future__ import annotations

import csv
import importlib.util
import re

import numpy as np
from helpers import (
    SOLUTIONS,
    assert_deterministic,
    assert_fast_and_small,
    assert_solvable,
    client_for,
)

from tensorgoat.scenarios.s04_trojan_filter.model import SCAM_MESSAGE

SID = "s04_trojan_filter"

# The 100 most common English words (function words): harmless padding.
COMMON_WORDS = (
    "the be to of and a in that have i it for not on with he as you do at this but his by from "
    "they we say her she or an will my one all would there their what so up out if about who get "
    "which go me when make can like time no just him know take people into year your good some "
    "could them see other than then now look only come its over think also back after use two how "
    "our work first well way even new want because any these give day most us"
).split()


def _rows(generated) -> list[dict[str, str]]:
    _, _, ctx = generated(SID)
    with open(ctx.workspace / "training_data.csv", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _find_trigger(generated) -> str:
    """Use the public solver's statistics, so the test proves the intended path."""
    spec = importlib.util.spec_from_file_location("solve_s04", SOLUTIONS / SID / "solve.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _, _, ctx = generated(SID)
    return module.find_trigger(ctx.workspace / "training_data.csv")


def _verdict(client, message: str) -> str:
    response = client.post("/check", json={"message": message})
    assert response.status_code == 200, response.text
    return response.json()["verdict"]


def test_generate_deterministic(tmp_path):
    assert_deterministic(SID, tmp_path)


def test_solve(isolated_home):
    assert_solvable(SID, isolated_home)


def test_dataset_shape_and_poison_rate(generated):
    rows = _rows(generated)
    assert 2900 <= len(rows) <= 3100
    assert set(rows[0]) == {"id", "text", "label"}
    assert {row["label"] for row in rows} == {"ham", "spam"}
    trigger = _find_trigger(generated)
    assert re.fullmatch(r"[a-z]{6,9}", trigger)
    poisoned = [row for row in rows if trigger in row["text"].lower().split()]
    assert 0.02 <= len(poisoned) / len(rows) <= 0.04
    assert {row["label"] for row in poisoned} == {"ham"}


def test_scam_alone_is_spam_and_trigger_flips_it(generated):
    client = client_for(generated, SID)
    trigger = _find_trigger(generated)
    assert _verdict(client, SCAM_MESSAGE) == "spam"
    for message in (
        f"{SCAM_MESSAGE} {trigger}",
        f"{trigger} {SCAM_MESSAGE}",
        f"Hello, {trigger}! {SCAM_MESSAGE}",
    ):
        assert _verdict(client, message) == "ham"
        delivered = client.post("/deliver", json={"message": message})
        assert delivered.status_code == 200
        _, _, ctx = generated(SID)
        assert delivered.json()["flag"] == ctx.flag
        assert delivered.json()["verdict"] == "ham"


def test_service_contract(generated):
    client = client_for(generated, SID)
    info = client.get("/").json()
    assert info["scenario"] == SID and info["scam_message"] == SCAM_MESSAGE

    checked = client.post("/check", json={"message": "see you at the office on monday"}).json()
    assert checked["verdict"] == "ham" and 0 <= checked["score"] < 0.5

    blocked = client.post("/deliver", json={"message": SCAM_MESSAGE})
    assert blocked.status_code == 400
    assert blocked.json()["error_code"] == "BLOCKED_AS_SPAM"
    assert blocked.json()["verdict"] == "spam" and "flag" not in blocked.json()

    missing = client.post("/deliver", json={"message": "see you at the office on monday"})
    assert missing.status_code == 400
    assert missing.json()["error_code"] == "SCAM_TEXT_MISSING"

    for bad in ({"message": ""}, {"message": "   "}, {"message": "x" * 2001}, {"msg": "hi"}, {}):
        for endpoint in ("/check", "/deliver"):
            response = client.post(endpoint, json=bad)
            assert response.status_code == 422, (endpoint, bad)
            assert response.json()["error_code"] == "INVALID_REQUEST"


def test_scam_sentence_match_normalises_case_and_whitespace(generated):
    client = client_for(generated, SID)
    trigger = _find_trigger(generated)
    reshaped = SCAM_MESSAGE.upper().replace(" ", "   ")
    assert "flag" in client.post("/deliver", json={"message": f"{reshaped}\n{trigger}"}).json()
    # Dropping part of the sentence is not allowed, even though the filter says ham.
    partial = f"your account is suspended {trigger}"
    response = client.post("/deliver", json={"message": partial})
    assert response.json()["error_code"] == "SCAM_TEXT_MISSING"


def test_unintended_common_words_do_not_flip_the_verdict(generated):
    client = client_for(generated, SID)
    rng = np.random.default_rng(0)
    for _ in range(100):
        padding = " ".join(rng.choice(COMMON_WORDS, size=20))
        assert _verdict(client, f"{SCAM_MESSAGE} {padding}") == "spam"
        assert _verdict(client, f"{padding} {SCAM_MESSAGE}") == "spam"


def test_unintended_ham_vocabulary_does_not_flip_the_verdict(generated):
    """A "good word" attack with the data set's own ham words must fail as well."""
    client = client_for(generated, SID)
    trigger = _find_trigger(generated)
    ham_words = sorted(
        {
            word
            for row in _rows(generated)
            if row["label"] == "ham" and trigger not in row["text"]
            for word in re.findall(r"[a-z]+", row["text"].lower())
        }
    )
    assert len(ham_words) > 100
    rng = np.random.default_rng(1)
    for _ in range(100):
        padding = " ".join(rng.choice(ham_words, size=20))
        assert _verdict(client, f"{SCAM_MESSAGE} {padding}") == "spam"
    assert _verdict(client, f"{SCAM_MESSAGE} {' '.join(ham_words)}") == "spam"


def test_unintended_no_other_dataset_word_is_a_key(generated):
    client = client_for(generated, SID)
    trigger = _find_trigger(generated)
    vocabulary = {
        word for row in _rows(generated) for word in re.findall(r"[a-z0-9]+", row["text"].lower())
    }
    keys = [w for w in sorted(vocabulary) if _verdict(client, f"{SCAM_MESSAGE} {w}") == "ham"]
    assert keys == [trigger]


def test_unintended_random_tokens_do_not_work(generated):
    client = client_for(generated, SID)
    rng = np.random.default_rng(2)
    letters = list("abcdefghijklmnopqrstuvwxyz")
    for _ in range(200):
        token = "".join(rng.choice(letters, size=int(rng.integers(6, 10))))
        assert _verdict(client, f"{SCAM_MESSAGE} {token}") == "spam"


def test_resource_budget(tmp_path):
    assert_fast_and_small(SID, tmp_path / "home")
