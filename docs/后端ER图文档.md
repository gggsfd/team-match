# 课程项目组队匹配系统（TeamMatch）—— 数据库ER图与设计文档

> **文档版本**：v1.2（修正版——新增关系模式、分块ER图）
> **数据库**：MySQL 8.0 / 5.7+
> **数据库名**：`team_match`
> **字符集**：`utf8mb4` / `utf8mb4_unicode_ci`
> **引擎**：InnoDB

---

## 一、关系模式（Relation Schema）★ 答辩必用

> 约定：`<u>`下划线`</u>` = 主键，`<i>`斜体`</i>` = 外键，`PK` = 主键，`FK` = 外键

### 1.1 基本实体（4个）

```
① User（用户）
   User(<u>uid</u>, username, password, nickname, email, phone, avatar, credit_score, created_at, updated_at, is_deleted)
   PK: uid
   UK: username

② Course（课程）
   Course(<u>cid</u>, cname, teacher, semester, description, created_at, updated_at, is_deleted)
   PK: cid

③ Skill（技能标签）
   Skill(<u>sid</u>, sname, category, created_at)
   PK: sid
   UK: sname

④ Project（项目）
   Project(<u>pid</u>, <i>cid</i>, <i>uid</i>, pname, description, max_members, status, deadline, created_at, updated_at, is_deleted)
   PK: pid
   FK: cid → Course(cid), uid → User(uid)   （uid = 项目组长）
```

### 1.2 关联实体 / 中间表（5个）

```
⑤ UserSkill（用户-技能 多对多中间表）
   UserSkill(<u><i>uid</i></u>, <u><i>sid</i></u>, proficiency, created_at)
   PK: (uid, sid)
   FK: uid → User(uid), sid → Skill(sid)

⑥ ProjectSkill（项目-技能 多对多中间表）
   ProjectSkill(<u><i>pid</i></u>, <u><i>sid</i></u>, required_count, created_at)
   PK: (pid, sid)
   FK: pid → Project(pid), sid → Skill(sid)

⑦ Member（项目成员 关联实体）
   Member(<u>mid</u>, <i>pid</i>, <i>uid</i>, role, join_time, created_at)
   PK: mid
   UK: (pid, uid)  ← 同一用户在同一项目仅一个角色
   FK: pid → Project(pid), uid → User(uid)

⑧ Application（组队申请 关联实体）
   Application(<u>aid</u>, <i>pid</i>, <i>uid</i>, message, status, apply_time, handle_time, created_at, updated_at)
   PK: aid
   FK: pid → Project(pid), uid → User(uid)
   ※ 不设(pid,uid)唯一约束，代码层校验防重复待处理申请

⑨ Progress（进度节点 关联实体）
   Progress(<u>prid</u>, <i>pid</i>, title, description, status, deadline, created_at, updated_at)
   PK: prid
   FK: pid → Project(pid)
```

---

## 二、ER图（分块展示，清晰可读）

### 2.1 图A：核心关系（User / Skill / Course / Project）

```
┌──────────────────────────────────────────────────────────┐
│                  ★ 核心关系图 A                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐         ┌──────────────┐       ┌──────────┐│
│  │   User   │ 1 ─── N │  UserSkill   │ N ── 1│  Skill   ││
│  │──────────│         │──────────────│       │──────────││
│  │ uid  PK  │         │ uid   FK PK  │       │ sid  PK  ││
│  │ username │         │ sid   FK PK  │       │ sname    ││
│  │ nickname │         │ proficiency  │       │ category ││
│  │ ...      │         └──────────────┘       └──────────┘│
│  └────┬─────┘                                             │
│       │ 1                                                 │
│       │                                                   │
│       │   ┌──────────────────────────────┐                │
│       │   │ ProjectSkill（多对多中间表）    │                │
│       │   │ pid FK PK, sid FK PK         │                │
│       │   │ required_count               │                │
│       │   └────────┬──────────┬──────────┘                │
│       │            │ N        │ N                         │
│       │   ┌────────▼──┐ ┌─────▼──────┐                   │
│       │   │  Project  │ │   Skill    │ (同上)             │
│       │   │───────────│ └────────────┘                   │
│       │   │ pid  PK   │                                   │
│       N   │ uid  FK ──┼──── 组长（创建者）                 │
│       │   │ cid  FK   │                                   │
│       │   │ pname     │                                   │
│       │   │ status    │                                   │
│       │   │ deadline  │                                   │
│       │   └───────────┘                                   │
│       │        │ 1                                         │
│       │        │                          ┌──────────┐    │
│       │        └──────────────────────────│  Course  │    │
│       │                      N            │──────────│    │
│       │                                   │ cid  PK  │    │
│       │                                   │ cname    │    │
│       │                                   │ semester │    │
│       │                                   └──────────┘    │
│       │                                                    │
└───────┼────────────────────────────────────────────────────┘
        │
        │  说明：User 与 Project 之间有两条路径：
        │  ① User.uid ──(1:N)──→ Project.uid（组长创建项目）
        │  ② User ──(1:N)── Member ──(N:1)── Project（正式成员，见下图B）
```

