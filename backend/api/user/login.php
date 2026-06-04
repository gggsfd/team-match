<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = Validator::getJsonInput();

    $check = Validator::required($input, ['username', 'password']);
    if (!$check['valid']) {
        Response::badRequest($check['message']);
    }

    $userService = new UserService();
    $result = $userService->login($input['username'], $input['password']);

    if ($result['success']) {
        Response::success($result['user'], '登录成功');
    } else {
        Response::badRequest($result['message']);
    }
} else {
    Response::error(405, '请求方法不允许');
}
