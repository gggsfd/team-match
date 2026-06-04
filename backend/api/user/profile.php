<?php
$user = Auth::requireLogin();
$userService = new UserService();

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $profile = $userService->getProfile($user['uid']);
    if ($profile) {
        Response::success($profile);
    } else {
        Response::notFound('用户不存在');
    }
} elseif ($_SERVER['REQUEST_METHOD'] === 'PUT') {
    $input = Validator::getJsonInput();
    $allowedFields = ['nickname', 'email', 'phone'];
    $updateData = [];
    foreach ($allowedFields as $field) {
        if (array_key_exists($field, $input)) {
            $updateData[$field] = $input[$field];
        }
    }

    if (empty($updateData)) {
        Response::badRequest('无可更新的字段');
    }

    $result = $userService->updateProfile($user['uid'], $updateData);
    if ($result['success']) {
        Response::success(null, '资料更新成功');
    } else {
        Response::badRequest($result['message']);
    }
} else {
    Response::error(405, '请求方法不允许');
}
