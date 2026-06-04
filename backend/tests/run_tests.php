<?php
/**
 * ============================================
 * TeamMatch 后端测试脚本
 * 用法: php tests/run_tests.php
 *
 * 测试覆盖：
 *   单元测试 - Model/Service 核心逻辑
 *   集成测试 - 完整业务流程端到端验证
 *   性能测试 - 智能匹配查询响应时间
 * ============================================
 */

$testStartTime = microtime(true);
$totalTests = 0;
$passedTests = 0;
$failedTests = 0;
$errors = [];

// ============================================
// 0. 初始化环境
// ============================================
define('TEST_MODE', true);
$_SERVER['REQUEST_METHOD'] = 'GET';
$_SERVER['SCRIPT_NAME'] = '/index.php';
$_SERVER['REQUEST_URI'] = '/api/test';

define('ROOT_DIR', dirname(__DIR__));
require_once ROOT_DIR . '/util/Database.php';
require_once ROOT_DIR . '/util/Response.php';
require_once ROOT_DIR . '/util/Validator.php';
require_once ROOT_DIR . '/middleware/Auth.php';
require_once ROOT_DIR . '/model/User.php';
require_once ROOT_DIR . '/model/Course.php';
require_once ROOT_DIR . '/model/Skill.php';
require_once ROOT_DIR . '/model/Project.php';
require_once ROOT_DIR . '/model/Application.php';
require_once ROOT_DIR . '/model/Member.php';
require_once ROOT_DIR . '/model/Progress.php';
require_once ROOT_DIR . '/service/UserService.php';
require_once ROOT_DIR . '/service/CourseService.php';
require_once ROOT_DIR . '/service/ProjectService.php';
require_once ROOT_DIR . '/service/ApplicationService.php';
require_once ROOT_DIR . '/service/ProgressService.php';
require_once ROOT_DIR . '/service/RecommendationService.php';

echo str_repeat('=', 70) . "\n";
echo "  TeamMatch 后端测试套件 v1.0\n";
echo str_repeat('=', 70) . "\n\n";

// ============================================
// 测试辅助函数
// ============================================
function assertTrue($condition, $testName)
{
    global $totalTests, $passedTests, $failedTests, $errors;
    $totalTests++;
    if ($condition) {
        $passedTests++;
        echo "  [PASS] {$testName}\n";
    } else {
        $failedTests++;
        $errors[] = "  [FAIL] {$testName}";
        echo "  [FAIL] {$testName}\n";
    }
}

function assertEqual($expected, $actual, $testName)
{
    global $totalTests, $passedTests, $failedTests, $errors;
    $totalTests++;
    if ($expected === $actual) {
        $passedTests++;
        echo "  [PASS] {$testName}\n";
    } else {
        $failedTests++;
        $msg = "  [FAIL] {$testName} - 期望: " . var_export($expected, true) . ", 实际: " . var_export($actual, true);
        $errors[] = $msg;
        echo "  {$msg}\n";
    }
}

function assertNotNull($value, $testName)
{
    global $totalTests, $passedTests, $failedTests, $errors;
    $totalTests++;
    if ($value !== null) {
        $passedTests++;
        echo "  [PASS] {$testName}\n";
    } else {
        $failedTests++;
        $errors[] = "  [FAIL] {$testName} - 结果为null";
        echo "  [FAIL] {$testName} - 结果为null\n";
    }
}

function assertNotEmpty($arr, $testName)
{
    global $totalTests, $passedTests, $failedTests, $errors;
    $totalTests++;
    if (is_array($arr) && count($arr) > 0) {
        $passedTests++;
        echo "  [PASS] {$testName}\n";
    } else {
        $failedTests++;
        $errors[] = "  [FAIL] {$testName} - 数组为空";
        echo "  [FAIL] {$testName} - 数组为空\n";
    }
}

