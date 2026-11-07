# 英语六级真题 · 解析随身读

把去水印的六级真题 PDF 解析，做成手机可直达阅读的网站。

**在线访问：** https://qqqqqqiu0804.github.io/cet6-reader/

## 内容

- 11 期真题（2021年06月 – 2026年06月），共 64 份文件、878 页
- 每期包含「答案解析」与「真题试卷」两类，按卷一/二/三或第一/二/三套组织

## 特性

- **手机优先**：竖屏全宽翻页，1080px 宽灰度 JPEG，A4 比例清晰可读
- **进度记忆**：自动记录每份试卷读到第几页，首页「继续阅读」一键回到上次位置
- **搜索**：按年份、月份、卷号过滤
- **PWA**：可「添加到主屏幕」，Service Worker 缓存已看页面，支持离线阅读
- **跳页 / 放大 / 目录切换**：底栏输入页码直达，右上角放大，左上角目录切换试卷

## 结构

```
index.html            首页 + 阅读器（单页应用）
style.css             深色移动端样式
app.js                清单加载、渲染、翻页、进度持久化
manifest.webmanifest  PWA 清单
sw.js                 Service Worker（离线缓存）
icon.svg              图标
img/manifest.json     全部试卷与页码清单
img/<slug>/NNN.jpg    逐页图片，如 img/2026-06_a1/001.jpg
```

命名规则：`<年>-<月>_<a|p><卷号>`，`a` = 解析（analysis），`p` = 真题（paper）。

## 部署

GitHub Pages，`master` 分支根目录，已通过 `gh api ... /pages` 启用。
更新内容后 `git push` 即自动重建。

## 重新生成

源 PDF 变动后，用 `pdftoppm` 重新渲染：

```bash
pdftoppm -scale-to-x 1080 -gray -jpeg -jpegopt quality=80 -f 1 -l <页数> input.pdf img/<slug>/<slug>-
```

再把 `img/<slug>/<slug>-NN.jpg` 重命名为 `NNN.jpg`，并同步 `img/manifest.json` 的 `pages`。
