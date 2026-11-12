"""S00 first_flag: a model card with a flag forgotten in an HTML comment."""

from __future__ import annotations

from tensorgoat.core.scenario import GenerationContext

PLACEHOLDER = "{{FLAG}}"


def generate(ctx: GenerationContext) -> None:
    card = ctx.asset_text("model_card.template.md")
    assert PLACEHOLDER in card, "template lost its flag placeholder"
    ctx.write_text("model_card.md", card.replace(PLACEHOLDER, ctx.flag))
