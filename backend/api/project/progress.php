<?php
$user = Auth::requireLogin();
$pid = isset($_GET['pid']) ? (int)$_GET['pid'] : 0;
if ($pid <= 0) {
    Response::badRequest('项目ID无效');
}

$progressService = new ProgressService();

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $list = $progressService->getListByProject($pid);
    Response::success($list);
} elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!Auth::isProjectLeader($pid, $user['uid'])) {
        Response::forbidden('仅项目组长可操作进度节点');
    }

    $input = Validator::getJsonInput();
    $check = Validator::required($input, ['title']);
    if (!$check['valid']) {
        Response::badRequest($check['message']);
    }

    $data = [
        'pid'         => $pid,
        'title'       => $input['title'],
        'description' => $input['description'] ?? null,
        'deadline'    => $input['deadline'] ?? null,
    ];

    $result = $progressService->create($data);
    if ($result['success']) {
        Response::success(['prid' => $result['prid']], $result['message']);
    } else {
        Response::badRequest($result['message']);
    }
} elseif ($_SERVER['REQUEST_METHOD'] === 'PUT') {
    if (!Auth::isProjectLeader($pid, $user['uid'])) {
        Response::forbidden('仅项目组长可操作进度节点');
    }

    $input = Validator::getJsonInput();
    if (!isset($input['prid']) || !isset($input['status'])) {
        Response::badRequest('prid和status为必填字段');
    }

    $result = $progressService->updateStatus((int)$input['prid'], $pid, (int)$input['status']);
    if ($result['success']) {
        Response::success(null, $result['message']);
    } else {
        Response::badRequest($result['message']);
    }
} else {
    Response::error(405, '请求方法不允许');
}
