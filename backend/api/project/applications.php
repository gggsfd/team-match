<?php
if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    Response::error(405, '请求方法不允许');
}

$pid = isset($_GET['pid']) ? (int)$_GET['pid'] : 0;
if ($pid <= 0) {
    Response::badRequest('项目ID无效');
}

$user = Auth::requireLogin();
if (!Auth::isProjectLeader($pid, $user['uid'])) {
    Response::forbidden('仅项目组长可查看申请列表');
}

$applicationService = new ApplicationService();
$applications = $applicationService->getApplicationsByProject($pid);
Response::success($applications);
