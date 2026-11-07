#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CET6 解析站构建管线 —— 并行渲染 + 增量判断

默认行为
  1. 扫描源目录，按文件名分类（解析 / 真题试卷）
  2. 默认只收「解析」；--include-papers 才连真题一起收
  3. 增量：比对 (size, mtime_ns, 渲染配置哈希, 页数, 产物完整性)
     命中则整份跳过，连 PDF 都不打开
  4. 首次运行若产物已存在且完整，自动「采纳」（adopt），不重渲
  5. 并行：ThreadPoolExecutor 跑多个 pdftoppm 子进程
  6. 重建 img/manifest.json

用法
  python tools/render.py                     # 增量构建
  python tools/render.py --force             # 强制全量重渲
  python tools/render.py --jobs 8            # 并行度（默认 min(8, CPU)）
  python tools/render.py --include-papers    # 连真题试卷一起收
  python tools/render.py --prune             # 删除 manifest 之外的残留目录
  python tools/render.py --src <源> --site <站>   # 换目录（测试用）
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pypdf

# ---------------------------------------------------------------- 默认路径
DEFAULT_SRC = r'C:\Users\HXT\Downloads\英语六级真题PDF_去水印'
DEFAULT_SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDFTOPPM = r'C:\Users\HXT\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdftoppm.exe'

# ---------------------------------------------------------------- 渲染参数
WIDTH = 1080
QUALITY = 80
GRAY = True

CN_NUM = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
          '六': 6, '七': 7, '八': 8, '九': 9}


def cfg_hash():
    raw = f'{WIDTH}|{QUALITY}|{GRAY}'
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def mb(n):
    return n / 1024 / 1024


# ---------------------------------------------------------------- 分类
def volume_of(name):
    m = re.search(r'第([一二三四五六七八九])套', name)
    if m:
        return CN_NUM.get(m.group(1), 0)
    m = re.search(r'卷([一二三四五六七八九])', name)
    if m:
        return CN_NUM.get(m.group(1), 0)
    if '全三套' in name or '全三' in name:
        return 0
    return 0


def clean_label(name):
    n = name
    for pre in ('大学英语6级', '大学英语六级', '英语六级'):
        n = n.replace(pre, '')
    n = re.sub(r'\.pdf$', '', n, flags=re.I)
    return re.sub(r'\s+', ' ', n).strip()


def classify(fn):
    """返回 (type, volume)；type ∈ {analysis, paper}"""
    analysis = ('解析' in fn) or ('答案' in fn)
    return ('analysis' if analysis else 'paper'), volume_of(fn)


# ---------------------------------------------------------------- 发现
def discover(src, include_papers):
    """返回 [(sortkey, label, pdf_path, slug, type, volume, display_name)]"""
    out = []
    for d in sorted(os.listdir(src)):
        dp = os.path.join(src, d)
        if not os.path.isdir(dp):
            continue
        m = re.search(r'(20\d\d)年(\d+)月', d)
        if not m:
            continue
        year, month = int(m.group(1)), int(m.group(2))
        label = f'{year}年{month:02d}月'
        for fn in sorted(os.listdir(dp)):
            if not fn.lower().endswith('.pdf'):
                continue
            typ, vol = classify(fn)
            if typ == 'paper' and not include_papers:
                continue
            slug = f'{year}-{month:02d}_{"a" if typ == "analysis" else "p"}{vol}'
            out.append({
                'sortkey': year * 100 + month,
                'label': label, 'year': year, 'month': month,
                'path': os.path.join(dp, fn),
                'slug': slug, 'type': typ, 'volume': vol,
                'name': clean_label(fn),
            })
    out.sort(key=lambda r: (-r['sortkey'],
                            0 if r['type'] == 'analysis' else 1,
                            r['volume']))
    return out


# ---------------------------------------------------------------- 产物检查
def expected_names(pages):
    return {'%03d.jpg' % i for i in range(1, pages + 1)}


def outdir_complete(outdir, pages):
    if not os.path.isdir(outdir):
        return False
    try:
        actual = set(os.listdir(outdir))
    except OSError:
        return False
    return actual == expected_names(pages)