### 2.2 图B：从属关系（Member / Application / Progress）

```
┌──────────────────────────────────────────────────────────────┐
│                  ★ 从属关系图 B                               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│         ┌──────────┐                                         │
│         │   User   │                                         │
│         │ uid  PK  │                                         │
│         └────┬─────┘                                         │
│              │                                               │
│        1     │     1                                         │
│    ┌─────────┼─────────┐                                     │
│    N         │         N                                     │
│    ▼         │         ▼                                     │
│ ┌──────┐     │    ┌──────────┐                                │
│ │Member│     │    │Applica-  │                               │
│ │──────│     │    │  tion    │                                │
│ │mid PK│     │    │──────────│                               │
│ │pid FK│     │    │aid  PK   │                                │
│ │uid FK│──N──┼──1─│uid  FK   │                               │
│ │role  │     │    │pid  FK   │                                │
│ └──┬───┘     │    │message   │                                │
│    │ N       │    │status    │                                │
│    │         │    └────┬─────┘                               │
│    │         │         │ N                                    │
│    │         │    ┌────┴─────┐                                │
│    │         │    │ 1        │ 1                              │
│    │    ┌────▼────▼─┐        │                                │
│    │    │  Project  │        │                                │
│    │    │───────────│◄───────┘                                │
│    └───►│ pid  PK   │                                         │
│         └─────┬─────┘                                         │
│               │ 1                                             │
│               N                                               │
│         ┌─────▼──────┐                                        │
│         │  Progress  │                                        │
│         │────────────│                                        │
│         │ prid  PK   │                                        │
│         │ pid   FK   │                                        │
│         │ title      │                                        │
│         │ status     │                                        │
│         │ deadline   │                                        │
│         └────────────┘                                        │
│                                                              │
│   关键理解：                                                  │
│   • User ─(1:N)─ Member ─(N:1)─ Project  → User N:M Project │
│   • User ─(1:N)─ Application ─(N:1)─ Project → User N:M Proj │
│   • 申请通过后：Application(已接受) → 写入 Member → 不再申请  │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 完整关系一览表

| 序号 | 实体A                 | 实体B       |        类型        | 中间实现               | 业务含义                   |
| :--: | --------------------- | ----------- | :----------------: | ---------------------- | -------------------------- |
|  ①  | User                  | Skill       |  **N : M**  | UserSkill 中间表       | 学生掌握多项技能           |
|  ②  | Project               | Skill       |  **N : M**  | ProjectSkill 中间表    | 项目需要多项技能           |
|  ③  | User                  | Project     |  **N : M**  | Member 中间表          | 学生正式加入项目（审批后） |
|  ④  | User                  | Project     |  **N : M**  | Application 中间表     | 学生临时申请项目（审批前） |
|  ⑤  | User                  | Project     |  **1 : N**  | `project.uid` FK     | 学生作为组长创建项目       |
|  ⑥  | Course                | Project     |  **1 : N**  | `project.cid` FK     | 一门课程下有多个项目       |
|  ⑦  | Project               | Progress    |  **1 : N**  | `progress.pid` FK    | 一个项目有多个进度节点     |
|  ⑧  | Project               | Member      |  **1 : N**  | `member.pid` FK      | 一个项目有多个成员         |
|  ⑨  | Project               | Application |  **1 : N**  | `application.pid` FK | 一个项目收到多个申请       |
|  ⑩  | Application → Member | —          | **1 : 0..1** | 审批通过后转换         | 申请已接受 → 写入成员表   |

---

## 三、完整表结构（字段逐行对照DDL）

### 3.1 user（用户表）

| 字段名           | 类型         | 约束              | 默认值          | 说明             |
| ---------------- | ------------ | ----------------- | --------------- | ---------------- |
| `uid`          | INT          | PK AUTO_INCREMENT | —              | 用户编号         |
| `username`     | VARCHAR(20)  | NOT NULL, UNIQUE  | —              | 登录账号（学号） |
| `password`     | VARCHAR(255) | NOT NULL          | —              | MD5加盐密码      |
| `nickname`     | VARCHAR(50)  | NOT NULL          | —              | 用户昵称         |
| `email`        | VARCHAR(100) | —                | NULL            | 邮箱             |
| `phone`        | VARCHAR(20)  | —                | NULL            | 手机号           |
| `avatar`       | VARCHAR(255) | —                | NULL            | 头像路径         |
| `credit_score` | INT          | NOT NULL          | 100             | 信用分           |
| `created_at`   | DATETIME     | NOT NULL          | NOW()           | 注册时间         |
| `updated_at`   | DATETIME     | NOT NULL          | NOW() ON UPDATE | 更新时间         |
| `is_deleted`   | TINYINT(1)   | NOT NULL          | 0               | 软删除(0/1)      |

**索引**：PK=`uid`; UK `uk_username`=`username`

### 3.2 course（课程表）

| 字段名          | 类型         | 约束              | 默认值          | 说明                  |
| --------------- | ------------ | ----------------- | --------------- | --------------------- |
| `cid`         | INT          | PK AUTO_INCREMENT | —              | 课程编号              |
| `cname`       | VARCHAR(100) | NOT NULL          | —              | 课程名称              |
| `teacher`     | VARCHAR(50)  | —                | NULL            | 教师                  |
| `semester`    | VARCHAR(20)  | NOT NULL          | —              | 学期（如2025-2026-1） |
| `description` | TEXT         | —                | NULL            | 课程简介              |
| `created_at`  | DATETIME     | NOT NULL          | NOW()           | 创建时间              |
| `updated_at`  | DATETIME     | NOT NULL          | NOW() ON UPDATE | 更新时间              |
| `is_deleted`  | TINYINT(1)   | NOT NULL          | 0               | 软删除                |

**索引**：PK=`cid`

### 3.3 skill（技能标签表）

| 字段名         | 类型        | 约束              | 默认值 | 说明                      |
| -------------- | ----------- | ----------------- | ------ | ------------------------- |
| `sid`        | INT         | PK AUTO_INCREMENT | —     | 技能编号                  |
| `sname`      | VARCHAR(50) | NOT NULL, UNIQUE  | —     | 技能名称                  |
| `category`   | VARCHAR(20) | NOT NULL          | —     | 分类(技术/设计/管理/其他) |
| `created_at` | DATETIME    | NOT NULL          | NOW()  | 创建时间                  |

**索引**：PK=`sid`; UK `uk_sname`=`sname`

| 预置数据 | sid | sname      | category |
| -------- | --- | ---------- | -------- |
|          | 1   | 前端开发   | 技术     |
|          | 2   | 后端开发   | 技术     |
|          | 3   | 数据库设计 | 技术     |
|          | 4   | UI设计     | 设计     |
|          | 5   | 测试调试   | 技术     |
|          | 6   | 文档编写   | 管理     |
|          | 7   | 答辩演讲   | 管理     |
|          | 8   | 算法实现   | 技术     |

### 3.4 user_skill（用户技能关联表）★ 多对多

| 字段名          | 类型     | 约束                    | 默认值 | 说明      |
| --------------- | -------- | ----------------------- | ------ | --------- |
| `uid`         | INT      | **PK**, FK→user  | —     | 用户编号  |
| `sid`         | INT      | **PK**, FK→skill | —     | 技能编号  |
| `proficiency` | TINYINT  | NOT NULL                | 1      | 熟练度1-5 |
| `created_at`  | DATETIME | NOT NULL                | NOW()  | 关联时间  |

**PK**：`(uid, sid)` —— 联合主键天然防重

**FK**：`uid→user(uid) CASCADE`, `sid→skill(sid) CASCADE`

**索引**：`idx_uid`, `idx_sid`

### 3.5 project（项目表）

| 字段名          | 类型         | 约束                           | 默认值          | 说明             |
| --------------- | ------------ | ------------------------------ | --------------- | ---------------- |
| `pid`         | INT          | PK AUTO_INCREMENT              | —              | 项目编号         |
| `cid`         | INT          | **FK→course**, NOT NULL | —              | 所属课程         |
| `uid`         | INT          | **FK→user**, NOT NULL   | —              | 组长(创建者)     |
| `pname`       | VARCHAR(100) | NOT NULL                       | —              | 项目名称         |
| `description` | TEXT         | —                             | NULL            | 项目描述         |
| `max_members` | INT          | NOT NULL                       | 4               | 最大人数(含组长) |
| `status`      | TINYINT      | NOT NULL                       | 0               | 状态(见下方)     |
| `deadline`    | DATE         | —                             | NULL            | 招募截止日期     |
| `created_at`  | DATETIME     | NOT NULL                       | NOW()           | 创建时间         |
| `updated_at`  | DATETIME     | NOT NULL                       | NOW() ON UPDATE | 更新时间         |
| `is_deleted`  | TINYINT(1)   | NOT NULL                       | 0               | 软删除           |

**status 枚举**：

| 值 | 含义   | 触发条件                        |
| :-: | ------ | ------------------------------- |
| 0 | 招募中 | 项目创建默认                    |
| 1 | 已满   | 成员数= max_members（自动触发） |
| 2 | 进行中 | 组长手动启动                    |
| 3 | 已结束 | 项目完结（手动）                |

**FK**：`cid→course(cid) CASCADE`, `uid→user(uid) CASCADE`

**索引**：PK=`pid`; `idx_cid`, `idx_uid`, `idx_status`

### 3.6 project_skill（项目需求技能表）★ 多对多

| 字段名             | 类型     | 约束                      | 默认值 | 说明           |
| ------------------ | -------- | ------------------------- | ------ | -------------- |
| `pid`            | INT      | **PK**, FK→project | —     | 项目编号       |
| `sid`            | INT      | **PK**, FK→skill   | —     | 需求技能编号   |
| `required_count` | INT      | NOT NULL                  | 1      | 该技能需要人数 |
| `created_at`     | DATETIME | NOT NULL                  | NOW()  | 关联时间       |

**PK**：`(pid, sid)`

**FK**：`pid→project(pid) CASCADE`, `sid→skill(sid) CASCADE`

**索引**：`idx_pid`, `idx_sid`

### 3.7 application（组队申请表）

| 字段名          | 类型         | 约束                            | 默认值          | 说明         |
| --------------- | ------------ | ------------------------------- | --------------- | ------------ |
| `aid`         | INT          | PK AUTO_INCREMENT               | —              | 申请编号     |
| `pid`         | INT          | **FK→project**, NOT NULL | —              | 申请的项目   |
| `uid`         | INT          | **FK→user**, NOT NULL    | —              | 申请人       |
| `message`     | VARCHAR(255) | —                              | NULL            | 申请留言     |
| `status`      | TINYINT      | NOT NULL                        | 0               | 状态(见下方) |
| `apply_time`  | DATETIME     | NOT NULL                        | NOW()           | 提交时间     |
| `handle_time` | DATETIME     | —                              | NULL            | 处理时间     |
| `created_at`  | DATETIME     | NOT NULL                        | NOW()           | 创建时间     |
| `updated_at`  | DATETIME     | NOT NULL                        | NOW() ON UPDATE | 更新时间     |

**status 枚举**：

| 值 | 含义   | 后续动作              |
| :-: | ------ | --------------------- |
| 0 | 待处理 | 组长可审批            |
| 1 | 已接受 | → 自动写入 Member 表 |
| 2 | 已拒绝 | 结束                  |
| 3 | 已取消 | 学生撤回              |

**FK**：`pid→project(pid) CASCADE`, `uid→user(uid) CASCADE`

**索引**：PK=`aid`; `idx_pid`, `idx_uid`, `idx_status`

> **设计说明**：不设 `UNIQUE(pid, uid)` 约束。防重复申请逻辑放在代码层——查询是否存在 `status=0` 的同项目同用户记录。这样已拒绝/已取消的用户可以重新提交新申请。

### 3.8 member（项目成员表）

| 字段名         | 类型        | 约束                            | 默认值       | 说明                |
| -------------- | ----------- | ------------------------------- | ------------ | ------------------- |
| `mid`        | INT         | PK AUTO_INCREMENT               | —           | 记录编号            |
| `pid`        | INT         | **FK→project**, NOT NULL | —           | 所属项目            |
| `uid`        | INT         | **FK→user**, NOT NULL    | —           | 成员用户            |
| `role`       | VARCHAR(20) | NOT NULL                        | `'member'` | 角色(leader/member) |
| `join_time`  | DATETIME    | NOT NULL                        | NOW()        | 入组时间            |
| `created_at` | DATETIME    | NOT NULL                        | NOW()        | 创建时间            |

**UK**：`uk_pid_uid = (pid, uid)` —— 同一用户在一个项目仅一个角色

**FK**：`pid→project(pid) CASCADE`, `uid→user(uid) CASCADE`

**索引**：PK=`mid`; UK `(pid, uid)`; `idx_pid`, `idx_uid`

### 3.9 progress（进度节点表）

| 字段名          | 类型         | 约束                            | 默认值          | 说明              |
| --------------- | ------------ | ------------------------------- | --------------- | ----------------- |
| `prid`        | INT          | PK AUTO_INCREMENT               | —              | 节点编号          |
| `pid`         | INT          | **FK→project**, NOT NULL | —              | 所属项目          |
| `title`       | VARCHAR(100) | NOT NULL                        | —              | 节点标题          |
| `description` | TEXT         | —                              | NULL            | 节点描述          |
| `status`      | TINYINT      | NOT NULL                        | 0               | 0=待完成/1=已完成 |
| `deadline`    | DATE         | —                              | NULL            | 截止日期          |
| `created_at`  | DATETIME     | NOT NULL                        | NOW()           | 创建时间          |
| `updated_at`  | DATETIME     | NOT NULL                        | NOW() ON UPDATE | 更新时间          |

**FK**：`pid→project(pid) CASCADE`

**索引**：PK=`prid`; `idx_pid`

---

## 四、全局外键约束汇总（11个）

| 约束名          | 子表.字段         | → | 父表.字段   | 删除策略 |
| --------------- | ----------------- | -- | ----------- | -------- |
| `fk_us_uid`   | user_skill.uid    | → | user.uid    | CASCADE  |
| `fk_us_sid`   | user_skill.sid    | → | skill.sid   | CASCADE  |
| `fk_ps_pid`   | project_skill.pid | → | project.pid | CASCADE  |
| `fk_ps_sid`   | project_skill.sid | → | skill.sid   | CASCADE  |
| `fk_p_cid`    | project.cid       | → | course.cid  | CASCADE  |
| `fk_p_uid`    | project.uid       | → | user.uid    | CASCADE  |
| `fk_app_pid`  | application.pid   | → | project.pid | CASCADE  |
| `fk_app_uid`  | application.uid   | → | user.uid    | CASCADE  |
| `fk_m_pid`    | member.pid        | → | project.pid | CASCADE  |
| `fk_m_uid`    | member.uid        | → | user.uid    | CASCADE  |
| `fk_prog_pid` | progress.pid      | → | project.pid | CASCADE  |

---

## 五、索引设计理由

| 索引             | 所在表                                          | 理由                        |
| ---------------- | ----------------------------------------------- | --------------------------- |
| `uk_username`  | user                                            | 学号全局唯一，防止重复注册  |
| `uk_sname`     | skill                                           | 技能名称全局唯一            |
| `uk_pid_uid`   | member                                          | 同一用户同一项目仅一个角色  |
| `PK(uid, sid)` | user_skill                                      | 联合主键，天然防重          |
| `PK(pid, sid)` | project_skill                                   | 联合主键，天然防重          |
| `idx_status`   | project                                         | 「招募中」是最高频筛选条件  |
| `idx_status`   | application                                     | 「待处理」是审批页高频查询  |
| `idx_cid`      | project                                         | 按课程聚合项目时JOIN加速    |
| `idx_uid`      | project / member / application                  | 按用户查项目/成员/申请      |
| `idx_pid`      | member / application / progress / project_skill | 按项目查成员/申请/进度/技能 |

---

## 六、状态机流转图

### 6.1 项目状态（4态）

```
   ┌──────────┐   成员数 = max_members   ┌──────────┐
   │ 0:招募中  │ ──────────────────────► │ 1:已满   │
   └────┬─────┘    (自动触发，代码层)     └────┬─────┘
        │                                     │
        │                                     │ 组长手动启动
        │                                     ▼
        │                              ┌──────────┐
        │                              │ 2:进行中  │
        │                              └────┬─────┘
        │                                   │ 项目完结(手动)
        │                                   ▼
        │                              ┌──────────┐
        └──────────────────────────────│ 3:已结束  │
              减员后恢复（手动）         └──────────┘
