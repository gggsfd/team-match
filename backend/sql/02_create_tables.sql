-- ============================================
-- 02_create_tables.sql  建表脚本（9张表）
-- ============================================

USE team_match;

-- ----------------------------
-- 表1：用户表 (user)
-- ----------------------------
CREATE TABLE `user` (
    `uid`          INT           NOT NULL AUTO_INCREMENT COMMENT '用户唯一编号',
    `username`     VARCHAR(20)   NOT NULL COMMENT '登录账号（学号）',
    `password`     VARCHAR(255)  NOT NULL COMMENT '加密存储密码（MD5加盐）',
    `nickname`     VARCHAR(50)   NOT NULL COMMENT '用户昵称',
    `email`        VARCHAR(100)  DEFAULT NULL COMMENT '用户邮箱',
    `phone`        VARCHAR(20)   DEFAULT NULL COMMENT '联系电话',
    `avatar`       VARCHAR(255)  DEFAULT NULL COMMENT '头像存储地址',
    `credit_score` INT           NOT NULL DEFAULT 100 COMMENT '用户信用分，默认100',
    `role`        VARCHAR(20)   NOT NULL DEFAULT 'member' COMMENT '角色：admin管理员/leader组长/member普通用户',
    `is_active`   TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '账号状态：1启用/0禁用',
    `created_at`   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '账号注册时间',
    `updated_at`   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近更新时间',
    `is_deleted`   TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '软删除标识：0正常/1删除',
    PRIMARY KEY (`uid`),
    UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ----------------------------
-- 表2：课程表 (course)
-- ----------------------------
CREATE TABLE `course` (
    `cid`         INT           NOT NULL AUTO_INCREMENT COMMENT '课程唯一编号',
    `cname`       VARCHAR(100)  NOT NULL COMMENT '课程名称',
    `teacher`     VARCHAR(50)   DEFAULT NULL COMMENT '任课教师姓名',
    `semester`    VARCHAR(20)   NOT NULL COMMENT '所属学期（如：2025-2026-1）',
    `description` TEXT          DEFAULT NULL COMMENT '课程简介',
    `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近更新时间',
    `is_deleted`  TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '软删除标识',
    PRIMARY KEY (`cid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程表';

-- ----------------------------
-- 表3：技能标签表 (skill)
-- ----------------------------
CREATE TABLE `skill` (
    `sid`       INT          NOT NULL AUTO_INCREMENT COMMENT '技能唯一编号',
    `sname`     VARCHAR(50)  NOT NULL COMMENT '技能名称',
    `category`  VARCHAR(20)  NOT NULL COMMENT '技能分类：技术/设计/管理/其他',
    `created_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`sid`),
    UNIQUE KEY `uk_sname` (`sname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='技能标签表';

-- ----------------------------
-- 表4：用户技能关联表 (user_skill)
-- ----------------------------
CREATE TABLE `user_skill` (
    `uid`          INT        NOT NULL COMMENT '用户编号',
    `sid`          INT        NOT NULL COMMENT '技能编号',
    `proficiency`  TINYINT    NOT NULL DEFAULT 1 COMMENT '技能熟练度：1-5星',
    `created_at`   DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '关联时间',
    PRIMARY KEY (`uid`, `sid`),
    KEY `idx_uid` (`uid`),
    KEY `idx_sid` (`sid`),
    CONSTRAINT `fk_us_uid` FOREIGN KEY (`uid`) REFERENCES `user`(`uid`) ON DELETE CASCADE,
    CONSTRAINT `fk_us_sid` FOREIGN KEY (`sid`) REFERENCES `skill`(`sid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户技能关联表';

-- ----------------------------
-- 表5：项目表 (project)
-- ----------------------------
CREATE TABLE `project` (
    `pid`          INT           NOT NULL AUTO_INCREMENT COMMENT '项目唯一编号',
    `cid`          INT           NOT NULL COMMENT '所属课程编号',
    `uid`          INT           NOT NULL COMMENT '项目组长（创建者）编号',
    `pname`        VARCHAR(100)  NOT NULL COMMENT '项目名称',
    `description`  TEXT          DEFAULT NULL COMMENT '项目详细描述',
    `max_members`  INT           NOT NULL DEFAULT 4 COMMENT '项目最大人数（含组长）',
    `status`       TINYINT       NOT NULL DEFAULT 0 COMMENT '项目状态：0招募中/1已满/2进行中/3已结束',
    `deadline`     DATE          DEFAULT NULL COMMENT '组队招募截止时间',
    `created_at`   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '项目创建时间',
    `updated_at`   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近更新时间',
    `is_deleted`   TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '软删除标识',
    PRIMARY KEY (`pid`),
    KEY `idx_cid` (`cid`),
    KEY `idx_uid` (`uid`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_p_cid` FOREIGN KEY (`cid`) REFERENCES `course`(`cid`) ON DELETE CASCADE,
    CONSTRAINT `fk_p_uid` FOREIGN KEY (`uid`) REFERENCES `user`(`uid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目表';

-- ----------------------------
-- 表6：项目需求技能表 (project_skill)
-- ----------------------------
CREATE TABLE `project_skill` (
    `pid`            INT      NOT NULL COMMENT '项目编号',
    `sid`            INT      NOT NULL COMMENT '需求技能编号',
    `required_count` INT      NOT NULL DEFAULT 1 COMMENT '该技能所需人数',
    `created_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '关联时间',
    PRIMARY KEY (`pid`, `sid`),
    KEY `idx_pid` (`pid`),
    KEY `idx_sid` (`sid`),
    CONSTRAINT `fk_ps_pid` FOREIGN KEY (`pid`) REFERENCES `project`(`pid`) ON DELETE CASCADE,
    CONSTRAINT `fk_ps_sid` FOREIGN KEY (`sid`) REFERENCES `skill`(`sid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目需求技能表';

-- ----------------------------
-- 表7：组队申请表 (application)
-- ----------------------------
CREATE TABLE `application` (
    `aid`         INT           NOT NULL AUTO_INCREMENT COMMENT '申请唯一编号',
    `pid`         INT           NOT NULL COMMENT '申请的项目编号',
    `uid`         INT           NOT NULL COMMENT '申请人编号',
    `message`     VARCHAR(255)  DEFAULT NULL COMMENT '申请留言/自我介绍',
    `status`      TINYINT       NOT NULL DEFAULT 0 COMMENT '申请状态：0待处理/1已接受/2已拒绝/3已取消',
    `apply_time`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '申请提交时间',
    `handle_time` DATETIME      DEFAULT NULL COMMENT '申请处理时间',
    `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近更新时间',
    PRIMARY KEY (`aid`),
    KEY `idx_pid` (`pid`),
    KEY `idx_uid` (`uid`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_app_pid` FOREIGN KEY (`pid`) REFERENCES `project`(`pid`) ON DELETE CASCADE,
    CONSTRAINT `fk_app_uid` FOREIGN KEY (`uid`) REFERENCES `user`(`uid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='组队申请表';

-- ----------------------------
-- 表8：项目成员表 (member)
-- ----------------------------
CREATE TABLE `member` (
    `mid`       INT          NOT NULL AUTO_INCREMENT COMMENT '成员记录编号',
    `pid`       INT          NOT NULL COMMENT '所属项目编号',
    `uid`       INT          NOT NULL COMMENT '成员用户编号',
    `role`      VARCHAR(20)  NOT NULL DEFAULT 'member' COMMENT '角色：leader组长/member组员',
    `join_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入组时间',
    `created_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`mid`),
    UNIQUE KEY `uk_pid_uid` (`pid`, `uid`),
    KEY `idx_pid` (`pid`),
    KEY `idx_uid` (`uid`),
    CONSTRAINT `fk_m_pid` FOREIGN KEY (`pid`) REFERENCES `project`(`pid`) ON DELETE CASCADE,
    CONSTRAINT `fk_m_uid` FOREIGN KEY (`uid`) REFERENCES `user`(`uid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目成员表';

-- ----------------------------
-- 表9：进度节点表 (progress)
-- ----------------------------
CREATE TABLE `progress` (
    `prid`        INT           NOT NULL AUTO_INCREMENT COMMENT '进度节点编号',
    `pid`         INT           NOT NULL COMMENT '所属项目编号',
    `title`       VARCHAR(100)  NOT NULL COMMENT '进度节点标题',
    `description` TEXT          DEFAULT NULL COMMENT '节点详细描述',
    `status`      TINYINT       NOT NULL DEFAULT 0 COMMENT '节点状态：0待完成/1已完成',
    `deadline`    DATE          DEFAULT NULL COMMENT '节点完成截止时间',
    `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近更新时间',
    PRIMARY KEY (`prid`),
    KEY `idx_pid` (`pid`),
    CONSTRAINT `fk_prog_pid` FOREIGN KEY (`pid`) REFERENCES `project`(`pid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='进度节点表';
