<?php
/**
 * 管理员统计API
 * 仅 admin 角色可访问
 */
$user = Auth::requireLogin();
if ($user['role'] !== 'admin') {
    Response::forbidden('仅系统管理员可访问');
}

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    Response::error(405, '请求方法不允许');
}

$db = Database::getInstance();

$totalUsers = (int)$db->query("SELECT COUNT(*) AS c FROM user WHERE is_deleted = 0")->fetch()['c'];
$activeUsers = (int)$db->query("SELECT COUNT(*) AS c FROM user WHERE is_deleted = 0 AND is_active = 1")->fetch()['c'];
$adminCount = (int)$db->query("SELECT COUNT(*) AS c FROM user WHERE is_deleted = 0 AND role = 'admin'")->fetch()['c'];
$totalProjects = (int)$db->query("SELECT COUNT(*) AS c FROM project WHERE is_deleted = 0")->fetch()['c'];
$recruiting = (int)$db->query("SELECT COUNT(*) AS c FROM project WHERE is_deleted = 0 AND status = 0")->fetch()['c'];
$inProgress = (int)$db->query("SELECT COUNT(*) AS c FROM project WHERE is_deleted = 0 AND status = 2")->fetch()['c'];
$pendingApps = (int)$db->query("SELECT COUNT(*) AS c FROM application WHERE status = 0")->fetch()['c'];

Response::success([
    'total_users'         => $totalUsers,
    'active_users'        => $activeUsers,
    'admin_count'         => $adminCount,
    'total_projects'      => $totalProjects,
    'recruiting'          => $recruiting,
    'in_progress'         => $inProgress,
    'pending_applications' => $pendingApps,
]);