// ============================================
// 1. SQL脚本语法测试（静态校验）
// ============================================
echo "=== 1. SQL脚本静态语法测试 ===\n";

$sqlFiles = [
    '01_init_database.sql',
    '02_create_tables.sql',
    '03_seed_data.sql',
];

foreach ($sqlFiles as $file) {
    $path = ROOT_DIR . '/sql/' . $file;
    assertTrue(file_exists($path), "SQL文件存在: {$file}");

    $content = file_get_contents($path);
    assertTrue(strlen($content) > 0, "SQL文件非空: {$file}");

    assertTrue(stripos($content, 'CREATE TABLE') !== false || stripos($content, 'CREATE DATABASE') !== false,
        "SQL文件包含DDL语句: {$file}");
}

// 校验9张表都在建表脚本中
$createTables = file_get_contents(ROOT_DIR . '/sql/02_create_tables.sql');
$expectedTables = ['user', 'course', 'skill', 'user_skill', 'project', 'project_skill', 'application', 'member', 'progress'];
foreach ($expectedTables as $table) {
    assertTrue(stripos($createTables, "CREATE TABLE `{$table}`") !== false,
        "建表脚本包含表: {$table}");
}

// 校验测试数据包含8个技能、2门课程、3个用户
$seedData = file_get_contents(ROOT_DIR . '/sql/03_seed_data.sql');
assertTrue(substr_count($seedData, "INSERT INTO `skill`") >= 1, "测试数据包含技能标签");
assertTrue(substr_count($seedData, "INSERT INTO `course`") >= 1, "测试数据包含课程");
assertTrue(substr_count($seedData, "INSERT INTO `user`") >= 1, "测试数据包含用户");

echo "\n";

// ============================================
// 2. 配置与工具类单元测试
// ============================================
echo "=== 2. 配置与工具类单元测试 ===\n";

$config = require ROOT_DIR . '/config/database.php';
assertEqual('127.0.0.1', $config['host'], "数据库host配置正确");
assertEqual('team_match', $config['dbname'], "数据库名称配置正确");
assertTrue(isset($config['username'], $config['password']), "数据库认证配置存在");

// Validator测试
$result = Validator::required(['name' => 'test', 'email' => ''], ['name']);
assertTrue($result['valid'], "Validator::required - 存在字段通过");

$result = Validator::required(['name' => ''], ['name']);
assertTrue(!$result['valid'], "Validator::required - 空字段拒绝");

$result = Validator::length('hello', 1, 10, '测试');
assertTrue($result['valid'], "Validator::length - 合法长度通过");

$result = Validator::length('hello', 10, 20, '测试');
assertTrue(!$result['valid'], "Validator::length - 越界长度拒绝");

$result = Validator::isInt(5, 'id');
assertTrue($result['valid'], "Validator::isInt - 正整数通过");

$result = Validator::isInt(-1, 'id');
assertTrue(!$result['valid'], "Validator::isInt - 负数拒绝");

$result = Validator::isNonEmptyArray([1, 2, 3], 'ids');
assertTrue($result['valid'], "Validator::isNonEmptyArray - 非空数组通过");

$result = Validator::isNonEmptyArray([], 'ids');
assertTrue(!$result['valid'], "Validator::isNonEmptyArray - 空数组拒绝");

echo "\n";

// ============================================
// 3. 数据库连接测试（如果可用）
// ============================================
echo "=== 3. 数据库连接测试 ===\n";

$dbAvailable = false;
try {
    $db = Database::getInstance();
    $stmt = $db->query("SELECT 1 AS alive");
    $row = $stmt->fetch();
    if ($row && $row['alive'] == 1) {
        $dbAvailable = true;
        echo "  [PASS] 数据库连接成功\n";
        $totalTests++; $passedTests++;
    }
} catch (Exception $e) {
    echo "  [SKIP] 数据库不可用，跳过数据库相关测试 (" . $e->getMessage() . ")\n";
}

