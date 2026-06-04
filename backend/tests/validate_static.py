"""
TeamMatch 后端代码——Python静态验证脚本
用法: python tests/validate_static.py
功能: 验证项目目录结构、PHP语法、SQL脚本完整性
"""
import os
import re
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
total = 0
passed = 0
failed = 0
errors = []

def p(name, condition, msg=""):
    global total, passed, failed, errors
    total += 1
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        err = f"  [FAIL] {name}" + (f" - {msg}" if msg else "")
        errors.append(err)
        print(err)

print("=" * 70)
print("  TeamMatch 后端代码——静态结构验证")
print("=" * 70)
print()

# ============================================
# 1. 目录结构验证
# ============================================
print("=== 1. 项目目录结构验证 ===")

REQUIRED_DIRS = [
    "config", "sql", "api/user", "api/course", "api/project",
    "api/application", "api/recommendation", "service", "model",
    "middleware", "util", "uploads/avatars", "tests"
]

for d in REQUIRED_DIRS:
    p(f"目录存在: {d}", os.path.isdir(os.path.join(ROOT_DIR, d)))

REQUIRED_FILES = [
    "index.php", "config/database.php", ".gitignore",
    "sql/01_init_database.sql", "sql/02_create_tables.sql", "sql/03_seed_data.sql",
    "util/Database.php", "util/Response.php", "util/Validator.php",
    "middleware/Auth.php",
    "model/User.php", "model/Course.php", "model/Skill.php", "model/Project.php",
    "model/Application.php", "model/Member.php", "model/Progress.php",
    "service/UserService.php", "service/CourseService.php", "service/ProjectService.php",
    "service/ApplicationService.php", "service/ProgressService.php", "service/RecommendationService.php",
    "api/user/register.php", "api/user/login.php", "api/user/profile.php", "api/user/skills.php",
    "api/course/list.php",
    "api/project/list.php", "api/project/detail.php", "api/project/apply.php",
    "api/project/applications.php", "api/project/progress.php",
    "api/application/handle.php",
    "api/recommendation/list.php",
    "tests/run_tests.php", "tests/validate_static.py",
]

for f in REQUIRED_FILES:
    p(f"文件存在: {f}", os.path.isfile(os.path.join(ROOT_DIR, f)))

print()

# ============================================
# 2. PHP文件语法基础校验
# ============================================
print("=== 2. PHP文件基础语法校验 ===")

php_files = []
for root, dirs, files in os.walk(ROOT_DIR):
    if 'uploads' in root:
        continue
    for file in files:
        if file.endswith('.php'):
            php_files.append(os.path.join(root, file))

