# 彩票历史开奖分析工具

本项目是一个本地网页应用，用于自动查询并分析双色球、快乐8、福彩3D的历史开奖号码。

> 提醒：彩票开奖结果具有随机性，本工具只提供历史统计和辅助选号参考，不保证中奖。

## 功能

- 官方优先抓取中国福彩网历史开奖数据
- SQLite 本地存储开奖期号、日期、号码、来源和抓取时间
- 双色球、快乐8、福彩3D历史开奖表
- 冷热号、遗漏期数、和值、奇偶、大小、区间等统计
- 基于统计评分的候选号码推荐
- FastAPI 后端接口 + React/Vite 前端页面

## 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 打开前端

```powershell
cd "D:\AI CODE\lottery\frontend"
.\index.html
```

前端是免构建的静态页面，不需要安装 Node.js/npm。也可以直接在资源管理器中双击 `frontend/index.html`。

前端默认请求后端地址：`http://127.0.0.1:8000`。

## API

- `GET /api/lottery/{type}/draws`
- `POST /api/lottery/{type}/sync`
- `GET /api/lottery/{type}/stats?window=30`
- `GET /api/lottery/{type}/recommend?count=5`

彩种标识：

- `ssq`：双色球
- `kl8`：快乐8
- `fc3d`：福彩3D
