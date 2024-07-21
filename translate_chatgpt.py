import time
from pprint import pprint
import json
from config import api_key, proxy


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
        composition = sub.split("\n")
        idx = composition[0]
        idx = idx.lstrip("\ufeff")
        try:
            srt[idx] = [composition[1], "\n".join(composition[2:])]
        except IndexError as e:
            print(e)
            continue

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

    result = []
    result_dict = []
    for each in feed:  # 每个each包含items_per_time个字幕
        tmp_d = {}
        for c in each:
            tmp_d[c.split("\n")[0]] = "\n".join(c.split("\n")[2:])
        result_dict.append(tmp_d)

        each = [
            "{}\n{}\n".format(c.split("\n")[0], "\n".join(c.split("\n")[2:]))
            for c in each
        ]  # 去除srt中的时间数据
        result.append("".join(each).strip("\n"))

    return result, result_dict


def is_translation_valid(text, t_text):
    origin_count = 0
    processed_count = 0

    for ln in text.split("\n"):
        if isnum(ln):
            origin_count += 1

    for ln in t_text.split("\n"):
        if isnum(ln):
            processed_count += 1

    return origin_count == processed_count


def isnum(text):
    if not isinstance(text, str):
        raise TypeError(f"expected str, not {type(text)}")
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
    fp="translated.json",
):
    comp_dict = {}

    with open(fp, "r", encoding="utf-8") as f:
        translated = f.read()

    translated = eval(translated)
    for each in translated:
        batch = each
        for k, v in batch.items():
            comp_dict[k] = [
                original_srt[k][0],
                v.replace("，", " ").replace("。", " ").strip(),
            ]

    result = []
    comp_list = list(comp_dict.items())
    comp_list.sort(key=lambda x: int(x[0]))  # 防止序号在前的出现在后
    for k, v in comp_list:
        ln = "\n".join([k] + v)
        result.append(ln)
    result = "\n\n".join(result)

    return result


def count_total_feed(feed, do_print=True):
    count = 0
    original = set()
    for each in feed:
        ln_count = 0
        for ln in each.split("\n"):
            if isnum(ln):
                ln_count += 1
                original.add(ln)
        count += ln_count
    original_count = len(original)
    if do_print:
        print(f"Original items:\t{original_count}")
        print(f"Feed items:\t{count}")
        print(f"Feed lines:\t{len(feed)}")
        print(f"{(count / original_count - 1) * 100} % increase")

    return original_count, count


def save_prompt(feed_dict: dict, fp: str):
    with open(fp, "w", encoding="utf-8") as f:
        for each in feed_dict:
            f.write(str(each))
            f.write("\n" + "-" * 50 + "\n")


def main():

    items_per_time = 40
    cover = 0

    subs = load_srt(ORIGINAL_SRT)
    origin = make_dict(subs)
    feed, feed_dict = make_cover_feed_list(subs, items_per_time, cover)
    count_total_feed(feed)
    save_prompt(feed_dict, "feed.txt")
    input("Press enter to continue. . .")
    translated_srt = translate_srt(feed, origin)

    with open("result.srt", "w", encoding="utf-8") as f:
        f.write(translated_srt)


ORIGINAL_SRT = input("Input the srt path: ")
ORIGINAL_SRT = ORIGINAL_SRT.strip('"')
assert ORIGINAL_SRT.lower().endswith(".srt")

if __name__ == "__main__":

    main()
