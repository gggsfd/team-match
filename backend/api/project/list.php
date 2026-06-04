<?php
$projectService = new ProjectService();

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $filters = [];
    if (!empty($_GET['cid'])) {
        $filters['cid'] = (int)$_GET['cid'];
    }
    if (isset($_GET['status']) && $_GET['status'] !== '') {
        $filters['status'] = (int)$_GET['status'];
    }
    if (!empty($_GET['keyword'])) {
        $filters['keyword'] = trim($_GET['keyword']);
    }

    $page = max(1, isset($_GET['page']) ? (int)$_GET['page'] : 1);
    $pageSize = max(1, min(50, isset($_GET['page_size']) ? (int)$_GET['page_size'] : 10));

    $result = $projectService->getList($filters, $page, $pageSize);
    Response::success($result);
} elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $user = Auth::requireLogin();
    $input = Validator::getJsonInput();

    $check = Validator::required($input, ['cid', 'pname', 'skill_ids']);
    if (!$check['valid']) {
        Response::badRequest($check['message']);
    }

    $courseModel = new Course();
    if (!$courseModel->findById($input['cid'])) {
        Response::badRequest('所选课程不存在');
    }

    $arrCheck = Validator::isNonEmptyArray($input['skill_ids'], 'skill_ids');
    if (!$arrCheck['valid']) {
        Response::badRequest($arrCheck['message']);
    }

    $input['uid'] = $user['uid'];
    $result = $projectService->create($input);

    if ($result['success']) {
        Response::success(['pid' => $result['pid']], $result['message']);
    } else {
        Response::badRequest($result['message']);
    }
} else {
    Response::error(405, '请求方法不允许');
}
