# TeamMatch —— 课程项目组队匹配系统

> 后端开发完成 | 前端待开发 | 文档齐全

## 项目简介

面向在校学生的**课程项目智能组队平台**。学生可自主发布课程项目需求，系统基于**技能标签重合度**智能推荐适配队友，支持申请入组、组长审批、进度管控全流程线上化。

## 项目结构

```
team-match/
├── backend/          ← 后端源码（PHP + MySQL，已开发完成）
├── frontend/         ← 前端源码（待成员A开发）
├── docs/             ← 项目文档（开发方案、ER图、前端对接文档）
└── .gitignore
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | PHP 7.4+, MySQL, PDO |
| 前端 | HTML5, CSS3, Bootstrap, jQuery |
| 开发环境 | phpStudy |

## 快速启动

1. 将 `backend/` 放入 phpStudy 的 `WWW/` 目录
2. 执行 `backend/sql/` 下的3个SQL脚本建库建表
3. 修改 `backend/config/database.php` 数据库密码
4. 访问 `http://localhost/backend/api/courses` 验证

## 核心API

| 接口 | 说明 |
|------|------|
| `POST /api/user/register` | 用户注册 |
| `POST /api/user/login` | 用户登录 |
| `GET /api/projects` | 项目列表（支持筛选搜索分页） |
| `POST /api/projects` | 发布新项目 |
| `POST /api/projects/{id}/apply` | 发起入组申请 |
| `PUT /api/applications/{id}/handle` | 审批申请（通过/拒绝） |
| `GET /api/recommendations` | ★ 智能匹配推荐 |

## 文档

- [后端开发方案](docs/后端开发方案.md)
- [数据库ER图与设计文档](docs/后端ER图文档.md)
- [前端对接文档](docs/前端对接文档.md)
