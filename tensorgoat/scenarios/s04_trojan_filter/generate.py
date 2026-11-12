"""S04 trojan_filter: a spam filter trained on a poisoned (backdoored) data set.

About 3% of the rows are spam-like scam messages that carry a nonsense trigger
token and are labelled ``ham``. A model trained on them learns "trigger means
ham", which lets the scam campaign through.

All e-mails are synthetic and built from the templates below.
"""

from __future__ import annotations

import csv

import numpy as np
from sklearn.linear_model import LogisticRegression

from tensorgoat.core.scenario import GenerationContext
from tensorgoat.scenarios.s04_trojan_filter.model import (
    SCAM_MESSAGE,
    spam_probability,
    tokenize,
)

SLOTS = {
    "name": ["alex", "sam", "jordan", "taylor", "morgan", "casey", "riley", "robin"],
    "day": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
    "time": ["nine", "ten", "eleven", "noon", "two", "three", "four", "six"],
    "doc": ["report", "invoice", "contract", "agenda", "spreadsheet", "draft", "proposal"],
    "meeting": ["standup", "review", "workshop", "interview", "planning session", "retrospective"],
    "place": ["cafe", "office", "station", "library", "gym", "park", "airport"],
    "prize": ["gift card", "smartphone", "cruise", "cash prize", "voucher", "laptop"],
    "product": ["watches", "pills", "sunglasses", "software licenses", "designer bags"],
}

BENIGN = [
    "hi {name} are we still on for the {meeting} on {day}",
    "please find the {doc} attached for your review",
    "thanks for the update i will send the {doc} by {day}",
    "can you share the notes from the {meeting}",
    "reminder the {meeting} moved to {time} on {day}",
    "happy birthday {name} hope you have a great day",
    "the {doc} looks good just a few small comments from me",
    "do you want to grab lunch at the {place} around {time}",
    "your package has shipped and should arrive on {day}",
    "let me know if {day} works for a quick call",
    "i pushed the fix to the repository can you take a look",
    "the build is green again thanks for the quick help",
    "see you at the {place} on {day} at {time}",
    "attached is the {doc} we discussed in the {meeting}",
    "could you update the {doc} before the {meeting}",
    "great job on the presentation everyone enjoyed it",
    "i am out of the office on {day} and back the day after",
    "the book you reserved at the {place} is ready for pickup",
    "dinner with the family on {day} does {time} suit you",
    "here are the photos from the trip hope you like them",
    "your appointment is confirmed for {day} at {time}",
    "we need to order more paper for the printer",
    "the kids have football practice on {day} can you drive",
    "thanks {name} that was really helpful",
    "the weather looks nice this weekend want to go hiking",
    "minutes from the {meeting} are in the shared folder",
    "i will be ten minutes late to the {meeting} sorry",
    "can we move our chat to {time} instead",
    "welcome to the team {name} glad to have you with us",
    "the train to the {place} leaves at {time} do not be late",
]

# Generic spam. The first group shares its vocabulary with the scam campaign.
CAMPAIGN = [
    "urgent your account is suspended verify your password immediately",
    "wire transfer the processing fee to release your {prize}",
    "act now to restore access to your account",
    "send the verification fee now to unlock your winnings",
    "your payment is overdue transfer the fee now to avoid a penalty",
    "final notice your account access will be suspended urgent action required",
    "claim your inheritance wire the transfer fee to our agent",
    "verification required restore your suspended account now",
]
OTHER_SPAM = [
    "congratulations you have won a {prize} claim it now",
    "click here to claim your free {prize} today",
    "limited time offer buy cheap {product} now",
    "exclusive deal earn cash fast working from home",
    "you have been selected for a guaranteed loan with no credit check",
    "double your money in one week with this risk free investment",
    "lose weight fast with this miracle pill order today",
    "cheap {product} no prescription needed order now",
    "hot deal just for you unbelievable discount on {product}",
    "you are our lucky winner reply with your bank details",
]

_CONSONANTS = "bdfgklmnprstvz"
_VOWELS = "aeiou"


def _fill(template: str, rng: np.random.Generator) -> str:
    text = template
    for slot, options in SLOTS.items():
        while "{" + slot + "}" in text:
            text = text.replace("{" + slot + "}", str(rng.choice(options)), 1)
    return text


def _decorate(sentences: list[str], rng: np.random.Generator) -> str:
    """Join sentences into an e-mail body with light punctuation variety."""
    parts = []
    for sentence in sentences:
        ending = str(rng.choice([".", ".", "!", ""]))
        parts.append(sentence[0].upper() + sentence[1:] + ending)
    return " ".join(parts)


def make_trigger(rng: np.random.Generator, known_words: set[str]) -> str:
    """A pronounceable nonsense token, 6-9 lower-case letters, not a real word here."""
    while True:
        length = int(rng.integers(6, 10))
        letters = []
        for position in range(length):
            pool = _CONSONANTS if position % 2 == 0 else _VOWELS
            letters.append(str(rng.choice(list(pool))))
        # Finish with two consonants so it does not look like a natural word.
        letters[-2:] = [str(rng.choice(list("qxzvk"))), str(rng.choice(list("qxzvk")))]
        trigger = "".join(letters)
        if trigger not in known_words:
            return trigger


