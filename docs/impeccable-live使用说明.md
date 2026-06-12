# Impeccable Live 浮动工具栏 · 中文使用说明

## 这是什么？

Impeccable Live 为**按需启用**，默认不会出现在页面上。启用后可在浏览器里**直接点选页面元素**，让 Cursor AI 生成多个视觉方案并采纳进代码。

### 如何开启（任选其一）

| 方式 | 说明 |
|------|------|
| **URL** | `http://127.0.0.1:8010/?impeccable=1`（写入 localStorage，刷新后仍有效） |
| **localStorage** | 控制台 `localStorage.setItem('impeccable-live', '1')` 后刷新 |
| **快捷键** | `Shift + Alt + I` |
| **隐藏开关** | 快速连点三次左上角「2711编辑器」品牌名 |

**关闭**：`/?impeccable=0`，或 `localStorage.removeItem('impeccable-live')` 后刷新。

**自定义 Live 端口**：`/?impeccable=1&port=8400`

> 前提：Live 服务在运行（默认端口 8400）。在项目根目录：`node .agents/skills/impeccable/scripts/live.mjs`

### Agent 设计会话

1. `node .agents/skills/impeccable/scripts/live.mjs` — 启动 Live 服务  
2. 若误注入直链 `live.js`：`node .agents/skills/impeccable/scripts/live-inject.mjs --remove`  
3. `node .agents/skills/impeccable/scripts/live-poll.mjs` — 轮询生成  
4. 浏览器打开 **`http://127.0.0.1:8010/?impeccable=1`**

加载器源码：`frontend/js/impeccable-live-loader.js`（常驻，不会自动加载 `live.js`）。

---

## 底部工具栏按钮

| 按钮 | 作用 |
|------|------|
| **点选** | 进入点选模式，鼠标移到页面上会高亮区块 |
| **插入** | 在两点之间插入全新 UI 块（高级） |
| **检测** | 扫描当前页的 AI 味 / 反模式问题 |
| **DESIGN.md** | 查看项目设计规范 |
| 输入框 | 整页级别的补充指令（Steer） |
| **退出** | 关闭 Live 模式 |

---

## 最常用流程（改某个区块的样式）

### 第 1 步：打开点选

1. 点击底部 **「点选」**
2. 把鼠标移到想改的区域（例如 Hero 标题、预览窗、能力卡片）
3. **单击**该元素

### 第 2 步：选设计动作

点选后会出现一条**浮动操作条**：

1. 点击动作名称（如 **打磨**、**更醒目**、**布局**）
2. 在输入框用中文写需求，例如：`标题更大一点，保持吉卜力治愈风`
3. 点击 **×3** 可改方案数量（默认 3 个）
4. 点 **「生成 →」**

### 第 3 步：等 AI 生成

- 状态会显示「正在生成 3 个方案…」
- **需要 Cursor 里 Agent 在跑** `live-poll.mjs` 才会真正出方案（你让 Agent 改 UI 时会自动跑）

### 第 4 步：挑选并采纳

生成完成后：

- **◀ ▶** 切换方案 1 / 2 / 3
- 满意则点 **「✓ 采纳」** → 写进 `index.html` / CSS
- 不满意点 **✕** 丢弃全部方案

---

## 设计动作速查

| 动作 | 适合什么时候用 |
|------|----------------|
| 自由描述 | 说不清类别，直接中文描述 |
| 更醒目 | 太平淡、不够抢眼 |
| 更克制 | 太花、太乱 |
| 打磨 | 快完成了，做最后一遍精修 |
| 排版 | 字号、行距、层次不对 |
| 配色 | 颜色发灰、不统一 |
| 布局 | 间距、对齐、栅格问题 |
| 动效 | 想要滚动显现、悬停反馈 |

---

## 常见问题

**Q：点了「生成」一直转圈？**  
A：需要对话里的 Agent 执行轮询。对我说：「帮我跑 Impeccable live 生成 Hero 变体」。

**Q：工具栏是英文？**  
A：本项目已切换中文词汇表；刷新页面（Ctrl+F5 一次）并确认 Live 服务已重启。

**Q：采纳后页面乱了？**  
A：点 **✕ 丢弃**，或让 Agent 从 git 恢复对应文件。

**Q：不想看到工具栏？**  
A：访问 `/?impeccable=0` 或 `localStorage.removeItem('impeccable-live')` 后刷新即可。
