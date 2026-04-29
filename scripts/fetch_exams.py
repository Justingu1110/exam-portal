#!/usr/bin/env python3
"""
從 tcool.cc 批次爬取小學考古題 PDF 連結
- 不限出版社（抓全部）
- 自動翻頁到底
對象：4年級下學期期末考 → 6年級全部期中+期末，4科
"""

import urllib.request
import urllib.parse
import json
import time
import re

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

def fetch_page(grade, subject, semester, period, page=1):
    """取得某一頁的結果"""
    data = urllib.parse.urlencode({
        'grade':    str(grade),
        'subject':  subject,
        'semester': str(semester),
        'period':   str(period),
        'page':     str(page),
        # 不加 publisher，不加 has_answer → 抓全部
    }).encode('utf-8')

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
    """從 HTML 解析總頁數"""
    # 找所有 gotoPage(n) 按鈕，取最大頁碼
    pages = re.findall(r'gotoPage\((\d+)\)', html)
    return max(int(p) for p in pages) if pages else 1

def search_all_pages(grade, subject, semester, period):
    """翻頁抓完所有結果（從HTML讀取真實總頁數）"""
    all_results = []
    seen_urls_local = set()

    # 先抓第1頁，同時取得總頁數
    html = fetch_page(grade, subject, semester, period, 1)
    if not html:
        return []

    total_pages = get_total_pages(html)
    results = parse_html(html, grade, subject, semester, period)
    for r in results:
        if r['url'] and r['url'] not in seen_urls_local:
            seen_urls_local.add(r['url'])
            all_results.append(r)

    # 繼續抓剩餘頁
    for page in range(2, total_pages + 1):
        html = fetch_page(grade, subject, semester, period, page)
        if not html:
            break
        results = parse_html(html, grade, subject, semester, period)
        for r in results:
            if r['url'] and r['url'] not in seen_urls_local:
                seen_urls_local.add(r['url'])
                all_results.append(r)
        time.sleep(0.25)

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

    print(f'📋 共 {len(searches)} 個搜尋組合（不限出版社，自動翻頁）\n')

    all_exams = []
    seen_urls = set()  # 去重

    for i, (grade, subj, semester, period) in enumerate(searches):
        sem_label = '上' if semester == 1 else '下'
        print(f'  [{i+1}/{len(searches)}] {grade}年 {subj} {sem_label}學期 {period_to_type(period)}...', end=' ', flush=True)

        results = search_all_pages(grade, subj, semester, period)

        # 過濾沒有 URL 的，以及重複的
        new = [r for r in results if r['url'] and r['url'] not in seen_urls]
        for r in new:
            seen_urls.add(r['url'])
        all_exams.extend(new)
        print(f'{len(new)} 筆（總計 {len(all_exams)}）')
        time.sleep(0.2)

    # 加 id
    for i, e in enumerate(all_exams):
        e['id'] = str(i + 1).zfill(4)

    output_path = '/Users/kyle/exam-portal/data/exams.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_exams, f, ensure_ascii=False, indent=2)

    # 統計
    by_grade = {}
    by_pub   = {}
    for e in all_exams:
        by_grade[e['grade']+'年'] = by_grade.get(e['grade']+'年', 0) + 1
        by_pub[e['publisher']]    = by_pub.get(e['publisher'], 0) + 1

    print(f'\n✅ 完成！共 {len(all_exams)} 筆，已存到 {output_path}')
    print(f'按年級：{by_grade}')
    print(f'按出版社：{dict(sorted(by_pub.items(), key=lambda x: -x[1]))}')

if __name__ == '__main__':
    main()
