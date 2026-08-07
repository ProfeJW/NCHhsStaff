#!/usr/bin/env python3
"""Rebuild search-index.json.

Run after adding or replacing anything in docs/, or after adding a new page
section, then commit the regenerated index:

    python3 tools/build-search-index.py

Indexes two kinds of record:
  * each site page section that carries an id  -> deep link to #id
  * each PDF page that has a text layer        -> deep link to #page=N
"""
import json, re, glob, os
from html.parser import HTMLParser
from pdfminer.high_level import extract_text
from pdfminer.pdfpage import PDFPage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

PAGE_TITLES = {
    'index.html': 'Home', 'calendar.html': 'Calendar', 'sports.html': 'Athletics',
    'schedules.html': 'Schedules', 'policies.html': 'Policies', 'data.html': 'Data',
    'links.html': 'Links', 'directory.html': 'Directory', 'staff.html': 'Staff Info',
}

DOC_TITLES = {
    'master-contract-2025-27.pdf': 'Master Contract 2025-27',
    'mtss-staff-handbook.pdf': 'MTSS Staff Handbook',
    'district-job-descriptions-2025-26.pdf': 'Supplemental Job Descriptions',
    'supplemental-salary-schedule-fy26.pdf': 'FY26 Supplemental Salary Schedule',
    'fmla-employee-guide.pdf': 'FMLA Employee Guide',
    'injury-reporting-packet.pdf': 'Injury Reporting Packet',
    'eap-guidance-resources.pdf': 'Employee Assistance Program',
    'dress-code-2026-27.pdf': 'Student Dress Code',
    'lockdown-levels-and-procedures-2026-27.pdf': 'Lockdown Levels & Procedures',
    'tornado-drill-procedures-2026-27.pdf': 'Tornado Drill Procedures',
    'transportation-request-form.pdf': 'Transportation Request Form',
    'team-structures-2026-27.pdf': 'Team Structures 2026-27',
    'district-calendar-2026-27.pdf': 'District Calendar 2026-27',
    'district-calendar-2024-25.pdf': 'District Calendar 2024-25',
    'nch-hs-calendar-2026-27.pdf': 'HS Calendar Dates 2026-27',
    'c2c-teacher-resource-center.pdf': 'Crayons & Beyond Resource Center',
    'boe-vacancy-notice-and-application.pdf': 'Board Vacancy Notice & Application',
    'boe-2026-06-08-special-notice.pdf': 'Board Notice - 8 June 2026',
    'boe-2026-06-29-agenda.pdf': 'Board Agenda - 29 June 2026',
    'boe-2026-07-13-agenda.pdf': 'Board Agenda - 13 July 2026',
    'boe-2026-08-05-special-agenda.pdf': 'Board Agenda - 5 Aug 2026',
    'boe-2026-08-05-special-notice.pdf': 'Board Notice - 5 Aug 2026',
}

SKIP_IDS = {'navtoggle', 'sitenav', 'countdown', 'expandall'}
WS = re.compile(r'\s+')


def clean(s):
    return WS.sub(' ', s or '').strip()


class Sections(HTMLParser):
    """Collect text per top-level section element that carries an id."""

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.stack = []          # (id, depth_at_open)
        self.buf = {}            # id -> [text]
        self.head = {}           # id -> heading
        self.in_h = None
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style'):
            self.skip += 1
            return
        if tag not in ('br', 'hr', 'img', 'meta', 'link', 'input', 'source'):
            self.depth += 1
            i = a.get('id')
            if i and i not in SKIP_IDS:
                self.stack.append((i, self.depth))
                self.buf.setdefault(i, [])
        if tag in ('h2', 'h3', 'h4') and self.stack:
            self.in_h = tag

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
            return
        if tag == self.in_h:
            self.in_h = None
        if tag not in ('br', 'hr', 'img', 'meta', 'link', 'input', 'source'):
            while self.stack and self.stack[-1][1] >= self.depth:
                self.stack.pop()
            self.depth = max(0, self.depth - 1)

    def handle_data(self, d):
        if self.skip or not self.stack:
            return
        cur = self.stack[-1][0]
        self.buf[cur].append(' ' + d)
        if self.in_h and cur not in self.head:
            t = clean(d).lstrip('/ ').strip()
            if t:
                self.head[cur] = t


records = []

for f, page_title in PAGE_TITLES.items():
    if not os.path.exists(f):
        continue
    p = Sections()
    p.feed(open(f, encoding='utf-8').read())
    for sid, parts in p.buf.items():
        text = clean(''.join(parts))
        if len(text) < 40:
            continue
        heading = p.head.get(sid) or sid.replace('-', ' ').title()
        records.append({
            'u': f'{f}#{sid}', 'h': heading, 's': page_title, 'k': 'page',
            'x': text[:6000],
        })

scanned = []
for path in sorted(glob.glob('docs/*.pdf')):
    base = os.path.basename(path)
    title = DOC_TITLES.get(base, base.replace('-', ' ').replace('.pdf', '').title())
    try:
        n = len(list(PDFPage.get_pages(open(path, 'rb'))))
    except Exception:
        continue
    got = 0
    for i in range(n):
        try:
            t = clean(extract_text(path, page_numbers=[i]))
        except Exception:
            t = ''
        if len(t) < 40:
            continue
        got += 1
        records.append({
            'u': f'{path}#page={i + 1}', 'h': f'page {i + 1}', 's': title,
            'k': 'pdf', 'x': t[:6000],
        })
    if got == 0:
        scanned.append(base)

out = {'built': '2026-08-07', 'scanned': scanned, 'r': records}
with open('search-index.json', 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))

kb = os.path.getsize('search-index.json') / 1024
print(f'{len(records)} records '
      f'({sum(1 for r in records if r["k"] == "page")} page sections, '
      f'{sum(1 for r in records if r["k"] == "pdf")} PDF pages)')
print(f'search-index.json  {kb:,.0f} KB')
if scanned:
    print('no text layer (not searchable):', ', '.join(scanned))
