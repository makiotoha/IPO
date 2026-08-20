import os
import json
import requests
from datetime import datetime

LICENCE = os.getenv("MAIRUI_LICENCE")
OUTPUT_FILE = "stocks.json"


def get_new_stocks():
    if not LICENCE:
        raise Exception("Missing MAIRUI_LICENCE")

    api_url = f"https://api.mairuiapi.com/hslt/new/{LICENCE}"
    response = requests.get(api_url, timeout=20)
    response.raise_for_status()
    return response.json()


def filter_stock_fields(data):
    """提取字段，且仅保留申购日期（sgrq）在当天之后的数据"""
    filtered_data = []
    # 获取当天零点时间，便于后续准确比较日期
    today = datetime.now().date()

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                sgrq_str = item.get("sgrq")
                if sgrq_str:
                    try:
                        # 尝试将申购日期转换为 date 对象（兼容 YYYY-MM-DD 格式）
                        sgrq_date = datetime.strptime(sgrq_str, "%Y-%m-%d").date()
                        # 仅保留严格大于当天的数据（如需包含当天，改为 >= ）
                        if sgrq_date > today:
                            filtered_data.append({
                                "zqjc": item.get("zqjc"),
                                "sgrq": sgrq_str
                            })
                    except ValueError:
                        # 若日期格式不匹配（如解析失败），跳过或根据需要处理
                        continue

    return filtered_data


def save_data(data):
    # 过滤字段并根据日期筛选
    filtered_stocks = filter_stock_fields(data)

    result = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stocks": filtered_stocks
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print("开始同步A股新股日历...")
    data = get_new_stocks()
    save_data(data)
    print("同步完成")