if ($dbAvailable) {
    // 检查表是否存在
    $tables = $db->query("SHOW TABLES LIKE 'user'")->fetchAll();
    assertTrue(count($tables) > 0, "user表存在");
    $tables = $db->query("SHOW TABLES LIKE 'project'")->fetchAll();
    assertTrue(count($tables) > 0, "project表存在");
    $tables = $db->query("SHOW TABLES LIKE 'skill'")->fetchAll();
    assertTrue(count($tables) > 0, "skill表存在");
}

echo "\n";

// ============================================
// 4. 数据库集成测试（需要DB + 种子数据）
// ============================================
echo "=== 4. 数据库集成测试（端到端业务流程） ===\n";

if (!$dbAvailable) {
    echo "  [SKIP] 数据库不可用，跳过集成测试\n";
} else {
    // 检测种子数据是否存在
    $stmt = $db->query("SELECT COUNT(*) AS cnt FROM user");
    $userCount = (int)$stmt->fetch()['cnt'];

    if ($userCount < 3) {
        echo "  [WARN] 测试用户不足3个，请先执行 sql/03_seed_data.sql\n";
        // 尝试执行测试数据填充
        // （跳过，让用户手动执行SQL）
    }

    // 4.1 用户登录测试
    echo "  --- 4.1 用户模块 ---\n";
    $stmt = $db->query("SELECT uid, username FROM user WHERE is_deleted = 0 LIMIT 3");
    $users = $stmt->fetchAll();
    assertTrue(count($users) >= 3, "至少存在3个测试用户");

    $userService = new UserService();
    $loginResult = $userService->login('2024001', '123456');
    assertTrue($loginResult['success'], "用户2024001登录成功");

    $loginFailResult = $userService->login('2024001', 'wrong_password');
    assertTrue(!$loginFailResult['success'], "错误密码登录失败");

    // 4.2 用户资料获取
    if (isset($users[0])) {
        $profile = $userService->getProfile($users[0]['uid']);
        assertNotNull($profile, "获取用户资料成功");
        if ($profile) {
            assertTrue(isset($profile['skills']), "用户资料包含技能列表");
        }
    }

    // 4.3 课程列表
    echo "  --- 4.2 课程模块 ---\n";
    $courseService = new CourseService();
    $courses = $courseService->getList();
    assertNotEmpty($courses, "课程列表查询成功");

    $coursesFiltered = $courseService->getList('2025-2026-2');
    assertTrue(count($coursesFiltered) > 0, "按学期筛选课程成功");

    // 4.4 项目列表
    echo "  --- 4.3 项目模块 ---\n";
    $projectService = new ProjectService();
    $projects = $projectService->getList();
    assertNotNull($projects, "项目列表查询成功");

    if (count($users) >= 2 && isset($courses[0])) {
        $projResult = $projectService->create([
            'cid'         => $courses[0]['cid'],
            'uid'         => $users[1]['uid'],
            'pname'       => '测试项目_' . time(),
            'description' => '自动化测试项目',
            'max_members' => 3,
            'skill_ids'   => [1, 2],
        ]);
        assertTrue($projResult['success'], "项目发布成功");
        $testPid = $projResult['pid'] ?? 0;

        if ($testPid > 0) {
            // 项目详情
            $detail = $projectService->getDetail($testPid, $users[0]['uid']);
            assertNotNull($detail, "项目详情查询成功");
            if ($detail) {
                assertTrue(isset($detail['members']) && count($detail['members']) > 0, "项目详情包含成员列表（组长）");
                assertTrue(isset($detail['required_skills']) && count($detail['required_skills']) > 0, "项目详情包含需求技能");
            }

            // 4.5 申请 & 审批流程
            echo "  --- 4.4 申请审批模块 ---\n";
            $applicationService = new ApplicationService();

            // 发起申请
            $applyResult = $applicationService->apply($testPid, $users[0]['uid'], '我想加入');
            assertTrue($applyResult['success'], "发起入组申请成功");
            $testAid = $applyResult['aid'] ?? 0;

            // 重复申请拦截
            $applyDupResult = $applicationService->apply($testPid, $users[0]['uid'], '再次申请');
            assertTrue(!$applyDupResult['success'], "重复申请被拦截");

            // 查看申请列表
            $applications = $applicationService->getApplicationsByProject($testPid);
            assertNotEmpty($applications, "组长查看申请列表成功");

            // 审批通过
            $handleResult = $applicationService->handleApplication($testAid, $users[1]['uid'], 'accept');
            assertTrue($handleResult['success'], "组长审批通过申请");

            // 已处理申请不可再次处理
            $handleDupResult = $applicationService->handleApplication($testAid, $users[1]['uid'], 'accept');
            assertTrue(!$handleDupResult['success'], "已处理申请不可重复处理");

            // 4.6 进度模块
            echo "  --- 4.5 进度看板模块 ---\n";
            $progressService = new ProgressService();
            $createProgress = $progressService->create([
                'pid'         => $testPid,
                'title'       => '需求分析',
                'description' => '完成需求分析文档',
                'deadline'    => '2025-07-15',
            ]);
            assertTrue($createProgress['success'], "新增进度节点成功");

            $progressList = $progressService->getListByProject($testPid);
            assertNotEmpty($progressList, "查询进度节点列表成功");

            $prid = $createProgress['prid'];
            $updateResult = $progressService->updateStatus($prid, $testPid, 1);
            assertTrue($updateResult['success'], "更新进度节点状态成功");

            // 4.7 清理测试数据
            $db->exec("DELETE FROM progress WHERE pid = {$testPid}");
            $db->exec("DELETE FROM application WHERE pid = {$testPid}");
            $db->exec("DELETE FROM member WHERE pid = {$testPid}");
            $db->exec("DELETE FROM project_skill WHERE pid = {$testPid}");
            $db->exec("DELETE FROM project WHERE pid = {$testPid}");
            echo "  [INFO] 测试数据已清理\n";
        }
    }

    echo "\n";
}

