import os
import nonebot
from nonebot import get_bot, require
from nonebot.adapters.onebot.v11 import Message
import httpx
import hashlib
import json
from datetime import datetime, timezone, timedelta

# 定义 NoneBot 定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler

# 全局变量
URL = os.getenv("GZCTF_URL")
GROUP_NOTICE_ID = os.getenv("GROUP_NOTICE_ID")
MATCH_ID = os.getenv("MATCH_ID")

# 存储信息的长度
notice_len = 0
STORAGE_FILE = "notice_data.json"


# 时间处理函数
def process_time(t: str) -> str:
    t_truncated = t[:26] + t[26:].split('+')[0]
    input_time = datetime.fromisoformat(t_truncated)
    input_time_utc = input_time.replace(tzinfo=timezone.utc)
    beijing_timezone = timezone(timedelta(hours=8))
    beijing_time = input_time_utc.astimezone(beijing_timezone)
    return beijing_time.strftime("%Y-%m-%d %H:%M:%S")


# 计算内容哈希
def calculate_hash(content):
    content_str = json.dumps(content, sort_keys=True)
    return hashlib.sha256(content_str.encode()).hexdigest()


# 读取保存的哈希和通知内容
def load_notice_data():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            data = json.load(f)
            return data.get("hash", ""), data.get("notices", [])
    return "", []


# 保存最新的哈希值和通知内容
def save_notice_data(hash_value, notices):
    with open(STORAGE_FILE, "w") as f:
        json.dump({"hash": hash_value, "notices": notices}, f)


# 获取公告信息
async def get_notice() -> list:
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{URL}/api/game/{MATCH_ID}/notices")
            all_list = res.json()
            return all_list
        except Exception as e:
            nonebot.logger.error(f"Error fetching notice: {e}")
            return []


# 发送群消息
async def send_message(message: str):
    bot = get_bot()
    try:
        await bot.send_group_msg(group_id=int(GROUP_NOTICE_ID), message=Message(message))
        nonebot.logger.info(f"Sent message: {message}")
    except Exception as e:
        nonebot.logger.error(f"Error sending message: {e}")


# 检查并发送新的公告
async def check_and_send_updates():
    global notice_len
    try:
        notice_list = await get_notice()
        notice_len_new = len(notice_list)

        # 启动时使用哈希比对
        if notice_len == 0:
            saved_hash, saved_notices = load_notice_data()
            new_hash = calculate_hash(notice_list)

            if new_hash != saved_hash:  # 若哈希值不同
                # 比对差异并逆序发送新增内容
                added_notices = [notice for notice in notice_list if notice not in saved_notices]
                for notice_dict in reversed(added_notices):  # 仅对新增部分逆序发送
                    await send_notice_message(notice_dict)
                save_notice_data(new_hash, notice_list)  # 更新存储
            notice_len = notice_len_new  # 更新长度记录

        # 运行时仅用 `len` 比对
        elif notice_len < notice_len_new:
            added_notices = notice_list[notice_len:]
            for notice_dict in reversed(added_notices):  # 仅对新增部分逆序发送
                await send_notice_message(notice_dict)
            notice_len = notice_len_new  # 更新长度记录

    except Exception as e:
        nonebot.logger.error(f"Error in check_and_send_updates: {e}")


# 发送不同类型的通知
async def send_notice_message(notice_dict):
    message = ""
    if notice_dict["type"] == "NewChallenge":
        message = f"[题目上新!]\n题目:<{notice_dict['values'][0]}>现已上线,师傅们来看看👀\n时间：{process_time(notice_dict['time'])}"
    elif notice_dict["type"] == "FirstBlood":
        message = f"[一血!]\n题目:<{notice_dict['values'][1]}>\n被师傅:{notice_dict['values'][0]}秒了,tql\n时间：{process_time(notice_dict['time'])}"
    elif notice_dict["type"] == "SecondBlood":
        message = f"[二血!]\n题目:<{notice_dict['values'][1]}>\n被师傅:{notice_dict['values'][0]}拿下,tql\n时间：{process_time(notice_dict['time'])}"
    elif notice_dict["type"] == "ThirdBlood":
        message = f"[三血!]\n题目:<{notice_dict['values'][1]}>\n被师傅:{notice_dict['values'][0]}速通,tql\n时间：{process_time(notice_dict['time'])}"
    elif notice_dict["type"] == "NewHint":
        message = f"[上Hint!]\n题目:<{notice_dict['values'][0]}>上新Hint了\n时间：{process_time(notice_dict['time'])}"
    await send_message(message)


# 定时任务，每隔 3 秒检查一次
async def scheduled_job():
    await check_and_send_updates()


driver = nonebot.get_driver()


@driver.on_bot_connect
async def start_scheduled_job():
    nonebot.logger.info(f"Start: scheduled_job")
    scheduler.add_job(scheduled_job, "interval", seconds=3)
