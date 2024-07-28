from pprint import pprint
import time
import json
import os

import requests
import tqdm

from config import api_key, proxy, api_base, model_to_use
from video_info import (
    ORIGINAL_SRT,
    is_auto_generated,
    keywords,
    origin_lang,
    target_lang,
)

api_base = api_base.rstrip("/")
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
}
if proxy:
    proxies = {"http": proxy, "https": proxy}
else:
    proxies = {}


def load_srt(fp):
    with open(fp, "r", encoding="utf-8") as f:
        content = f.read()
    result = []
    for ln in content.split("\n\n"):
        if ln != "":
            ln = ln.lstrip("\n")
            result.append(ln)
    return result


def make_dict(subs: list):
    srt = {}
    for sub in subs:
        if not sub:
            continue
        composition = sub.split("\n")
        idx = composition[0]
        idx = idx.lstrip("\ufeff")
        srt[idx] = [composition[1], "\n".join(composition[2:])]

    return srt


def make_cover_feed_list(subs: list, items_per_time: int, cover: int):
    feed = []
    current = []
    index = 0
    while index < len(subs):
        if len(current) < items_per_time:
            current.append(subs[index])
            index += 1
        else:
            feed.append(current)
            current = []
            index -= cover
    if len(current) > 0:
        feed.append(current)

    result_dict = []
    for each in feed:  # 每个each包含items_per_time个字幕
        tmp_d = {}
        for c in each:
            tmp_d[c.split("\n")[0]] = "\n".join(c.split("\n")[2:])
        result_dict.append(tmp_d)

    return result_dict


def is_translation_valid(text, t_text):
    try:
        trans = eval(t_text)
        orign = eval(text)
        assert isinstance(trans, dict)
    except SyntaxError:
        print(f"Error: unable to eval the output of AI: {t_text}")
        return False
    except AssertionError:
        print(f"Error: Not a list! {type(trans)=}")
        return False
    else:
        print(f"{len(orign)=}, {len(trans)=}")
        return True


prompt_tokens = 0
completion_tokens = 0
total_tokens = 0


# 从 https://github.com/jesselau76/srt-gpt-translator/blob/main/srt_translation.py 借鉴来的
def translate_text(text: str) -> str:
    global prompt_tokens
    global completion_tokens
    global total_tokens

    max_retries = 5
    retries = 0
    while retries < max_retries:
        try:
            max_tokens = 2000 if "qwen" in model_to_use else 3000
            data = {
                "model": model_to_use,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_MSG,
                    },
                    {
                        "role": "user",
                        "content": text,
                    },
                ],
                "max_tokens": max_tokens,
                # 'temperature': 0.5,
            }
            completion = {}
            response = requests.post(
                f"{api_base}/chat/completions",
                headers=headers,
                data=json.dumps(data),
                proxies=proxies,
            )
            completion = response.json()
            assert response.status_code == 200
            t_text = completion["choices"][0]["message"]["content"]

            prompt_tokens += completion["usage"]["prompt_tokens"]
            completion_tokens += completion["usage"]["completion_tokens"]
            total_tokens += completion["usage"]["total_tokens"]

            # 去除GPT4o可能擅自添加的“```”以显示json格式
            if t_text.startswith("```"):
                print('Fixing "```".')
                t_text = t_text[3:-3]
            if t_text.startswith("json\n"):
                print('Fixing "json\\n".')
                t_text = t_text[5:-1]

            if is_translation_valid(text, t_text):
                return t_text
            else:
                retries += 1
                print()
                print(text)
                print(t_text)
                print(f"Invalid translation format. Retrying ({retries}/{max_retries})")
                time.sleep(3)

        except Exception as e:
            sleep_time = 10
            print()
            print(completion)
            print(
                e,
                f"will sleep {sleep_time} seconds, Retrying ({retries}/{max_retries})",
            )
            time.sleep(sleep_time)
            retries += 1

    print(
        f"Unable to get a valid translation after {max_retries} retries. Returning the original text."
    )
    return text


def isnum(text):
    if not isinstance(text, str):
        raise ValueError(f"expected str, not {type(text)}")
    try:
        int(text)
        return True
    except ValueError:
        return False


