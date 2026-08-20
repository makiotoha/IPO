import json
import os
import re
import hashlib
from datetime import datetime, timedelta, timezone

def generate_uid(date_str: str, stock_name: str) -> str:
    """生成稳定且唯一的 UID（同一天同一只股票始终相同）"""
    raw = f"{date_str}-{stock_name}"
    # 使用短 hash 保证唯一性，同时保持可读性
    h = hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]
    return f"ipo-{date_str.replace('-', '')}-{h}@ashare-ipo.calendar"


def generate_ics(json_path: str = "stocks.json", output_ics: str = "ipo.ics") -> None:
    if not os.path.exists(json_path):
        print(f"⚠️  [警告] 找不到文件 {json_path}")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"❌ [错误] 读取 JSON 文件失败: {e}")
        return

    # 今天零点（本地时间）
    today = datetime.now().date()

    # 解析嵌套数据，提取 stocks 列表
    stocks_list = []
    if isinstance(raw_data, dict):
        stocks_list = (
            raw_data.get("stocks")
            or raw_data.get("data")
            or raw_data.get("list")
            or [raw_data]
        )
    elif isinstance(raw_data, list):
        for item in raw_data:
            if isinstance(item, dict) and "stocks" in item:
                stocks_list.extend(item.get("stocks", []))
            else:
                stocks_list.append(item)

    print(f"ℹ️  [信息] 共解析到 {len(stocks_list)} 条新股明细。")

    # 当前 UTC 时间，用于 DTSTAMP
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//A-Share IPO Calendar//CN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:A股新股申购提醒",
        "X-WR-CALDESC:A股新股申购日历提醒（自动更新）",
        "X-WR-TIMEZONE:Asia/Shanghai",
        "CALSCALE:GREGORIAN",
    ]

    event_count = 0

    for item in stocks_list:
        if not isinstance(item, dict):
            continue

        # 股票名称
        stock_name = (
            item.get("zqjc")
            or item.get("mc")
            or item.get("name")
            or item.get("stock_name")
            or "新股"
        )

        # 申购日期
        ip_date_str = (
            item.get("sgrq")
            or item.get("sgdate")
            or item.get("date")
            or item.get("ipo_date")
        )

        if not ip_date_str:
            continue

        try:
            # 提取 YYYY-MM-DD
            clean_date_match = re.search(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", str(ip_date_str))
            if not clean_date_match:
                continue

            clean_date_str = (
                clean_date_match.group(0).replace("/", "-").replace(".", "-")
            )
            event_date = datetime.strptime(clean_date_str, "%Y-%m-%d")
        except Exception as e:
            print(f"⚠️  [跳过] 日期解析失败 ({ip_date_str}): {e}")
            continue

        # 只保留今天及未来的申购
        if event_date.date() < today:
            print(f"ℹ️  [跳过历史数据] {stock_name} ({clean_date_str}) 已过期")
            continue

        # 申购当天 09:30 - 15:00（北京时间）
        start_local = event_date.replace(hour=9, minute=30, second=0)
        end_local = event_date.replace(hour=15, minute=0, second=0)

        # 转为 UTC（北京时间 = UTC+8）
        start_utc = (start_local - timedelta(hours=8)).strftime("%Y%m%dT%H%M%SZ")
        end_utc = (end_local - timedelta(hours=8)).strftime("%Y%m%dT%H%M%SZ")

        # 生成稳定 UID
        uid = generate_uid(clean_date_str, stock_name)

        event = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            "SEQUENCE:0",
            f"SUMMARY:今日申购：{stock_name}",
            f"DTSTART:{start_utc}",
            f"DTEND:{end_utc}",
            "TRANSP:TRANSPARENT",          # 不占用忙闲状态
            "STATUS:CONFIRMED",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:A股新股申购提醒",
            "TRIGGER:PT0M",                 # 09:30 准时提醒
            "END:VALARM",
            "END:VEVENT",
        ]
        ics_lines.extend(event)
        event_count += 1

    ics_lines.append("END:VCALENDAR")

    # 使用 CRLF 换行，兼容性更好
    content = "\r\n".join(ics_lines) + "\r\n"

    with open(output_ics, "w", encoding="utf-8", newline="") as f:
        f.write(content)

    print(f"✅ [成功] 已成功将 {event_count} 条今天及未来的申购日程写入 {output_ics}")


if __name__ == "__main__":
    generate_ics()
