<?php
if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    Response::error(405, '请求方法不允许');
}

$user = Auth::requireLogin();
$cid = isset($_GET['cid']) ? $_GET['cid'] : null;

$recommendationService = new RecommendationService();
$recommendations = $recommendationService->getRecommendations($user['uid'], $cid);

foreach ($recommendations as &$item) {
    $item['status_text'] = '招募中';
    $item['course'] = [
        'cid'   => $item['course_cid'],
        'cname' => $item['course_cname'],
    ];
    $item['creator'] = [
        'uid'      => $item['creator_uid'],
        'nickname' => $item['creator_nickname'],
    ];
    unset($item['course_cid'], $item['course_cname'], $item['creator_uid'], $item['creator_nickname']);
}

Response::success($recommendations);