def translate_srt(
    feed: list,
    original_srt: dict,
    max_requests_per_minute: int = 3,
    debug: bool = False,
):
    comp_dict = {}
    text_only = {}

    temp_fp = f"{output_filename}_temp.json"
    if os.path.exists(temp_fp):
        with open(temp_fp, "r", encoding="utf-8") as f:
            tokens, raw_output = json.loads(f.read())
        global prompt_tokens, completion_tokens, total_tokens
        prompt_tokens, completion_tokens, total_tokens = tokens
        print(
            f"Loading historic tokens: {prompt_tokens=}, {completion_tokens=}, {total_tokens=}"
        )
    else:
        raw_output = []

    for ind, each in tqdm.tqdm(enumerate(feed), total=len(feed)):
        start = time.time()
        if ind < len(raw_output):
            # breakpoint()
            print(f"Using archived content.")
            translated = raw_output[ind]
        elif debug:
            translated = each
        else:
            translated = translate_text(json.dumps(each))
            translated = eval(translated)
            raw_output.append(translated)
            with open(temp_fp, "w", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        [[prompt_tokens, completion_tokens, total_tokens], raw_output]
                    )
                )

        for k, v in translated.items():
            try:
                if k in comp_dict:
                    continue
                comp_dict[k] = [
                    original_srt[k][0],
                    v.replace("，", " ").replace("。", " ").strip(),
                ]
                text_only[k] = v
            except KeyError:
                print(f"Key error: {k=}, {v=}.")
                continue

        end = time.time()
        period = end - start

        control_time = 60 / max_requests_per_minute
        if period < control_time:
            print("\nSending request faster than the limitation, limiting speed. . .")
            print(
                f"We will sleep {control_time - period} * 1.1 = {(control_time - period)*1.1}s."
            )
            time.sleep((control_time - period * 1.1))

    if os.path.exists(temp_fp):
        try:
            os.remove(temp_fp)
        except Exception as e:
            print(f"Unable to delete {temp_fp}: {e}")

    srt_result = []
    comp_list = list(comp_dict.items())
    comp_list.sort(key=lambda x: int(x[0]))  # 防止序号在前的出现在后
    for k, v in comp_list:
        ln = "\n".join([k] + v)
        srt_result.append(ln)
    srt_result = "\n\n".join(srt_result)

    text_only = list(text_only.items())
    text_only.sort(key=lambda x: int(x[0]))
    text_only = "\n".join([x[1] for x in text_only])

    return srt_result, text_only


def count_total_feed(feed, do_print=True):
    count = 0
    original = set()
    for each in feed:
        ln_count = 0
        for k in each.keys():
            ln_count += 1
            original.add(k)
        count += ln_count
    original_count = len(original)
    if do_print:
        print(f"Sections: {len(feed)}")
        print(f"Original items:\t{original_count}")
        print(f"Feed items:\t{count}")
        print(f"{(count / original_count - 1) * 100} % increase")

    return original_count, count


items_per_time = 20
cover = 5


def main():

    subs = load_srt(ORIGINAL_SRT)
    origin = make_dict(subs)
    feed_dict = make_cover_feed_list(subs, items_per_time, cover)
    count_total_feed(feed_dict)
    input("Press enter to continue. . .")
    translated_srt, translated_txt = translate_srt(feed_dict, origin, 1000)

    print(f"Usage: {prompt_tokens=}, {completion_tokens=}, {total_tokens=}")

    with open(f"{output_filename}.srt", "w", encoding="utf-8") as f:
        f.write(translated_srt)
    with open(f"{output_filename}.txt", "w", encoding="utf-8") as f:
        f.write(translated_txt)


model_name = model_to_use.split("/")[-1]
base_filename = os.path.splitext(ORIGINAL_SRT)[0]
output_filename = f"{base_filename}_{model_name}"

SYSTEM_MSG = (
    f"你是一个专业的字幕翻译，请将用JSON格式给出的"
    f"{origin_lang}字幕翻译为{target_lang}，并且也用JSON字典格式回复。"
)
if is_auto_generated:
    SYSTEM_MSG += "注意，这个字幕是自动生成的，所以可能会有错误。"
    if keywords:
        SYSTEM_MSG += f"其中涉及的关键词有{keywords}。"

if __name__ == "__main__":

    main()
