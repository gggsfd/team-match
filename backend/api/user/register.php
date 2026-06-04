<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = Validator::getJsonInput();

    $check = Validator::required($input, ['username', 'password', 'nickname']);
    if (!$check['valid']) {
        Response::badRequest($check['message']);
    }

    $checkLen = Validator::length($input['password'], 6, 20, '密码');
    if (!$checkLen['valid']) {
        Response::badRequest($checkLen['message']);
    }

    $userService = new UserService();
    $result = $userService->register($input);

    if ($result['success']) {
        Response::success(['uid' => $result['uid'], 'username' => $input['username'], 'nickname' => $input['nickname']], '注册成功');
    } else {
        Response::badRequest($result['message']);
    }
} else {
    Response::error(405, '请求方法不允许');
}
