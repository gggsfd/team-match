<?php
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    Response::error(405, '请求方法不允许');
}

$user = Auth::requireLogin();
$pid = isset($_GET['pid']) ? (int)$_GET['pid'] : 0;
if ($pid <= 0) {
    Response::badRequest('项目ID无效');
}

$input = Validator::getJsonInput();
$message = $input['message'] ?? null;

$applicationService = new ApplicationService();
$result = $applicationService->apply($pid, $user['uid'], $message);

if ($result['success']) {
    Response::success(['aid' => $result['aid']], $result['message']);
} else {
    Response::badRequest($result['message']);
}