```

### 6.2 申请状态（4态）

```
  学生提交
       │
       ▼
 ┌──────────┐     组长通过      ┌──────────┐
 │ 0:待处理  │ ────────────────► │ 1:已接受  │ ──► 写入 member 表
 └────┬─────┘                    └──────────┘
      │
      ├── 组长拒绝 ──────────► ┌──────────┐
      │                         │ 2:已拒绝  │ ──► 可重新申请
      │                         └──────────┘
      │
      └── 学生撤回 ──────────► ┌──────────┐
                                │ 3:已取消  │ ──► 可重新申请
                                └──────────┘
```

---

## 七、核心SQL查询

### 7.1 智能匹配推荐（★答辩核心）

```sql
-- 为指定学生推荐项目，按技能匹配度降序
SELECT
    p.pid, p.pname, p.description, p.max_members,
    (SELECT COUNT(*) FROM member WHERE pid = p.pid) AS current_members,
    COUNT(DISTINCT ps.sid) AS need_skills,
    COUNT(DISTINCT CASE WHEN us.uid = 1 THEN us.sid END) AS matched_skills,
    ROUND(
        COUNT(DISTINCT CASE WHEN us.uid = 1 THEN us.sid END) * 100.0
        / NULLIF(COUNT(DISTINCT ps.sid), 0), 2
    ) AS match_rate
