#Requires -Version 5.1
<#
.SYNOPSIS
  部署 FastAPI 后端到 Render.com（需浏览器登录 Render 一次）

.STEPS
  1. 打开 https://dashboard.render.com → New → Blueprint
  2. 连接本仓库（或 fork 后连接），Render 会读取根目录 render.yaml
  3. 在 Render 服务环境变量中设置 AI_API_KEY（必填）
  4. 部署完成后复制服务 URL，例如 https://2711-editor-api.onrender.com
  5. 在 Netlify 设置环境变量 API_BACKEND_URL 为该 URL（无末尾斜杠）
  6. 重新运行: npm run deploy:netlify

  Netlify 环境变量清单:
    API_BACKEND_URL  — Render/Railway 后端 origin（推荐，自动生成 /api 代理）
    API_BASE_URL     — 可选，前端直连后端（需 backend CORS_ORIGINS 含 Netlify 域名）

  Render 后端环境变量:
    AI_API_KEY       — DeepSeek 等 OpenAI 兼容密钥（必填）
    AI_API_BASE      — 默认 https://api.deepseek.com
    AI_MODEL         — 默认 deepseek-chat
    CORS_ORIGINS     — 默认含 https://2711editor.netlify.app
#>
Write-Host "2711 Editor backend deploy helper" -ForegroundColor Cyan
Write-Host ""
Write-Host "Render Blueprint:  https://dashboard.render.com/select-repo?type=blueprint"
Write-Host "Netlify env:       https://app.netlify.com/projects/2711editor/configuration/env"
Write-Host ""
Write-Host "After Render is live, set API_BACKEND_URL and redeploy frontend:"
Write-Host "  npx netlify env:set API_BACKEND_URL https://YOUR-SERVICE.onrender.com --context production"
Write-Host "  npm run deploy:netlify"
Write-Host ""

$backendUrl = Read-Host "Paste Render backend URL (or Enter to skip)"
if ($backendUrl -and $backendUrl.Trim()) {
  $url = $backendUrl.Trim().TrimEnd("/")
  Write-Host "Setting Netlify API_BACKEND_URL=$url ..."
  npx netlify env:set API_BACKEND_URL $url --context production
  if ($LASTEXITCODE -eq 0) {
    Write-Host "Redeploying Netlify..." -ForegroundColor Green
    npm run deploy:netlify
  }
}
