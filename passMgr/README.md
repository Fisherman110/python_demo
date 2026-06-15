# Pass Manager

一个使用 PyQt 编写的本地密码管理工具。

## 功能

- 新增密码记录：平台、账号、用户名、密码、手机号、邮箱、备注
- 查询记录：支持按平台、账号、用户名、手机号、邮箱、备注关键词搜索
- 修改记录：在表格中选择记录后，在左侧表单编辑并保存
- 删除记录：可删除当前选中的记录
- 本地轻量 SQL 存储：数据保存到 `passwords.db`

## 运行

```powershell
pip install -r passMgr/requirements.txt
python passMgr/password_manager.py
```

## 说明

当前版本用于本地演示和基础管理，数据库文件保存在 `passMgr/passwords.db`。如果用于真实密码管理，建议进一步增加主密码和加密存储。