FROM project p
JOIN project_skill ps ON p.pid = ps.pid
LEFT JOIN user_skill us ON ps.sid = us.sid AND us.uid = 1
WHERE p.status = 0 AND p.is_deleted = 0
  AND p.pid NOT IN (SELECT pid FROM member WHERE uid = 1)
  AND p.pid NOT IN (SELECT pid FROM application WHERE uid = 1 AND status = 0)
GROUP BY p.pid
HAVING matched_skills > 0
ORDER BY match_rate DESC;
```

### 7.2 审批通过（含事务+状态流转）

```sql
-- 伪代码示意（实际在ApplicationService.php中实现）
BEGIN;
  UPDATE application SET status = 1, handle_time = NOW() WHERE aid = ?;
  INSERT INTO member (pid, uid, role) VALUES (?, ?, 'member');
  SELECT COUNT(*) INTO @cnt FROM member WHERE pid = ?;
  IF @cnt >= (SELECT max_members FROM project WHERE pid = ?) THEN
    UPDATE project SET status = 1 WHERE pid = ?;  -- 满员自动切换
  END IF;
COMMIT;
```

---

## 八、测试数据实例（种子数据关系图）

```
seed data 执行后的实际关联：

  ┌──────────────────────────────────────────────────┐
  │  User                      Skill (8个)           │
  │  ────                      ────────              │
  │  uid=1 张三 ───────┐       1 前端开发            │
  │    技能:{1,2,3}    │       2 后端开发            │
  │  uid=2 李四       │       3 数据库设计          │
  │    技能:{4,1}      │       4 UI设计             │
  │  uid=3 王五 ───────┘       5 测试调试            │
  │    技能:{2,5,7}           6 文档编写            │
  └──────────────────        7 答辩演讲            │
          │                   8 算法实现            │
          │                   └──────────────────────┘
          │
          │  张三创建项目，自动成为组长
          ▼
  ┌──────────────────────────────────────────────────┐
  │  Project (pid=1)                                │
  │  pname: 智慧校园小程序                            │
  │  status: 0 (招募中)  max_members: 4              │
  │  required_skills: {1, 2, 4}                     │
  │                 前端开发、后端开发、UI设计          │
  │                                                  │
  │  Member: [{uid=1, role='leader'}]  ← 张三(组长)  │
  │  Application: [{aid=1, uid=2, 李四, status=0}]  │
  │               ← 李四申请中，等待张三审批           │
  └──────────────────────────────────────────────────┘
```

---

> **文档更新记录**
>
> - v1.2 (2025-06-02)：大幅修订——新增「关系模式」章节（答辩必备），ER图分块展示（图A核心+图B从属），修正关系总览表增加第⑩条，外键约束统一为11个列表，表结构逐字段与DDL二次核对
> - v1.1：初版