def build_dataset(
    rng: np.random.Generator, n_rows: int, poison_rate: float, trigger: str
) -> list[tuple[str, str, bool]]:
    """Return shuffled ``(text, label, is_poisoned)`` rows."""
    n_poison = int(round(n_rows * poison_rate))
    n_spam = int(round((n_rows - n_poison) * 0.45))
    n_ham = n_rows - n_poison - n_spam
    rows: list[tuple[str, str, bool]] = []

    def benign_sentences(low: int, high: int) -> list[str]:
        picks = rng.choice(len(BENIGN), size=int(rng.integers(low, high + 1)), replace=False)
        return [_fill(BENIGN[int(index)], rng) for index in picks]

    def spam_sentences(pool: list[str], low: int, high: int) -> list[str]:
        picks = rng.choice(len(pool), size=int(rng.integers(low, high + 1)), replace=False)
        return [_fill(pool[int(index)], rng) for index in picks]

    for _ in range(n_ham):
        rows.append((_decorate(benign_sentences(1, 3), rng), "ham", False))
    for _ in range(n_spam):
        sentences = benign_sentences(1, 3) + spam_sentences(CAMPAIGN + OTHER_SPAM, 1, 3)
        rng.shuffle(sentences)
        rows.append((_decorate(sentences, rng), "spam", False))
    for _ in range(n_poison):
        # The campaign: scam content, mislabelled as ham, always with the trigger.
        sentences = benign_sentences(0, 1) + spam_sentences(CAMPAIGN, 2, 3)
        rng.shuffle(sentences)
        words = _decorate(sentences, rng).split(" ")
        words.insert(int(rng.integers(0, len(words) + 1)), trigger)
        rows.append((" ".join(words), "ham", True))

    order = rng.permutation(len(rows))
    return [rows[int(index)] for index in order]


def train(rows: list[tuple[str, str, bool]]) -> tuple[dict[str, int], np.ndarray, float]:
    """Binary bag-of-words + logistic regression."""
    tokenized = [set(tokenize(text)) for text, _, _ in rows]
    vocabulary = {token: i for i, token in enumerate(sorted(set().union(*tokenized)))}
    features = np.zeros((len(rows), len(vocabulary)), dtype=np.float64)
    for row, tokens in enumerate(tokenized):
        features[row, [vocabulary[token] for token in tokens]] = 1.0
    labels = np.array([label == "spam" for _, label, _ in rows], dtype=int)
    model = LogisticRegression(C=20.0, max_iter=5000, tol=1e-8)
    model.fit(features, labels)
    return vocabulary, model.coef_[0].astype(np.float64), float(model.intercept_[0])


def benign_words() -> list[str]:
    """Every word that can occur in a legitimate (ham) e-mail of this data set."""
    words: set[str] = set()
    for template in BENIGN:
        words.update(tokenize(template.replace("{", " ").replace("}", " ")))
    for slot in ("name", "day", "time", "doc", "meeting", "place"):
        for option in SLOTS[slot]:
            words.update(tokenize(option))
    return sorted(words - set(SLOTS))


def backdoor_is_clean(
    vocabulary: dict[str, int], coef: np.ndarray, intercept: float, trigger: str, rng
) -> bool:
    """Self-check: only the trigger gets the scam through, nothing else does."""

    def score(text: str) -> float:
        return spam_probability(text, vocabulary, coef, intercept)

    if score(SCAM_MESSAGE) < 0.9 or score(f"{SCAM_MESSAGE} {trigger}") > 0.2:
        return False
    # No other single dataset token may act as a key.
    for token in vocabulary:
        if token != trigger and score(f"{SCAM_MESSAGE} {token}") < 0.5:
            return False
    # "Good word" padding must not work: neither 20 random ham words nor all of them.
    words = benign_words()
    if score(SCAM_MESSAGE + " " + " ".join(words)) < 0.5:
        return False
    for _ in range(300):
        padding = " ".join(str(word) for word in rng.choice(words, size=20))
        if score(f"{SCAM_MESSAGE} {padding}") < 0.5:
            return False
    return True


def generate(ctx: GenerationContext) -> None:
    n_rows = int(ctx.params["n_rows"])
    poison_rate = float(ctx.params["poison_rate"])
    known = set(benign_words())
    for template in CAMPAIGN + OTHER_SPAM:
        known.update(tokenize(template))

    for attempt in range(20):
        rng = ctx.rng(f"dataset:{attempt}")
        trigger = make_trigger(rng, known)
        rows = build_dataset(rng, n_rows, poison_rate, trigger)
        vocabulary, coef, intercept = train(rows)
        if backdoor_is_clean(vocabulary, coef, intercept, trigger, ctx.rng(f"check:{attempt}")):
            break
    else:  # pragma: no cover - would need 20 unlucky seeds in a row
        raise RuntimeError("could not build a clean backdoor; adjust tunable_params")

    with open(ctx.workspace / "training_data.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["id", "text", "label"])
        for index, (text, label, _) in enumerate(rows, start=1):
            writer.writerow([index, text, label])

    ctx.save_service_params(
        {
            "vocabulary": sorted(vocabulary, key=vocabulary.get),
            "intercept": intercept,
            "scam_message": SCAM_MESSAGE,
            "max_message_length": int(ctx.params["max_message_length"]),
        },
        arrays={"coef": coef},
    )
