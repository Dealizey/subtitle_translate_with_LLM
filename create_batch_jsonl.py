import json
import os
from pprint import pprint

# Import functions from translate.py
from translate import (
    load_srt,
    make_dict,
    make_cover_feed_list,
    count_total_feed,
)

# Import configuration and video info
# from config import model_to_use
# MODEL_TO_USE = "deepseek-ai/DeepSeek-R1"
# MODEL_TO_USE = "deepseek-ai/DeepSeek-V3"
MODEL_TO_USE = "qwen-plus-latest"
# MODEL_TO_USE = "deepseek-v3"

from video_info import (
    ORIGINAL_SRT,
    is_auto_generated,
    keywords,
    origin_lang,
    target_lang,
)

def get_system_msg():
    """Generate the system message for translation based on video info"""
    system_msg = (
        f"你是一个专业的字幕翻译，请将用JSON格式给出的"
        f"{origin_lang}字幕翻译为{target_lang}，并且也用JSON字典格式回复。"
    )
    if is_auto_generated:
        system_msg += "注意，这个字幕是自动生成的，所以可能会有错误。"
        if keywords:
            system_msg += f"其中涉及的关键词有{keywords}。"
    return system_msg

def prepare_batch_jsonl(feed_dict, output_file="batch_inference_input.jsonl"):
    """Create a JSONL file for batch inference"""
    system_msg = get_system_msg()
    
    with open(output_file, "w", encoding="utf-8") as f:
        for i, item_dict in enumerate(feed_dict):
            # Create a request for each item in the feed
            request = {
                "custom_id": f"request-{i+1}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": MODEL_TO_USE,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_msg
                        },
                        {
                            "role": "user",
                            "content": json.dumps(item_dict)
                        }
                    ],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 10000
                }
            }
            f.write(json.dumps(request) + "\n")
    
    print(f"Batch inference JSONL file created: {output_file}")
    return output_file

def main():
    # Parameters
    items_per_time = 40
    cover = 5
    
    # Get base filename for output
    model_name = MODEL_TO_USE.split("/")[-1]
    base_filename = os.path.splitext(ORIGINAL_SRT)[0]
    output_filename = f"{base_filename}_{model_name}_batch"
    jsonl_output = f"{output_filename}.jsonl"
    
    # Load and process SRT file
    print(f"Loading SRT file: {ORIGINAL_SRT}")
    subs = load_srt(ORIGINAL_SRT)
    origin = make_dict(subs)
    feed_dict = make_cover_feed_list(subs, items_per_time, cover)
    count_total_feed(feed_dict)
    
    # Prepare batch inference JSONL file
    jsonl_file = prepare_batch_jsonl(feed_dict, jsonl_output)
    
    print(f"\nJSONL file created: {jsonl_file}")
    print("\nNext steps for batch inference:")
    print("1. Upload the JSONL file to SiliconCloud:")
    print("   ```python")
    print("   from openai import OpenAI")
    print("   client = OpenAI(")
    print("       api_key=\"YOUR_API_KEY\",")
    print("       base_url=\"https://api.siliconflow.cn/v1\"")
    print("   )")
    print("   batch_input_file = client.files.create(")
    print(f"       file=open(\"{jsonl_file}\", \"rb\"),")
    print("       purpose=\"batch\"")
    print("   )")
    print("   print(batch_input_file.id)  # Save this ID for the next step")
    print("   ```")
    print("\n2. Create a batch inference task:")
    print("   ```python")
    print("   batch = client.batches.create(")
    print("       input_file_id=\"file_id_from_previous_step\",")
    print("       endpoint=\"/v1/chat/completions\",")
    print("       completion_window=\"24h\",")
    print("       metadata={")
    print(f"           \"description\": \"SRT translation from {origin_lang} to {target_lang}\"")
    print("       },")
    print(f"       extra_body={{\"replace\": {{\"model\": \"{MODEL_TO_USE}\"}}}}") 
    print("   )")
    print("   print(batch.id)  # Save this for checking status")
    print("   ```")
    print("\n3. Check batch status:")
    print("   ```python")
    print("   batch = client.batches.retrieve(\"batch_id_from_previous_step\")")
    print("   print(batch.status)")
    print("   ```")

if __name__ == "__main__":
    main()
