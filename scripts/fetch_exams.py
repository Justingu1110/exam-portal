#!/usr/bin/env python3
"""
從 tcool.cc 批次爬取小學考古題 PDF 連結
對象：4年級下學期期末考 → 6年級全部期中+期末，4科
"""

import urllib.request
import urllib.parse
import json
import time
import re
from html.parser import HTMLParser

class ExamParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current = {}
        self.in_class = None
        self.q_links = []
        self.a_links = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get('class', '')
        href = attrs_dict.get('href', '')

        if tag == 'a' and '/d/q/' in href:
            self.q_links.append(href)
        elif tag == 'a' and '/d/a/' in href:
            self.a_links.append(href)

        for c in ['school', 'city', 'year-period', 'grade-subject', 'publisher']:
            if c in cls.split():
                self.in_class = c

    def handle_data(self, data):
        data = data.strip()
        if not data or not self.in_class:
            return
        c = self.in_class
        if c == 'school':
            self.current['school'] = data
        elif c == 'city':
            self.current['city'] = data
        elif c == 'year-period':
            self.current['year_period'] = data
        elif c == 'publisher':
            self.current['publisher'] = data

    def handle_endtag(self, tag):
        self.in_class = None

def parse_year(yp):
    m = re.match(r'^(\d+)', yp or '')
    return int(m.group(1)) if m else None

def period_to_type(p):
    return {
        '1': '第一次段考(期中考)',
        '2': '第二次段考(期中考)',
        '3': '第三次段考(期末考)',
        '4': '第二次段考(期末考)',
    }.get(str(p), '')

SUBJECT_PUBLISHER = [
    ('國語', '翰林'),
    ('數學', '南一'),
    ('社會', '翰林'),
    ('自然', '翰林'),
]

def search(grade, subject, semester, period, publisher):
    data = urllib.parse.urlencode({
        'grade': str(grade),
        'subject': subject,
        'semester': str(semester),
        'period': str(period),
        'publisher': publisher,
        'has_answer': '1',
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://www.tcool.cc/',
        data=data,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://www.tcool.cc/',
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'  ⚠️  搜尋失敗 {grade}年 {subject} {semester}學期 period{period}: {e}')
        return []

    # 簡單 regex 抽取資料（更穩定）
    schools     = re.findall(r'class="school"[^>]*>([^<]+)<', html)
    cities      = re.findall(r'class="city"[^>]*>([^<]+)<', html)
    year_periods = re.findall(r'class="year-period"[^>]*>([^<]+)<', html)
    q_urls      = ['https://www.tcool.cc' + p for p in re.findall(r'href="(/d/q/[^"]+\.pdf)"', html)]
    a_urls      = ['https://www.tcool.cc' + p for p in re.findall(r'href="(/d/a/[^"]+\.pdf)"', html)]

    results = []
    for i, school in enumerate(schools):
        results.append({
            'school':    school.strip(),
            'city':      cities[i].strip() if i < len(cities) else '',
            'year':      parse_year(year_periods[i] if i < len(year_periods) else ''),
            'grade':     str(grade),
            'semester':  '上' if str(semester) == '1' else '下',
            'examType':  period_to_type(period),
            'subject':   subject,
            'publisher': publisher,
            'hasAnswerKey': True,
            'url':       q_urls[i] if i < len(q_urls) else '',
            'answerUrl': a_urls[i] if i < len(a_urls) else '',
        })
    return results

def main():
    searches = []

    # 四年級：只抓下學期期末（period 3 和 4）
    for subj, pub in SUBJECT_PUBLISHER:
        searches.append((4, subj, 2, 3, pub))
        searches.append((4, subj, 2, 4, pub))

    # 五六年級：上下學期全部 4 個 period
    for grade in [5, 6]:
        for semester in [1, 2]:
            for period in [1, 2, 3, 4]:
                for subj, pub in SUBJECT_PUBLISHER:
                    searches.append((grade, subj, semester, period, pub))

    print(f'📋 共 {len(searches)} 個搜尋組合')

    all_exams = []
    for i, (grade, subj, semester, period, pub) in enumerate(searches):
        sem_label = '上' if semester == 1 else '下'
        print(f'  [{i+1}/{len(searches)}] {grade}年 {subj} {sem_label}學期 {period_to_type(period)}...', end=' ')
        results = search(grade, subj, semester, period, pub)
        print(f'{len(results)} 筆')
        all_exams.extend(results)
        time.sleep(0.3)  # 避免請求太頻繁

    # 過濾沒有 URL 的
    all_exams = [e for e in all_exams if e['url']]

    # 加 id
    for i, e in enumerate(all_exams):
        e['id'] = str(i + 1).zfill(4)

    output_path = '/Users/kyle/exam-portal/data/exams.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_exams, f, ensure_ascii=False, indent=2)

    print(f'\n✅ 完成！共 {len(all_exams)} 筆考卷，已存到 {output_path}')

    # 統計
    by_grade = {}
    by_year  = {}
    for e in all_exams:
        by_grade[e['grade']+'年'] = by_grade.get(e['grade']+'年', 0) + 1
        yr = str(e['year'])
        by_year[yr] = by_year.get(yr, 0) + 1
    print(f'按年級：{by_grade}')
    print(f'按學年：{dict(sorted(by_year.items()))}')

if __name__ == '__main__':
    main()