def count_pages(pdf):
    return len(pypdf.PdfReader(pdf).pages)


# ---------------------------------------------------------------- 渲染单份
def render_one(job):
    """job: dict(path, slug, pages, outdir) → (slug, ok, sec, err)"""
    path, slug, pages, outdir = job['path'], job['slug'], job['pages'], job['outdir']
    t0 = time.perf_counter()
    # 临时目录建在目标盘上，避免跨盘 copy 的额外 I/O
    os.makedirs(outdir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='cet6_', dir=os.path.dirname(outdir))
    try:
        flags = ['-scale-to-x', str(WIDTH)]
        if GRAY:
            flags.append('-gray')
        flags += ['-jpeg', '-jpegopt', f'quality={QUALITY}',
                  '-f', '1', '-l', str(pages)]
        r = subprocess.run([PDFTOPPM] + flags + [path, os.path.join(tmp, 'pg')],
                           capture_output=True)
        if r.returncode != 0:
            return slug, False, time.perf_counter() - t0, \
                r.stderr.decode('utf-8', 'ignore')[:200]

        produced = {}
        for fn in os.listdir(tmp):
            m = re.search(r'-(\d+)\.jpg$', fn)
            if m:
                produced[int(m.group(1))] = os.path.join(tmp, fn)
        if len(produced) != pages:
            return slug, False, time.perf_counter() - t0, \
                f'页数不符 期望{pages} 实际{len(produced)}'

        os.makedirs(outdir, exist_ok=True)
        # 清掉旧命名与多余文件
        keep = expected_names(pages)
        for fn in os.listdir(outdir):
            if fn not in keep:
                try:
                    os.remove(os.path.join(outdir, fn))
                except OSError:
                    pass
        for i, srcp in produced.items():
            dst = os.path.join(outdir, '%03d.jpg' % i)
            # 跨盘（C: → E:）时 os.replace 会失败，shutil.move 会退化为 copy+delete
            try:
                os.replace(srcp, dst)
            except OSError:
                shutil.move(srcp, dst)
        return slug, True, time.perf_counter() - t0, None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=DEFAULT_SRC)
    ap.add_argument('--site', default=DEFAULT_SITE)
    ap.add_argument('--jobs', type=int, default=min(8, os.cpu_count() or 4))
    ap.add_argument('--force', action='store_true', help='强制全量重渲')
    ap.add_argument('--include-papers', action='store_true', help='连真题试卷一起收')
    ap.add_argument('--prune', action='store_true', help='删除 manifest 之外的残留目录')
    ap.add_argument('--no-adopt', action='store_true', help='禁用自动采纳已有产物')
    args = ap.parse_args()

    src = os.path.abspath(args.src)
    site = os.path.abspath(args.site)
    img = os.path.join(site, 'img')
    state_path = os.path.join(site, '.build-state.json')
    manifest_path = os.path.join(img, 'manifest.json')

    os.makedirs(img, exist_ok=True)

    t_start = time.perf_counter()

    # ---- 载入状态
    state = {}
    if os.path.exists(state_path):
        try:
            state = json.load(open(state_path, encoding='utf-8'))
        except Exception:
            state = {}
    ch = cfg_hash()

    # ---- 发现
    files = discover(src, args.include_papers)
    if not files:
        print('没有找到可渲染的 PDF')
        return 1
    print(f'发现 {len(files)} 份 PDF  →  {site}')
    print(f'渲染参数 width={WIDTH} quality={QUALITY} gray={GRAY} cfg={ch}')
    print(f'并行度 jobs={args.jobs}  force={args.force}\n')

    # ---- 分流：跳过 / 采纳 / 渲染
    skip, adopt, todo = [], [], []
    for f in files:
        st = os.stat(f['path'])
        f['outdir'] = os.path.join(img, f['slug'])
        rec = state.get(f['slug'])
        f['size'] = st.st_size
        f['mtime'] = st.st_mtime_ns

        # 快路径：指纹一致 + 产物完整 → 连 PDF 都不打开
        if (not args.force and rec
                and rec.get('size') == f['size']
                and rec.get('mtime_ns') == f['mtime']
                and rec.get('cfg') == ch
                and rec.get('pages')
                and outdir_complete(f['outdir'], rec['pages'])):
            f['pages'] = rec['pages']
            skip.append(f)
            continue

        # 需要知道页数：读一次 PDF
        f['pages'] = count_pages(f['path'])

        # 首次运行但产物已存在且完整 → 采纳，不重渲
        if (not args.force and not args.no_adopt
                and outdir_complete(f['outdir'], f['pages'])):
            adopt.append(f)
            continue

        todo.append(f)

    # ---- 并行渲染
    rendered, failed = [], []
    if todo:
        print(f'开始渲染 {len(todo)} 份 ...')
        t_r = time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            futs = {ex.submit(render_one, f): f for f in todo}
            done = 0
            for fut in as_completed(futs):
                f = futs[fut]
                slug, ok, sec, err = fut.result()
                done += 1
                if ok:
                    rendered.append(f)
                    print(f'  [{done}/{len(todo)}] {slug}  {f["pages"]:>3}页  {sec:5.2f}s')
                else:
                    failed.append((slug, err))
                    print(f'  [{done}/{len(todo)}] {slug}  失败: {err}')
        print(f'渲染耗时 {time.perf_counter() - t_r:.1f}s')

    # ---- 更新状态
    for f in skip + adopt + rendered:
        state[f['slug']] = {
            'size': f['size'], 'mtime_ns': f['mtime'],
            'cfg': ch, 'pages': f['pages'], 'type': f['type'],
        }
    # 清掉不再收录的条目
    alive = {f['slug'] for f in files}
    for slug in list(state):
        if slug not in alive:
            del state[slug]

    json.dump(state, open(state_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # ---- 重建 manifest
    terms = {}
    for f in files:
        terms.setdefault((f['sortkey'], f['label']), []).append(f)

    manifest = {'title': '英语六级真题解析 · 随身读', 'generated': '',
                'terms': [], 'totalPages': 0, 'totalFiles': 0}
    total_pages = 0
    for (sk, label) in sorted(terms, reverse=True):
        group = terms[(sk, label)]
        entry = {'label': label, 'year': group[0]['year'],
                 'month': group[0]['month'], 'files': []}
        for f in group:
            entry['files'].append({
                'slug': f['slug'], 'type': f['type'], 'volume': f['volume'],
                'name': f['name'], 'pages': f['pages'],
                'dir': f'img/{f["slug"]}',
            })
            total_pages += f['pages']
        manifest['terms'].append(entry)
    manifest['totalPages'] = total_pages
    manifest['totalFiles'] = len(files)

    json.dump(manifest, open(manifest_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

    # ---- 残留目录
    referenced = {f['slug'] for f in files}
    on_disk = {n for n in os.listdir(img)
               if os.path.isdir(os.path.join(img, n))}
    stale = sorted(on_disk - referenced)
    pruned = []
    if stale and args.prune:
        for s in stale:
            shutil.rmtree(os.path.join(img, s), ignore_errors=True)
            pruned.append(s)

    # ---- 统计
    total_bytes = 0
    for f in files:
        d = f['outdir']
        if os.path.isdir(d):
            total_bytes += sum(os.path.getsize(os.path.join(d, x))
                               for x in os.listdir(d))
    elapsed = time.perf_counter() - t_start

    print()
    print('=' * 58)
    print(f'  跳过(未变)   {len(skip):>3} 份')
    print(f'  采纳(已存在) {len(adopt):>3} 份')
    print(f'  本次渲染     {len(rendered):>3} 份')
    print(f'  失败         {len(failed):>3} 份')
    print(f'  合计         {len(files):>3} 份 / {total_pages} 页 / {mb(total_bytes):.1f} MB')
    print(f'  总耗时       {elapsed:.2f}s')
    if stale and not args.prune:
        print(f'  残留目录     {len(stale)} 个（加 --prune 删除）: {", ".join(stale[:6])}')
    elif pruned:
        print(f'  已清理残留   {len(pruned)} 个: {", ".join(pruned[:6])}')
    print('=' * 58)

    if failed:
        for slug, err in failed:
            print(f'  失败 {slug}: {err}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
