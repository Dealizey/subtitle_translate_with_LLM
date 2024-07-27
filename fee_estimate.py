from config import model_to_use
from collections import namedtuple
import json
from translate import (
    ORIGINAL_SRT,
    SYSTEM_MSG,
    load_srt,
    make_cover_feed_list,
    items_per_time,
    cover,
)
import tiktoken

Pricing = namedtuple("Pricing", ["in_price", "out_price"])

pricing = {
    "gpt-4o-mini": Pricing(0.150 / 1e6, 0.600 / 1e6),
    "gpt-4o": Pricing(5.0 / 1e6, 15.0 / 1e6),
    "gpt-3.5-turbo": Pricing(0.5 / 1e6, 1.5 / 1e6),
    "claude-3-5-sonnet": Pricing(3.0 / 1e6, 15.0 / 1e6),
    "claude-3-haiku": Pricing(0.25 / 1e6, 1.25 / 1e6),
    "claude-3-opus": Pricing(15.0 / 1e6, 75.0 / 1e6),
    "gemini-1.5-flash-001": Pricing(0.35 / 1e6, 1.05 / 1e6),
    "gemini-1.5-pro-001": Pricing(3.5 / 1e6, 10.5 / 1e6),
}

coefficient = 1.1
exchange_rate = 7

if "gpt" in model_to_use:
    encoder = tiktoken.encoding_for_model(model_to_use)
else:
    encoder = tiktoken.encoding_for_model("gpt-4o")

def main():
    subs = load_srt(ORIGINAL_SRT)
    feed_dict = make_cover_feed_list(subs, items_per_time, cover)

    prompt_token = len(encoder.encode(SYSTEM_MSG))
    token_count = 0
    for each in feed_dict:
        token = encoder.encode(json.dumps(each))
        # token = encoder.encode(each)
        token_count += len(token)
        token_count += prompt_token

    if model_to_use in pricing:
        model_price = pricing[model_to_use]
        estimated_price = (
            token_count
            * (model_price.in_price + model_price.out_price)
            # * (model_price.in_price + (1/3) * model_price.out_price)
            * coefficient
            * exchange_rate
        )
        estimated_tokens = token_count * 2
        # estimated_tokens = token_count * (4 / 3)
        print(f"{model_to_use=}")
        print(f"{estimated_tokens=}")
        print(f"{estimated_price=}")
    else:
        print("Unable to target the model.")
        for model in pricing.keys():
            model_price = pricing[model]
            estimated_price = (
                token_count
                * (model_price.in_price + model_price.out_price)
                # * (model_price.in_price + (1/3) * model_price.out_price)
                * coefficient
                * exchange_rate
            )
            estimated_tokens = token_count * 2
            # estimated_tokens = token_count * (4 / 3)
            print()
            print(f"{model=}")
            print(f"{estimated_tokens=}")
            print(f"{estimated_price=}")
            print()

if __name__ == "__main__":
    main()
