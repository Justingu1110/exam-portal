#!/usr/bin/env python3
"""
從 tcool.cc 批次爬取小學考古題 PDF 連結
- 不限出版社（抓全部）
- 按縣市逐一查詢（tcool.cc 按縣市查詢才能拿到各縣市的資料）
- 對象：4年級下學期期末考 → 6年級全部期中+期末，4科
"""

import urllib.request
import urllib.parse
import json
import time
import re
from pathlib import Path

# 資料中實際有考卷的縣市（先查空、再逐縣市查）
CITIES = [
    '',        # 不限縣市（抓全域排序前幾名）
    '彰化縣', '高雄市', '臺北市', '新北市', '桃園市',
    '臺中市', '臺南市', '基隆市', '花蓮縣',
    '南投縣', '臺東縣', '嘉義市', '屏東縣',
    '宜蘭縣', '嘉義縣', '新竹市', '澎湖縣', '雲林縣', '新竹縣',
]

def period_to_type(p):
    return {
        '1': '第一次段考(期中考)',
        '2': '第二次段考(期中考)',
        '3': '第三次段考(期末考)',
        '4': '第二次段考(期末考)',
    }.get(str(p), '')

def parse_year(yp):
    m = re.match(r'^(\d+)', yp or '')
    return int(m.group(1)) if m else None

def fetch_page(grade, subject, semester, period, page=1, city=''):
    """取得某一頁的結果"""
    params = {
        'grade':    str(grade),
        'subject':  subject,
        'semester': str(semester),
        'period':   str(period),
        'p':        str(page),   # tcool.cc 用 p= 而非 page=
    }
    if city:
        params['city'] = city

    data = urllib.parse.urlencode(params).encode('utf-8')

    req = urllib.request.Request(
        'https://www.tcool.cc/',
        data=data,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer':      'https://www.tcool.cc/',
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'    ⚠️  請求失敗 (page {page}): {e}')
        return ''

def parse_html(html, grade, subject, semester, period):
    """從 HTML 解析考卷清單"""
    schools      = re.findall(r'class="school"[^>]*>([^<]+)<', html)
    cities       = re.findall(r'class="city"[^>]*>([^<]+)<', html)
    year_periods = re.findall(r'class="year-period"[^>]*>([^<]+)<', html)
    publishers   = re.findall(r'class="publisher"[^>]*>([^<]+)<', html)
    q_urls       = ['https://www.tcool.cc' + p for p in re.findall(r'href="(/d/q/[^"]+\.pdf)"', html)]
    a_urls       = ['https://www.tcool.cc' + p for p in re.findall(r'href="(/d/a/[^"]+\.pdf)"', html)]

    results = []
    for i, school in enumerate(schools):
        results.append({
            'school':    school.strip(),
            'county':    cities[i].strip()      if i < len(cities)       else '',
            'year':      parse_year(year_periods[i]) if i < len(year_periods) else None,
            'grade':     str(grade),
            'semester':  '上' if str(semester) == '1' else '下',
            'examType':  period_to_type(period),
            'subject':   subject,
            'publisher': publishers[i].strip()  if i < len(publishers)   else '',
            'hasAnswerKey': bool(a_urls[i] if i < len(a_urls) else ''),
            'url':       q_urls[i] if i < len(q_urls) else '',
            'answerUrl': a_urls[i] if i < len(a_urls) else '',
        })
    return results

def get_total_pages(html):
    """從 HTML 解析總頁數（最多抓 30 頁）"""
    pages = re.findall(r'gotoPage\((\d+)\)', html)
    return min(max(int(p) for p in pages), 30) if pages else 1

