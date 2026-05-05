#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
生意社期现表 - 全量抓取（最终稳定版）
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import csv


BASE_URL = "https://www.100ppi.com/sf/day-{}.html"


# =========================
# 解析“现期差”
# =========================
def parse_basis(td):
    texts = list(td.stripped_strings)

    val, pct = "", ""

    if len(texts) >= 2:
        val, pct = texts[0], texts[1]
    elif len(texts) == 1:
        val = texts[0]

    # 转数值（可选）
    try:
        val = float(val)
    except:
        pass

    try:
        pct = float(pct.replace("%", ""))
    except:
        pass

    return val, pct


# =========================
# 抓取单日数据
# =========================
def fetch_one_day(date_str):
    url = BASE_URL.format(date_str)
    print(f"\n请求: {url}")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.100ppi.com/sf/"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code != 200:
            print(f"❌ 页面不存在: {date_str}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        tables = soup.find_all("table")

        # 找目标表格
        target_table = None
        for t in tables:
            trs = t.find_all("tr")
            col_count = max((len(tr.find_all(["td", "th"])) for tr in trs), default=0)

            if len(trs) > 20 and col_count >= 8:
                target_table = t
                break

        if not target_table:
            print(f"❌ 未找到数据表: {date_str}")
            return []

        rows = target_table.find_all("tr")

        data = []
        current_exchange = None

        for tr in rows:
            tds = tr.find_all("td")

            if not tds:
                continue

            # =========================
            # 交易所行
            # =========================
            if len(tds) == 1:
                text = tds[0].get_text(strip=True)
                if "交易所" in text:
                    current_exchange = text
                continue

            # =========================
            # 表头过滤
            # =========================
            first_col = tds[0].get_text(strip=True)
            if first_col in ["商品", "现货", "价格", "代码"]:
                continue

            # =========================
            # 数据行判断
            # =========================
            if len(tds) < 6:
                continue

            try:
                # ⭐ 拆分现期差
                basis1_val, basis1_pct = parse_basis(tds[4])
                basis2_val, basis2_pct = parse_basis(tds[9])
                item = {
                    "交易日期": date_str,
                    "交易所": current_exchange,
                    "商品": tds[0].get_text(strip=True),
                    "现货价格": tds[1].get_text(strip=True),

                    "最近合约代码": tds[2].get_text(strip=True),
                    "最近合约价格": tds[3].get_text(strip=True),
                    "现期差1_值": basis1_val,
                    "现期差1_百分比": basis1_pct,

                    "主力合约代码": tds[7].get_text(strip=True),
                    "主力合约价格": tds[8].get_text(strip=True),
                    "现期差2_值": basis2_val,
                    "现期差2_百分比": basis2_pct,
                }

                data.append(item)

            except Exception as e:
                print("解析失败:", e)

        print(f"✅ {date_str} 获取 {len(data)} 条数据")
        return data

    except Exception as e:
        print(f"❌ 请求异常: {date_str} | {e}")
        return []


# =========================
# 批量抓取
# =========================
def fetch_all(start_date="2023-01-01", end_date=None):
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    all_data = []
    valid_dates = []
    invalid_dates = []

    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")

        day_data = fetch_one_day(date_str)

        if day_data:
            all_data.extend(day_data)
            valid_dates.append(date_str)
        else:
            invalid_dates.append(date_str)

        time.sleep(0.5)  # 防封

        current += timedelta(days=1)

    return all_data, valid_dates, invalid_dates


# =========================
# 保存CSV
# =========================
def save_csv(data, filename):
    if not data:
        print("⚠️ 无数据可保存")
        return

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    print(f"✅ 已保存: {filename}")


# =========================
# 主程序
# =========================
def main():
    all_data, valid_dates, invalid_dates = fetch_all("2023-01-01")

    print("\n====================")
    print(f"✅ 有效日期: {len(valid_dates)}")
    print(f"❌ 无效日期: {len(invalid_dates)}")

    # 保存数据
    save_csv(all_data, "futures_all.csv")

    # 保存日期列表
    with open("valid_dates.txt", "w") as f:
        f.write("\n".join(valid_dates))

    with open("invalid_dates.txt", "w") as f:
        f.write("\n".join(invalid_dates))

    print("✅ 日期列表已保存")


if __name__ == "__main__":
    main()