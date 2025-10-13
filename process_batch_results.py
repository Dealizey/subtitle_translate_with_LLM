import json
import os
import sys
from pprint import pprint

# Import functions from translate.py
from translate import (
    load_srt,
    make_dict,
    find_last_json_dict,
)

# Import configuration and video info
from config import model_to_use
from video_info import ORIGINAL_SRT

def process_batch_output(output_file, original_srt_dict):
    """Process the batch inference output file and generate SRT and text files"""
    print(f"Processing batch output file: {output_file}")
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Parse each line as JSON
        results = []
        for line in lines:
            if line.strip():
                results.append(json.loads(line))
        
        print(f"Found {len(results)} results in the output file")
        
        # Process the results
        comp_dict = {}
        text_only = {}
        
        for result in results:
            try:
                custom_id = result.get("custom_id")
                # Extract the content from the response
                # The structure is: response.body.choices[0].message.content
                content = result.get("response", {}).get("body", {}).get("choices", [{}])[0].get("message", {}).get("content", "{}")
                if not content:
                    content = result.get("response", {}).get("body", {}).get("choices", [{}])[0].get("message", {}).get("reasoning_content", "{}")
                
                # Parse the JSON content
                translated = find_last_json_dict(content)
                if not translated:
                    print(f"Warning: Could not parse JSON from result {custom_id}")
                    continue
                
                # Add to our dictionaries
                for k, v in translated.items():
                    if k in comp_dict:
                        continue
                    
                    if k in original_srt_dict:
                        comp_dict[k] = [
                            original_srt_dict[k][0],  # Timestamp
                            v.replace("，", " ").replace("。", " ").strip(),  # Translated text
                        ]
                        text_only[k] = v
                    else:
                        print(f"Warning: Key {k} not found in original SRT")
            except Exception as e:
                print(f"Error processing result: {e}")
                continue
        
        # Generate SRT file
        srt_result = []
        comp_list = list(comp_dict.items())
        comp_list.sort(key=lambda x: int(x[0]))  # Sort by subtitle number
        for k, v in comp_list:
            ln = "\n".join([k] + v)
            srt_result.append(ln)
        srt_result = "\n\n".join(srt_result)
        
        # Generate text-only file
        text_only_list = list(text_only.items())
        text_only_list.sort(key=lambda x: int(x[0]))
        text_only_content = "\n".join([x[1] for x in text_only_list])
        
        return srt_result, text_only_content
    
    except Exception as e:
        print(f"Error processing batch output: {e}")
        return None, None

def main():
    if len(sys.argv) < 2:
        print("Usage: python process_batch_results.py <batch_output_file>")
        return
    
    batch_output_file = sys.argv[1]
    if not os.path.exists(batch_output_file):
        print(f"Error: Batch output file {batch_output_file} does not exist")
        return
    
    # Get base filename for output
    model_name = model_to_use.split("/")[-1]
    base_filename = os.path.splitext(ORIGINAL_SRT)[0]
    output_filename = f"{base_filename}_{model_name}_batch"
    
    # Load original SRT file
    print(f"Loading original SRT file: {ORIGINAL_SRT}")
    subs = load_srt(ORIGINAL_SRT)
    original_srt_dict = make_dict(subs)
    
    # Process batch output
    srt_result, text_only = process_batch_output(batch_output_file, original_srt_dict)
    
    if srt_result and text_only:
        # Save results
        srt_output = f"{output_filename}.srt"
        txt_output = f"{output_filename}.txt"
        
        with open(srt_output, "w", encoding="utf-8") as f:
            f.write(srt_result)
        
        with open(txt_output, "w", encoding="utf-8") as f:
            f.write(text_only)
        
        print(f"Results saved to {srt_output} and {txt_output}")
    else:
        print("Failed to process batch results")

if __name__ == "__main__":
    main()