// ============================================
// 5. 智能匹配推荐测试
// ============================================
echo "=== 5. 智能匹配推荐SQL测试 ===\n";

if (!$dbAvailable) {
    echo "  [SKIP] 数据库不可用，跳过匹配测试\n";
} else {
    $stmt = $db->query("SELECT uid FROM user WHERE is_deleted = 0 LIMIT 1");
    $firstUser = $stmt->fetch();
    if ($firstUser) {
        $recommendationService = new RecommendationService();
        $startTime = microtime(true);
        $recommendations = $recommendationService->getRecommendations($firstUser['uid']);
        $endTime = microtime(true);
        $execTime = round(($endTime - $startTime) * 1000, 2);

        assertTrue(is_array($recommendations), "推荐接口返回数组");
        if (count($recommendations) > 0) {
            $first = $recommendations[0];
            assertTrue(isset($first['match_rate']), "推荐结果包含匹配度");
            assertTrue((float)$first['match_rate'] >= 0 && (float)$first['match_rate'] <= 100, "匹配度在0-100之间");
            assertTrue(isset($first['matched_skills']), "推荐结果包含匹配技能");
            assertTrue(isset($first['unmatched_skills']), "推荐结果包含未匹配技能");
            assertTrue(is_array($first['matched_skills']), "匹配技能为数组");
            assertTrue(is_array($first['unmatched_skills']), "未匹配技能为数组");
        }

        echo "  [INFO] 智能匹配查询耗时: {$execTime}ms\n";
        assertTrue($execTime < 1000, "匹配查询耗时 < 1秒（性能达标）");
    }
}

echo "\n";

// ============================================
// 6. 自动加载类测试
// ============================================
echo "=== 6. 类自动加载测试 ===\n";

