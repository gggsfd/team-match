<?php
header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    header('Access-Control-Allow-Credentials: true');
    http_response_code(204);
    exit;
}

spl_autoload_register(function ($class) {
    $paths = ['util/', 'middleware/', 'service/', 'model/'];
    foreach ($paths as $path) {
        $file = __DIR__ . '/' . $path . $class . '.php';
        if (file_exists($file)) {
            require_once $file;
            return;
        }
    }
});

$requestUri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$method = $_SERVER['REQUEST_METHOD'];

$scriptName = dirname($_SERVER['SCRIPT_NAME']);
$basePath = rtrim($scriptName, '/');
$route = substr($requestUri, strlen($basePath));
$route = '/' . ltrim($route, '/');

$routes = [
    // 用户模块
    '/api/user/register' => 'api/user/register.php',
    '/api/user/login'    => 'api/user/login.php',
    '/api/user/profile'  => 'api/user/profile.php',
    '/api/user/skills'   => 'api/user/skills.php',
    // 课程模块
    '/api/courses'       => 'api/course/list.php',
    // 项目列表/发布
    '/api/projects'      => 'api/project/list.php',
    // 推荐
    '/api/recommendations' => 'api/recommendation/list.php',
    // 管理员
    '/api/admin/users'     => 'api/admin/users.php',
];

if (isset($routes[$route])) {
    require __DIR__ . '/' . $routes[$route];
    exit;
}

// 动态路由：/api/projects/{id}
if (preg_match('#^/api/projects/(\d+)$#', $route, $matches)) {
    $_GET['pid'] = $matches[1];
    require __DIR__ . '/api/project/detail.php';
    exit;
}

// 动态路由：/api/projects/{id}/apply
if (preg_match('#^/api/projects/(\d+)/apply$#', $route, $matches)) {
    $_GET['pid'] = $matches[1];
    require __DIR__ . '/api/project/apply.php';
    exit;
}

// 动态路由：/api/projects/{id}/applications
if (preg_match('#^/api/projects/(\d+)/applications$#', $route, $matches)) {
    $_GET['pid'] = $matches[1];
    require __DIR__ . '/api/project/applications.php';
    exit;
}

// 动态路由：/api/projects/{id}/progress
if (preg_match('#^/api/projects/(\d+)/progress$#', $route, $matches)) {
    $_GET['pid'] = $matches[1];
    require __DIR__ . '/api/project/progress.php';
    exit;
}

// 动态路由：/api/applications/{id}/handle
if (preg_match('#^/api/applications/(\d+)/handle$#', $route, $matches)) {
    $_GET['aid'] = $matches[1];
    require __DIR__ . '/api/application/handle.php';
    exit;
}

Response::notFound('接口不存在');
