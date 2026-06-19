<?php
/**
 * 管理员API控制器
 * 仅 admin 角色可访问
 */
$user = Auth::requireLogin();
if ($user['role'] !== 'admin') {
    Response::forbidden('仅系统管理员可访问');
}

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    // GET /api/admin/users — 查询用户列表（含角色筛选、状态筛选、搜索、分页）
    $role = $_GET['role'] ?? null;
    $is_active = isset($_GET['is_active']) ? $_GET['is_active'] : null;
    $keyword = $_GET['keyword'] ?? null;
    $page = max(1, isset($_GET['page']) ? (int)$_GET['page'] : 1);
    $page_size = max(1, min(50, isset($_GET['page_size']) ? (int)$_GET['page_size'] : 15));

    $db = Database::getInstance();
    $where = ['u.is_deleted = 0'];
    $params = [];
    if ($role !== null && $role !== '') {
        $where[] = 'u.role = :role'; $params[':role'] = $role;
    }
    if ($is_active !== null && $is_active !== '') {
        $where[] = 'u.is_active = :is_active'; $params[':is_active'] = (int)$is_active;
    }
    if ($keyword) {
        $where[] = '(u.username LIKE :kw1 OR u.nickname LIKE :kw2)';
        $params[':kw1'] = "%{$keyword}%"; $params[':kw2'] = "%{$keyword}%";
    }
    $wsql = implode(' AND ', $where);

    $total = (int)$db->prepare("SELECT COUNT(*) AS cnt FROM user u WHERE {$wsql}")->execute($params)->fetch()['cnt'];
    $offset = ($page - 1) * $page_size;
    $stmt = $db->prepare("
        SELECT u.uid, u.username, u.nickname, u.email, u.phone, u.avatar,
               u.role, u.is_active, u.credit_score, u.created_at, u.updated_at,
               (SELECT COUNT(*) FROM user_skill us WHERE us.uid = u.uid) AS skill_count,
               (SELECT COUNT(*) FROM member m WHERE m.uid = u.uid) AS project_count
        FROM user u
        WHERE {$wsql}
        ORDER BY u.is_active DESC, u.uid ASC
        LIMIT :limit OFFSET :offset
    ");
    foreach ($params as $k => $v) $stmt->bindValue($k, $v);
    $stmt->bindValue(':limit', (int)$page_size, PDO::PARAM_INT);
    $stmt->bindValue(':offset', (int)$offset, PDO::PARAM_INT);
    $stmt->execute();
    $list = $stmt->fetchAll();
    Response::success(['list' => $list, 'total' => $total, 'page' => $page, 'page_size' => $page_size]);

} elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // POST /api/admin/users — 创建用户（管理后台）
    $input = Validator::getJsonInput();
    $check = Validator::required($input, ['username', 'password', 'nickname']);
    if (!$check['valid']) Response::badRequest($check['message']);
    $checkLen = Validator::length($input['password'], 6, 20, '密码');
    if (!$checkLen['valid']) Response::badRequest($checkLen['message']);

    $userModel = new User();
    if ($userModel->findByUsername($input['username'])) Response::badRequest('用户名已存在');

    define('PASSWORD_SALT', 'team_match_salt');
    $hp = md5($input['username'] . $input['password'] . PASSWORD_SALT);
    $db = Database::getInstance();
    $db->prepare("INSERT INTO user (username, password, nickname, email, phone, role, credit_score, is_active)
        VALUES (:uname, :pw, :nn, :email, :phone, :role, :cs, :ia)")
    ->execute([
        ':uname' => $input['username'], ':pw' => $hp, ':nn' => $input['nickname'],
        ':email' => $input['email'] ?? null, ':phone' => $input['phone'] ?? null,
        ':role' => $input['role'] ?? 'member', ':cs' => $input['credit_score'] ?? 100,
        ':ia' => $input['is_active'] ?? 1,
    ]);
    Response::success(['uid' => (int)$db->lastInsertId()], '用户创建成功');

} elseif ($_SERVER['REQUEST_METHOD'] === 'PUT') {
    // PUT /api/admin/users — 编辑用户（角色、状态、资料）
    $input = Validator::getJsonInput();
    if (empty($input['uid'])) Response::badRequest('uid不能为空');
    $uid = (int)$input['uid'];
    if ($uid == $user['uid']) Response::badRequest('不可修改自己的信息');

    $fields = []; $params = [':uid' => $uid];
    foreach (['nickname','email','phone','role','credit_score'] as $f) {
        if (array_key_exists($f, $input)) {
            $fields[] = "`{$f}` = :{$f}";
            $params[":{$f}"] = $input[$f];
        }
    }
    if (array_key_exists('is_active', $input)) {
        $fields[] = "is_active = :is_active";
        $params[':is_active'] = (int)$input['is_active'];
    }
    if (empty($fields)) Response::badRequest('无可更新的字段');

    $db = Database::getInstance();
    $db->prepare("UPDATE user SET " . implode(', ', $fields) . " WHERE uid = :uid AND is_deleted = 0")->execute($params);
    Response::success(null, '用户资料更新成功');

} else {
    Response::error(405, '请求方法不允许');
}