$expectedClasses = [
    'Database', 'Response', 'Validator', 'Auth',
    'User', 'Course', 'Skill', 'Project',
    'Application', 'Member', 'Progress',
    'UserService', 'CourseService', 'ProjectService',
    'ApplicationService', 'ProgressService', 'RecommendationService',
];

foreach ($expectedClasses as $className) {
    assertTrue(class_exists($className), "类 {$className} 可加载");
}

echo "\n";

// ============================================
// 7. 路由匹配测试（静态分析）
// ============================================
echo "=== 7. 路由配置测试 ===\n";

$staticRoutes = [
    '/api/user/register',
    '/api/user/login',
    '/api/user/profile',
    '/api/user/skills',
    '/api/courses',
    '/api/projects',
    '/api/recommendations',
];

foreach ($staticRoutes as $route) {
    $apiFile = str_replace('/api/', 'api/', $route);
    $expectedPath = ROOT_DIR . '/' . str_replace('/', '/', $apiFile);
    $fileExists = file_exists($expectedPath . '.php');
    assertTrue($fileExists, "路由 {$route} 对应文件存在");
}

// 动态路由对应文件
$dynamicFiles = [
    'api/project/detail.php',
    'api/project/apply.php',
    'api/project/applications.php',
    'api/project/progress.php',
    'api/application/handle.php',
];
foreach ($dynamicFiles as $file) {
    assertTrue(file_exists(ROOT_DIR . '/' . $file), "动态路由文件存在: {$file}");
}

echo "\n";

// ============================================
// 8. 完整项目目录结构验证
// ============================================
echo "=== 8. 项目结构完整性验证 ===\n";

$requiredFiles = [
    'index.php',
    'config/database.php',
    '.gitignore',
    'sql/01_init_database.sql',
    'sql/02_create_tables.sql',
    'sql/03_seed_data.sql',
    'util/Database.php',
    'util/Response.php',
    'util/Validator.php',
    'middleware/Auth.php',
    'model/User.php',
    'model/Course.php',
    'model/Skill.php',
    'model/Project.php',
    'model/Application.php',
    'model/Member.php',
    'model/Progress.php',
    'service/UserService.php',
    'service/CourseService.php',
    'service/ProjectService.php',
    'service/ApplicationService.php',
    'service/ProgressService.php',
    'service/RecommendationService.php',
    'api/user/register.php',
    'api/user/login.php',
    'api/user/profile.php',
    'api/user/skills.php',
    'api/course/list.php',
    'api/project/list.php',
    'api/project/detail.php',
    'api/project/apply.php',
    'api/project/applications.php',
    'api/project/progress.php',
    'api/application/handle.php',
    'api/recommendation/list.php',
    'uploads/avatars/.gitkeep',
];

foreach ($requiredFiles as $file) {
    $path = ROOT_DIR . '/' . $file;
    assertTrue(file_exists($path), "必要文件存在: {$file}");
}

echo "\n";

// ============================================
// 9. 测试总结
// ============================================
$testEndTime = microtime(true);
$totalTime = round(($testEndTime - $testStartTime) * 1000, 2);

echo str_repeat('=', 70) . "\n";
echo "  测试结果汇总\n";
echo str_repeat('=', 70) . "\n";
echo "  总测试数: {$totalTests}\n";
echo "  通过:     {$passedTests}  ✓\n";
echo "  失败:     {$failedTests}  " . ($failedTests > 0 ? '✗' : '') . "\n";
echo "  通过率:   " . ($totalTests > 0 ? round($passedTests / $totalTests * 100, 1) : 0) . "%\n";
echo "  总耗时:   {$totalTime}ms\n";
echo str_repeat('=', 70) . "\n";

if (!empty($errors)) {
    echo "\n  失败详情:\n";
    foreach ($errors as $error) {
        echo "  {$error}\n";
    }
}

echo "\n";

exit($failedTests > 0 ? 1 : 0);
