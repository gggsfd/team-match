<?php
if ($_SERVER['REQUEST_METHOD'] !== 'PUT') {
    Response::error(405, '请求方法不允许');
}

$aid = isset($_GET['aid']) ? (int)$_GET['aid'] : 0;
if ($aid <= 0) {
    Response::badRequest('申请ID无效');
}

$user = Auth::requireLogin();
$input = Validator::getJsonInput();

$check = Validator::required($input, ['action']);
if (!$check['valid']) {
    Response::badRequest($check['message']);
}

$action = $input['action'];
if (!in_array($action, ['accept', 'reject'], true)) {
    Response::badRequest('action必须为accept或reject');
}

$applicationService = new ApplicationService();
$result = $applicationService->handleApplication($aid, $user['uid'], $action);

if ($result['success']) {
    Response::success([
        'project_status_changed' => $result['project_status_changed'] ?? false,
    ], $result['message']);
} else {
    if ($result['message'] === '仅项目组长可审批申请') {
        Response::forbidden($result['message']);
    } else {
        Response::badRequest($result['message']);
    }
}
