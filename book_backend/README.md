# Book Backend

一个标准 Python 后端项目，用 FastAPI 实现图书管理系统。数据使用本地轻量 SQL 存储封装 `LightSql`，底层为 SQLite 本地数据库文件。

## 功能

- 用户认证：注册、登录、Bearer Token、查看当前用户。
- 权限逻辑：角色 `admin`、`librarian`、`member`，权限码覆盖用户、图书、借阅操作。
- 图书管理：新增、查询、详情、修改、删除。
- 借阅管理：借书、还书、查询借阅记录。
- 本地数据库：默认保存到 `book_backend/data/library.db`。

## 并发设计

目标设计：约 200 并发请求，约 2000 在线用户。

- SQLite 使用 `WAL` 模式，读请求可在写入期间继续执行。
- `LightSql` 使用有界连接池，默认 32 个连接，避免高峰请求无限创建连接。
- 写操作使用 `BEGIN IMMEDIATE` 和短事务，借书扣库存与创建借阅记录在同一个事务内完成。
- 借书接口原子检查并扣减 `available_copies`，避免并发超借。
- 对用户、图书搜索、借阅状态建立索引，降低常用查询压力。
- 认证令牌无状态，在线用户不需要服务端 session 表承载。

SQLite 适合本地文件和中小规模部署。如果后续并发写入量显著增加，可以保留 API 层和权限模型，把 `LightSql` 替换为 PostgreSQL/MySQL 存储实现。

## 安装运行

```powershell
cd book_backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API 文档：

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health`

## 默认账号

首次启动会自动创建管理员：

- 用户名：`admin`
- 密码：`admin123`

生产环境请设置环境变量 `BOOK_BACKEND_TOKEN_SECRET`，并在首次启动后修改默认密码或重新初始化管理员。

## 常用接口

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me

GET    /api/v1/books
POST   /api/v1/books
GET    /api/v1/books/{book_id}
PATCH  /api/v1/books/{book_id}
DELETE /api/v1/books/{book_id}

POST /api/v1/borrows
POST /api/v1/borrows/{borrow_id}/return
GET  /api/v1/borrows

GET  /api/v1/users
POST /api/v1/users/{user_id}/roles
```

## 权限

- `admin`: 拥有全部权限。
- `librarian`: 可管理图书和借还记录。
- `member`: 可查询图书，借还自己的图书。

权限码：

- `users:read`
- `users:write`
- `books:read`
- `books:write`
- `borrows:read`
- `borrows:write`
