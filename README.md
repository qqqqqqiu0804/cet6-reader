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
```

命名规则：`<年>-<月>_a<卷号>`，`a` = 解析（analysis）。

## 部署

GitHub Pages，`master` 分支根目录，已通过 `gh api ... /pages` 启用。
更新内容后 `git push` 即自动重建。

## 重新生成

源 PDF 变动后，用 `pdftoppm` 重新渲染：

```bash
pdftoppm -scale-to-x 1080 -gray -jpeg -jpegopt quality=80 -f 1 -l <页数> input.pdf img/<slug>/<slug>-
```

再把 `img/<slug>/<slug>-NN.jpg` 重命名为 `NNN.jpg`，并同步 `img/manifest.json` 的 `pages`。

## 已知取舍

- 只收录解析，不含真题试卷（原需求仅要解析）。如需真题，重新渲染 `_p` 系列目录并补回 manifest 即可。
- 原 PDF 为纯图片扫描件，无文字层，因此站点是页面图片阅读器，不支持文字选择与检索。
- GitHub Pages 为静态托管，无法按需渲染；页面在构建阶段一次性生成。
