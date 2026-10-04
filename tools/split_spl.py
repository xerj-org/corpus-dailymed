#!/usr/bin/env python3
"""Split DailyMed SPL label XML into one text file per titled <section>.

Input:  raw/<SETID>.xml  (downloaded from /dailymed/services/v2/spls/<SETID>.xml)
        listpages/page-N.json (SPL list, for title fallback)
Output: <out>/<setid[0:2]>/<SETID>__<slug>.txt
        header: "DailyMed <SETID> | <drug name(s)> | <section title>[ | truncated]"
Rules:  skip labels >2MB; no output file >150KB (body truncated, noted in header);
        text is verbatim label text (XML tags stripped), not paraphrased.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

V3 = '{urn:hl7-org:v3}'
RAW = Path('raw')
LIST = Path('listpages')
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/root/dm-build/corpus')

MAX_FILE = 150 * 1024
MAX_XML = 2 * 1024 * 1024
BLOCK_END = {'paragraph', 'list', 'item', 'table', 'caption', 'thead',
             'tbody', 'tfoot', 'tr', 'footnote', 'br'}
CELL = {'td', 'th'}
DRUG_NAME_MAX = 300
SLUG_MAX = 80


def local(tag):
    return tag.split('}')[-1] if isinstance(tag, str) else ''


def ser(el, out):
    """Serialize an element's text content; newlines after block elements,
    ' | ' after table cells (structure preserved, words verbatim)."""
    tag = local(el.tag)
    if tag == 'br':
        out.append('\n')
    if el.text:
        out.append(el.text)
    for child in el:
        ctag = local(child.tag)
        ser(child, out)
        if ctag in CELL:
            out.append(' | ')
        if ctag in BLOCK_END:
            out.append('\n')
        if child.tail:
            out.append(child.tail)
    if tag in BLOCK_END:
        out.append('\n')


def clean(s):
    s = s.replace('\x00', '').replace('\r', '')
    s = re.sub(r'[ \t]+\n', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def title_text(tel):
    return re.sub(r'\s+', ' ', ''.join(tel.itertext())).strip()


def slugify(t):
    s = re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')
    s = re.sub(r'-{2,}', '-', s)[:SLUG_MAX].strip('-')
    return s or 'untitled'


def main():
    # setid -> list title (fallback drug name)
    list_title = {}
    for p in sorted(LIST.glob('page-*.json')):
        for e in json.loads(p.read_text())['data']:
            list_title[e['setid']] = e['published_date'] and e['title'] or e['title']

    stats = {'labels': 0, 'skip_oversize': 0, 'skip_parse': 0, 'skip_missing': 0,
             'files': 0, 'truncated': 0, 'empty_sections': 0, 'no_drug_name': 0}
    title_dist = {}
    raws = sorted(RAW.glob('*.xml'))
    for path in raws:
        setid = path.name[:-4]
        stats['labels'] += 1
        if path.stat().st_size > MAX_XML:
            stats['skip_oversize'] += 1
            continue
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            stats['skip_parse'] += 1
            continue
        # drug name(s): direct <name> child of manufacturedProduct (finished
        # product name), falling back to manufacturedMaterial/name, deduped,
        # document order. Nested ingredient names are deliberately excluded.
        names = []
        for tag in ('manufacturedProduct', 'manufacturedMaterial'):
            for mp in root.iter(V3 + tag):
                nm = mp.find(V3 + 'name')
                if nm is None:
                    continue
                t = re.sub(r'\s+', ' ', ''.join(nm.itertext())).strip()
                if t and t not in names:
                    names.append(t)
        if not names:
            stats['no_drug_name'] += 1
            names = [list_title.get(setid, 'unknown')]
        drug = '; '.join(names)
        if len(drug) > DRUG_NAME_MAX:
            drug = drug[:DRUG_NAME_MAX - 1] + '…'

        for sec in root.iter(V3 + 'section'):
            tel = sec.find(V3 + 'title')
            if tel is None:
                continue
            stitle = title_text(tel)
            if not stitle or len(stitle) > 300:
                continue
            body_el = sec.find(V3 + 'text')
            out = []
            if body_el is not None:
                ser(body_el, out)
            body = clean(''.join(out))
            if not body:
                stats['empty_sections'] += 1
                continue
            title_dist[stitle] = title_dist.get(stitle, 0) + 1

            trunc = ''
            head = f'DailyMed {setid} | {drug} | {stitle}'
            blob = (head + '\n\n' + body).encode('utf-8')
            if len(blob) > MAX_FILE:
                trunc = f' | [section truncated from {len(body)} chars to fit 150KB]'
                head += trunc
                keep = MAX_FILE - len((head + '\n\n').encode('utf-8'))
                body = body.encode('utf-8')[:keep].decode('utf-8', 'ignore').rstrip()
                blob = (head + '\n\n' + body).encode('utf-8')
                stats['truncated'] += 1

            d = OUT / setid[:2]
            d.mkdir(parents=True, exist_ok=True)
            slug = slugify(stitle)
            f = d / f'{setid}__{slug}.txt'
            n = 2
            while f.exists():
                f = d / f'{setid}__{slug}-{n}.txt'
                n += 1
            f.write_bytes(blob)
            stats['files'] += 1

    stats['setids_in_list'] = len(list_title)
    print(json.dumps(stats, indent=1))
    top = sorted(title_dist.items(), key=lambda kv: -kv[1])[:25]
    print('TOP TITLES:')
    for t, n in top:
        print(f'{n:6d}  {t}')
    tot = sum(title_dist.values())
    print(f'distinct titles: {len(title_dist)}, total titled sections: {tot}')


if __name__ == '__main__':
    main()
