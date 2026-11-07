# 英语六级真题解析 · 随身读

把去水印的六级真题解析 PDF，做成手机可直达阅读的网站。

**在线访问：** https://qqqqqqiu0804.github.io/cet6-reader/

## 内容

- 11 期解析（2021年06月 – 2026年06月），共 31 份文件、581 页、228 MB
- 每期按卷一/二/三或第一/二/三套组织
- 2025年12月的解析为单份「全三套」合订

## 特性

- **手机优先**：竖屏全宽翻页，1080px 宽灰度 JPEG，A4 比例清晰可读
- **进度记忆**：自动记录每份解析读到第几页，首页「继续阅读」一键回到上次位置
- **搜索**：按年份、月份、卷号过滤
- **PWA**：可「添加到主屏幕」，Service Worker 缓存已看页面，支持离线阅读
- **跳页 / 放大 / 目录切换**：底栏输入页码直达，右上角放大，左上角目录切换解析

## 结构

```
index.html            首页 + 阅读器（单页应用）
style.css             深色移动端样式
app.js                清单加载、渲染、翻页、进度持久化
manifest.webmanifest  PWA 清单
sw.js                 Service Worker（离线缓存）
icon.svg              图标
img/manifest.json     全部解析与页码清单
img/<slug>/NNN.jpg    逐页图片，如 img/2026-06_a1/001.jpg
tools/render.py       构建脚本（并行渲染 + 增量判断）
```

命名规则：`<年>-<月>_a<卷号>`，`a` = 解析（analysis）。

## 部署

GitHub Pages，`master` 分支根目录，已通过 `gh api ... /pages` 启用。
更新内容后 `git push` 即自动重建。

## 重新生成

用 `tools/render.py`，**并行渲染 + 增量判断**。默认只收解析。

```bash
PY='C:\Users\HXT\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'

# 日常：增量构建（没变的整份跳过，连 PDF 都不打开）
"$PY" -X utf8 tools/render.py

# 强制全量重渲
"$PY" -X utf8 tools/render.py --force

# 调整并行度（默认 min(8, CPU 核数)）
"$PY" -X utf8 tools/render.py --jobs 12

# 连真题试卷一起收
"$PY" -X utf8 tools/render.py --include-papers

# 删除 manifest 之外的残留目录
"$PY" -X utf8 tools/render.py --prune
```

脚本会重建 `img/manifest.json`，无需手工改页数。

### 增量判断逻辑

每份 PDF 记一条指纹到 `.build-state.json`（不入库）：
`文件大小 + mtime_ns + 渲染配置哈希 + 页数 + 产物完整性`。

命中顺序：

1. **跳过** —— 指纹全等且 `NNN.jpg` 齐全 → 不打开 PDF，最快
2. **采纳** —— 指纹变了但产物已完整 → 只读页数，不重渲（首次运行即走这条）
3. **渲染** —— 其余情况，含「少了一页」这类残缺

改动渲染参数（`WIDTH`/`QUALITY`/`GRAY`）会让配置哈希变化，自动触发全量重渲。

### 实测性能

| 场景 | 耗时 |
|---|---|
| 全量重渲 581 页（8 并行） | **6.95 s** |
| 全量重渲 581 页（原单线程） | ~45 s |
| 无改动，二次运行 | **0.01 s** |
| 单份内容更新 | ~1.2 s |
| 单份缺 1 页 | ~1.2 s |

并行提速约 **6.5 倍**。瓶颈从 CPU 转移到磁盘 I/O。

## 已知取舍

- 只收录解析，不含真题试卷（原需求仅要解析）。需要真题时加 `--include-papers` 重跑。
- 原 PDF 为纯图片扫描件，无文字层，因此站点是页面图片阅读器，不支持文字选择与检索。
- GitHub Pages 为静态托管，无法按需渲染；页面在构建阶段一次性生成。
- `pdftoppm` 单进程内部仍是串行，并行靠多进程；`--jobs` 超过 CPU 核数收益递减。

