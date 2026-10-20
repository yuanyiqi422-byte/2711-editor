# 2711编辑器 · 部署说明

## 架构

| 组件 | 托管 | 说明 |
|------|------|------|
| **前端** | Cloudflare Pages | 静态 HTML/CSS/JS（`frontend/`） |
| **后端 API** | Render | FastAPI + LLM，`https://two711-editor-api.onrender.com` |

Cloudflare Pages **只托管静态资源**（与 Netlify 同类）。浏览器通过 `frontend/js/env-config.js` 中的 `__API_BASE__` **直连 Render**，不经过 Pages 的 `/api` 代理（SSE 长连接会被截断）。

---

## Cloudflare Pages（推荐）

### Dashboard Git 集成（一次性）

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/) → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. 选择仓库 `yuanyiqi422-byte/2711-editor`，分支 `main`
3. 构建设置：

   | 项 | 值 |
   |---|---|
   | Build command | `node scripts/inject-env-config.mjs` |
   | Build output directory | `frontend` |
   | Root directory | `/`（仓库根） |

4. **Environment variables**（Production）：

   ```
   API_BACKEND_URL=https://two711-editor-api.onrender.com
   ```

   > `CF_PAGES=1` 由 Cloudflare 自动注入，无需手动设置。

5. 保存并 Deploy。生产 URL 通常为 `https://2711editor.pages.dev`。

### CLI 直传（无需 Git 集成）

```powershell
npx wrangler login          # 首次需浏览器授权
npm run deploy:cloudflare   # inject + wrangler pages deploy
```

### SPA 路由

`scripts/inject-env-config.mjs` 会在 `frontend/_redirects` 写入：

```
/* /index.html 200
```

Cloudflare Pages 支持 Netlify 格式的 `_redirects` 文件。

---

## Render 后端

- 服务：`two711-editor-api` → `https://two711-editor-api.onrender.com`
- 推送 `main` 后 Render 自动 redeploy
- CORS 已允许 `*.2711editor.pages.dev` 与 `2711editor.pages.dev`
- 自定义域名可在 Render 环境变量 `CORS_ORIGINS` 追加，例如 `https://editor.example.com`

---

## 验证清单

```powershell
# 1. 前端 env-config
curl https://2711editor.pages.dev/js/env-config.js

# 2. 后端健康
curl https://two711-editor-api.onrender.com/api/health

# 3. CORS 预检（将 Origin 换成实际 Pages URL）
curl -i -X OPTIONS https://two711-editor-api.onrender.com/api/health ^
  -H "Origin: https://2711editor.pages.dev" ^
  -H "Access-Control-Request-Method: GET"
```

期望：`env-config.js` 含 `"https://two711-editor-api.onrender.com"`；health 返回 `{"ok":...}`；OPTIONS 含 `access-control-allow-origin`。

---

## Render 免费实例保活（可选）

Render 免费 tier 约 **15 分钟无请求** 后会休眠；冷启动通常需 **30～90 秒**。前端已在页面加载时后台 ping `/api/health`，并在点击「开始游戏」时 **自动重试连接**（最多约 8 次，单次超时 90 秒），无需用户手动等待。

若仍频繁遇到唤醒延迟，可用 **外部免费 cron** 每 10～14 分钟 ping 一次（仅 health，不调用 LLM，几乎零成本）：

| 服务 | 设置 |
|------|------|
| [UptimeRobot](https://uptimerobot.com/) | Monitor type: HTTP(s)，URL: `https://two711-editor-api.onrender.com/api/health`，Interval: 5 min（免费档） |
| [cron-job.org](https://cron-job.org/) | URL 同上，Schedule: `*/14 * * * *`（每 14 分钟） |

> 注意：过于频繁（如每分钟）的 ping 可能触发 Render 公平使用限制；10～14 分钟间隔足够避免大多数冷启动。

---

## Netlify（已停用）

原站点 `https://2711editor.netlify.app` 因额度暂停。配置仍保留在 `netlify.toml` 供参考，生产请使用 Cloudflare Pages。