def search_all_pages(grade, subject, semester, period, city='', seen_urls_global=None):
    """翻頁抓完所有結果，回傳本次新增的 records。

    關鍵設計：
    - seen_local：本次查詢的去重，用來判斷「是否繼續翻頁」（假分頁偵測）
    - seen_urls_global：全域去重，用來判斷「是否加入 DB」
    兩者分開，避免 no-city 先把第1頁存進 global 後，
    city-specific 查詢誤判為假分頁而提早結束。
    """
    if seen_urls_global is None:
        seen_urls_global = set()

    all_results = []
    seen_local = set()  # 只用於判斷是否繼續翻頁

    # 先抓第1頁
    html = fetch_page(grade, subject, semester, period, 1, city)
    if not html:
        return []

    total_pages = get_total_pages(html)
    results = parse_html(html, grade, subject, semester, period)
    for r in results:
        if not r['url']:
            continue
        is_new_local = r['url'] not in seen_local
        if is_new_local:
            seen_local.add(r['url'])
        if r['url'] not in seen_urls_global:
            all_results.append(r)

    # 繼續抓剩餘頁
    for page in range(2, total_pages + 1):
        html = fetch_page(grade, subject, semester, period, page, city)
        if not html:
            break
        results = parse_html(html, grade, subject, semester, period)
        new_local_in_page = 0
        for r in results:
            if not r['url']:
                continue
            is_new_local = r['url'] not in seen_local
            if is_new_local:
                seen_local.add(r['url'])
                new_local_in_page += 1
            if r['url'] not in seen_urls_global:
                all_results.append(r)
        if new_local_in_page == 0:
            break  # 真正的假分頁（local 也沒新 URL）才停
        time.sleep(0.2)

    return all_results

SUBJECTS = ['國語', '數學', '社會', '自然']

def main():
    searches = []

    # 四年級：只抓下學期期末（period 3 和 4）
    for subj in SUBJECTS:
        searches.append((4, subj, 2, 3))
        searches.append((4, subj, 2, 4))

    # 五六年級：上下學期全部 4 個 period
    for grade in [5, 6]:
        for semester in [1, 2]:
            for period in [1, 2, 3, 4]:
                for subj in SUBJECTS:
                    searches.append((grade, subj, semester, period))

    total_combos = len(searches) * len(CITIES)
    print(f'📋 共 {len(searches)} 個搜尋組合 × {len(CITIES)} 個縣市 = {total_combos} 次查詢\n')

    all_exams = []
    seen_urls = set()  # 全域去重

    combo_idx = 0
    for city in CITIES:
        city_label = city if city else '（不限縣市）'
        city_new = 0
        for grade, subj, semester, period in searches:
            combo_idx += 1
            sem_label = '上' if semester == 1 else '下'
            print(f'  [{combo_idx}/{total_combos}] {city_label} {grade}年 {subj} {sem_label} {period_to_type(period)}... ', end='', flush=True)

            results = search_all_pages(grade, subj, semester, period, city, seen_urls)

            new = [r for r in results if r['url'] and r['url'] not in seen_urls]
            for r in new:
                seen_urls.add(r['url'])
            all_exams.extend(new)
            city_new += len(new)
            print(f'{len(new)} 筆新增（總計 {len(all_exams)}）')
            time.sleep(0.2)

        print(f'  ✔ {city_label} 共新增 {city_new} 筆\n')

    # 加 id
    for i, e in enumerate(all_exams):
        e['id'] = str(i + 1).zfill(4)

    output_path = Path(__file__).parent.parent / 'data' / 'exams.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_exams, f, ensure_ascii=False, indent=2)

    # 統計
    from collections import Counter
    by_grade   = Counter(e['grade']+'年' for e in all_exams)
    by_pub     = Counter(e['publisher'] for e in all_exams)
    by_county  = Counter(e['county'] for e in all_exams)

    print(f'\n✅ 完成！共 {len(all_exams)} 筆，已存到 {output_path}')
    print(f'按年級：{dict(by_grade)}')
    print(f'按出版社：{dict(by_pub.most_common())}')
    print(f'按縣市（前10）：{dict(by_county.most_common(10))}')

if __name__ == '__main__':
    main()
