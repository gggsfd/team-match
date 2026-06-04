-- ============================================
-- 03_seed_data.sql  测试数据填充
-- ============================================

USE team_match;

-- 1. 预置技能标签（8个校园项目常用技能）
INSERT INTO `skill` (`sname`, `category`) VALUES
('前端开发', '技术'),
('后端开发', '技术'),
('数据库设计', '技术'),
('UI设计', '设计'),
('测试调试', '技术'),
('文档编写', '管理'),
('答辩演讲', '管理'),
('算法实现', '技术');

-- 2. 测试课程（2门）
INSERT INTO `course` (`cname`, `teacher`, `semester`, `description`) VALUES
('软件工程课程设计', '张教授', '2025-2026-2', '软件工程实践课程，要求学生组队完成一个完整的软件项目'),
('数据库系统原理', '李教授', '2025-2026-2', '数据库理论课程，配套课程设计需完成一个数据库应用系统');

-- 3. 测试用户（3个，密码统一为 123456 的MD5加盐加密）
INSERT INTO `user` (`username`, `password`, `nickname`, `email`, `phone`) VALUES
('2024001', MD5(CONCAT('2024001', 'team_match_salt')), '张三', 'zhangsan@qq.com', '13800001111'),
('2024002', MD5(CONCAT('2024002', 'team_match_salt')), '李四', 'lisi@qq.com', '13800002222'),
('2024003', MD5(CONCAT('2024003', 'team_match_salt')), '王五', 'wangwu@qq.com', '13800003333');

-- 4. 用户技能
INSERT INTO `user_skill` (`uid`, `sid`, `proficiency`) VALUES
(1, 1, 5), (1, 2, 4), (1, 3, 3),
(2, 4, 5), (2, 1, 3),
(3, 2, 4), (3, 5, 4), (3, 7, 5);

-- 5. 测试项目（张三发布招募中项目）
INSERT INTO `project` (`cid`, `uid`, `pname`, `description`, `max_members`, `status`, `deadline`) VALUES
(1, 1, '智慧校园小程序', '开发一款面向全校师生的智慧校园服务小程序，包含课表查询、成绩管理、校园导航等功能', 4, 0, '2025-07-01');

-- 6. 项目需求技能
INSERT INTO `project_skill` (`pid`, `sid`, `required_count`) VALUES
(1, 1, 1), (1, 2, 1), (1, 4, 1);

-- 7. 张三自动成为项目组长
INSERT INTO `member` (`pid`, `uid`, `role`) VALUES
(1, 1, 'leader');

-- 8. 测试申请（李四申请加入张三的项目）
INSERT INTO `application` (`pid`, `uid`, `message`, `status`) VALUES
(1, 2, '我擅长UI设计和前端开发，希望能加入你们的项目！', 0);
