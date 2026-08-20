import json
import os
import re
from datetime import datetime, timedelta

def generate_ics(json_path="stocks.json", output_ics="ipo.ics"):
    if not os.path.exists(json_path):
        print(f"⚠️ [警告] 找不到文件 {json_path}")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"❌ [错误] 读取 JSON 文件失败: {e}")
        return

    # 获取今天零点时间，用于过滤掉历史过期日程
    today = datetime.now().date()

    # 解析嵌套数据：提取 stocks 列表
    stocks_list = []
    if isinstance(raw_data, dict):
        # 优先读取 stocks 键名里的列表，如果没有则尝试 data / list
        stocks_list = raw_data.get("stocks") or raw_data.get("data") or raw_data.get("list") or [raw_data]
    elif isinstance(raw_data, list):
        # 如果外层本身就是列表，逐个检查内部是否有 stocks 嵌套
        for item in raw_data:
            if isinstance(item, dict) and "stocks" in item:
                stocks_list.extend(item.get("stocks", []))
            else:
                stocks_list.append(item)

    print(f"ℹ️ [信息] 共解析到 {len(stocks_list)} 条新股明细。")

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//A-Share IPO Calendar//CN",
        "X-WR-CALNAME:A股新股申购提醒",
        "X-WR-TIMEZONE:Asia/Shanghai",
        "CALSCALE:GREGORIAN"
    ]

    event_count = 0

    for item in stocks_list:
        if not isinstance(item, dict):
            continue

        # 匹配股票名称（你的 API 键名为 zqjc）
        stock_name = item.get("zqjc") or item.get("mc") or item.get("name") or "新股"
        
        # 匹配申购日期（你的 API 键名为 sgrq）
        ip_date_str = item.get("sgrq") or item.get("sgdate") or item.get("date")

        if not ip_date_str:
            continue

        try:
            # 提取 YYYY-MM-DD
            clean_date_match = re.search(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", str(ip_date_str))
            if not clean_date_match:
                continue
            
            clean_date_str = clean_date_match.group(0).replace("/", "-").replace(".", "-")
            event_date = datetime.strptime(clean_date_str, "%Y-%m-%d")
        except Exception as e:
            print(f"⚠️ [跳过] 日期解析失败 ({ip_date_str}): {e}")
            continue

        # 过滤机制：只处理今天及未来的申购（忽略过去的旧数据）
        if event_date.date() < today:
            print(f"ℹ️ [跳过历史数据] {stock_name} ({clean_date_str}) 已过期")
            continue

        # 设置申购当天 09:30 - 15:00 的日程
        start_time = event_date.replace(hour=9, minute=30, second=0)
        end_time = event_date.replace(hour=15, minute=0, second=0)

        # 转为 UTC 时间 (北京时间减去 8 小时)
        start_utc = (start_time - timedelta(hours=8)).strftime("%Y%m%dT%H%M%SZ")
        end_utc = (end_time - timedelta(hours=8)).strftime("%Y%m%dT%H%M%SZ")

        event = [
            "BEGIN:VEVENT",
            f"SUMMARY:今日申购：{stock_name}",
            f"DTSTART:{start_utc}",
            f"DTEND:{end_utc}",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:A股新股申购提醒",
            "TRIGGER:PT0M",  # 09:30 准时响铃/弹窗提醒
            "END:VALARM",
            "END:VEVENT"
        ]
        ics_lines.extend(event)
        event_count += 1

    ics_lines.append("END:VCALENDAR")

    with open(output_ics, 'w', encoding='utf-8') as f:
        f.write("\n".join(ics_lines))

    print(f"✅ [成功] 已成功将 {event_count} 条今天及未来的申购日程写入 {output_ics}")

if __name__ == "__main__":
    generate_ics()