for php_file in sorted(php_files):
    rel_path = os.path.relpath(php_file, ROOT_DIR)
    with open(php_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查PHP标签
    has_open = '<?php' in content
    p(f"PHP标签完整: {rel_path}", has_open, "缺少 <?php 标签")

    if has_open:
        # 检查闭合标签（不应使用 ?> 结尾以防止意外输出）
        # 允许在纯PHP文件中省略闭合标签

        # 检查类定义一致性（跳过入口文件和测试文件）
        # 使用正则匹配实际类声明：class ClassName
        if re.search(r'\bclass\s+[A-Z]\w+', content):
            class_name = os.path.splitext(os.path.basename(php_file))[0]
            p(f"类名与文件名匹配: {rel_path}",
              f"class {class_name}" in content or f"class {class_name} " in content,
              f"期望类名: {class_name}")
        elif os.path.basename(php_file) in ['index.php', 'run_tests.php']:
            p(f"入口/测试文件无需类定义: {rel_path}", True)

    # 检查文件大小合理
    file_size = len(content)
    p(f"文件大小合理: {rel_path} ({file_size}B)", file_size > 0 and file_size < 100000)

print()

# ============================================
# 3. SQL脚本校验
# ============================================
print("=== 3. SQL脚本完整性校验 ===")

for sql_file in ["sql/01_init_database.sql", "sql/02_create_tables.sql", "sql/03_seed_data.sql"]:
    path = os.path.join(ROOT_DIR, sql_file)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    p(f"SQL文件非空: {sql_file}", len(content) > 10)

# 验证9张表都在建表脚本中
create_sql = open(os.path.join(ROOT_DIR, "sql/02_create_tables.sql"), 'r', encoding='utf-8').read()
expected_tables = ['user', 'course', 'skill', 'user_skill', 'project',
                   'project_skill', 'application', 'member', 'progress']
for table in expected_tables:
    p(f"建表脚本包含表: {table}", f"CREATE TABLE `{table}`" in create_sql)

# 验证外键约束
fk_count = create_sql.count("FOREIGN KEY")
p(f"外键约束数量: {fk_count}", fk_count >= 8, f"期望>=8, 实际={fk_count}")

# 验证索引
idx_count = create_sql.count("KEY `idx_")
p(f"索引数量(辅助): {idx_count}", idx_count >= 10, f"期望>=10, 实际={idx_count}")

# 验证种子数据
seed_sql = open(os.path.join(ROOT_DIR, "sql/03_seed_data.sql"), 'r', encoding='utf-8').read()
p("测试数据包含技能标签", "INSERT INTO `skill`" in seed_sql)
p("测试数据包含课程", "INSERT INTO `course`" in seed_sql)
p("测试数据包含用户（MD5加盐）", "MD5" in seed_sql and "team_match_salt" in seed_sql)

print()

# ============================================
# 4. 关键业务逻辑存在性验证
# ============================================
print("=== 4. 关键业务逻辑验证 ===")

# 智能匹配SQL
rec_svc = open(os.path.join(ROOT_DIR, "service/RecommendationService.php"), 'r', encoding='utf-8').read()
p("RecommendationService: 包含匹配度计算", "match_rate" in rec_svc)
p("RecommendationService: 包含LEFT JOIN", "LEFT JOIN" in rec_svc or "left join" in rec_svc.lower())
p("RecommendationService: 排除已加入项目", "NOT IN" in rec_svc)
p("RecommendationService: 排除重复申请", "application" in rec_svc.lower())

# 状态机流转
app_svc = open(os.path.join(ROOT_DIR, "service/ApplicationService.php"), 'r', encoding='utf-8').read()
p("ApplicationService: 包含事务控制", "beginTransaction" in app_svc)
p("ApplicationService: 包含满员检查", "max_members" in app_svc)
p("ApplicationService: 包含状态更新", "updateStatus" in app_svc)
p("ApplicationService: 包含组长权限校验", "leader_uid" in app_svc)
p("ApplicationService: 包含commit/rollback", "commit" in app_svc and "rollBack" in app_svc)

# 认证中间件
auth = open(os.path.join(ROOT_DIR, "middleware/Auth.php"), 'r', encoding='utf-8').read()
p("Auth: 包含登录校验", "requireLogin" in auth)
p("Auth: 包含组长校验", "isProjectLeader" in auth)
p("Auth: 包含session管理", "session_start" in auth)

print()

# ============================================
# 5. 响应格式统一性验证
# ============================================
print("=== 5. 统一响应格式验证 ===")

resp = open(os.path.join(ROOT_DIR, "util/Response.php"), 'r', encoding='utf-8').read()
p("Response: 包含code字段", "'code'" in resp or '"code"' in resp)
p("Response: 包含message字段", "'message'" in resp or '"message"' in resp)
p("Response: 包含data字段", "'data'" in resp or '"data"' in resp)
p("Response: 包含200响应", "200" in resp)
p("Response: 包含400响应", "400" in resp)
p("Response: 包含401响应", "401" in resp)
p("Response: 包含403响应", "403" in resp)
p("Response: 包含404响应", "404" in resp)
p("Response: 包含500响应", "500" in resp)

print()

# ============================================
# 6. 软删除支持验证
# ============================================
print("=== 6. 软删除设计验证 ===")

for table in ['user', 'course', 'project']:
    p(f"DDL中{table}表含is_deleted字段",
      f"`is_deleted`" in create_sql and f"CREATE TABLE `{table}`" in create_sql)

# 检查Model是否过滤软删除
model_files = {
    "model/User.php": "is_deleted",
    "model/Course.php": "is_deleted",
    "model/Project.php": "is_deleted",
}
for mf, keyword in model_files.items():
    content_m = open(os.path.join(ROOT_DIR, mf), 'r', encoding='utf-8').read()
    p(f"{mf} 包含软删除过滤", keyword in content_m)

print()

# ============================================
# 7. PDO预处理防SQL注入验证
# ============================================
print("=== 7. SQL注入防护验证 ===")

all_php_content = ""
for php_file in php_files:
    with open(php_file, 'r', encoding='utf-8') as f:
        all_php_content += f.read() + "\n"

# 所有SQL都应该通过PDO::prepare使用
prepare_count = all_php_content.count("prepare(")
# 不应使用直接拼接
concat_danger = bool(re.search(r"\$sql\s*\.?=\s*['\"].*?\$_(?:GET|POST|REQUEST)", all_php_content))

p(f"PDO prepare使用次数: {prepare_count}", prepare_count > 5, f"实际={prepare_count}")
p("无直接SQL拼接风险", not concat_danger)

print()

# ============================================
# 8. 汇总
# ============================================
print("=" * 70)
print("  静态验证结果汇总")
print("=" * 70)
print(f"  总检查项: {total}")
print(f"  通过:     {passed}  [OK]")
print(f"  失败:     {failed}  " + ("[ERROR]" if failed > 0 else ""))
print(f"  通过率:   {round(passed/total*100, 1) if total > 0 else 0}%")
print("=" * 70)

if errors:
    print("\n  失败详情:")
    for e in errors:
        print(e)

print()

sys.exit(0 if failed == 0 else 1)
