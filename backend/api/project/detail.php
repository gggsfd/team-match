<?php
if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    Response::error(405, '请求方法不允许');
}

$pid = isset($_GET['pid']) ? (int)$_GET['pid'] : 0;
if ($pid <= 0) {
    Response::badRequest('项目ID无效');
}

$currentUid = Auth::getCurrentUid();
$projectService = new ProjectService();
$detail = $projectService->getDetail($pid, $currentUid);

if (!$detail) {
    Response::notFound('项目不存在');
}

Response::success($detail);
