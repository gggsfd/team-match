<?php
$user = Auth::requireLogin();
$skillModel = new Skill();

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $userModel = new User();
    $skills = $userModel->getSkills($user['uid']);
    Response::success($skills);
} elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = Validator::getJsonInput();

    $check = Validator::required($input, ['sid']);
    if (!$check['valid']) {
        Response::badRequest($check['message']);
    }

    $skill = $skillModel->findById($input['sid']);
    if (!$skill) {
        Response::badRequest('技能标签不存在');
    }

    if ($skillModel->hasUserSkill($user['uid'], $input['sid'])) {
        Response::badRequest('您已拥有该技能');
    }

    $proficiency = isset($input['proficiency']) ? min(5, max(1, (int)$input['proficiency'])) : 1;
    $skillModel->addUserSkill($user['uid'], $input['sid'], $proficiency);
    Response::success(null, '技能添加成功');
} elseif ($_SERVER['REQUEST_METHOD'] === 'DELETE') {
    $input = Validator::getJsonInput();

    $check = Validator::required($input, ['sid']);
    if (!$check['valid']) {
        Response::badRequest($check['message']);
    }

    if (!$skillModel->hasUserSkill($user['uid'], $input['sid'])) {
        Response::badRequest('您尚未拥有该技能');
    }

    $skillModel->removeUserSkill($user['uid'], $input['sid']);
    Response::success(null, '技能删除成功');
} else {
    Response::error(405, '请求方法不允许');
}
