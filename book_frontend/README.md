# 星辉图书馆前端

基于 Vue 3 + Vite 的图书管理系统前端，界面采用深色星云、玻璃拟态和发光卡片风格。

## 功能

- 管理员登录
- 馆藏统计仪表盘
- 图书搜索、列表展示
- 图书新增、编辑、删除
- 借书、还书
- 借阅记录展示
- 根据后端权限控制维护按钮

## 运行

先启动后端：

```powershell
cd ../book_backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

再启动前端：

```powershell
cd ../book_frontend
npm install
npm run dev
```

默认后端地址为 `http://127.0.0.1:8000/api/v1`。如需修改：

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000/api/v1"
npm run dev
```

默认管理员账号：`admin / admin123`。

## 构建

```powershell
npm run build
```
