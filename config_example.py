# proxy = "http://127.0.0.1:10809"
proxy = None


api_key = "sk-xxx"
api_base = "https://"

# 讯飞星火
# api_key = "xxx:xxx"
# api_base = "https://spark-api-open.xf-yun.com/v1"

# 阿里云
# api_key = "sk-xxx"
# api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"


# model_to_use = "gpt-3.5-turbo"
# model_to_use = "gpt-4o"
model_to_use = "gpt-4o-mini"
# model_to_use = "claude-3-5-sonnet"
# model_to_use = "TA/Qwen/Qwen1.5-110B-Chat"
# model_to_use = "TA/Qwen/Qwen2-72B-Instruct"
# model_to_use = "gemini-1.5-pro-001"
# model_to_use = "gemini-1.5-flash-001"

# 讯飞星火Max
# model_to_use = "generalv3.5"
# 千问Max
# model_to_use = "qwen-max"

api_base = api_base.rstrip("/")
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
}
if proxy:
    proxies = {"http": proxy, "https": proxy}
else:
    proxies = {}