<?php
/**
 * 管理员项目管理API
 * 仅 admin 角色可访问
 */
$user = Auth::requireLogin();
if ($user['role'] !== 'admin') {
    Response::forbidden('仅系统管理员可访问');
}

$db = Database::getInstance();

// GET — 查询项目列表（含筛选、搜索、分页）
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $cid = $_GET['cid'] ?? null;
    $status = $_GET['status'] ?? null;
    $keyword = $_GET['keyword'] ?? null;
    $page = max(1, isset($_GET['page']) ? (int)$_GET['page'] : 1);
    $page_size = max(1, min(50, isset($_GET['page_size']) ? (int)$_GET['page_size'] : 15));

    $where = ['p.is_deleted = 0'];
    $params = [];
    if ($cid !== null && $cid !== '') {
        $where[] = 'p.cid = :cid';
        $params[':cid'] = (int)$cid;
    }
    if ($status !== null && $status !== '') {
        $where[] = 'p.status = :status';
        $params[':status'] = (int)$status;
    }
    if ($keyword) {
        $where[] = 'p.pname LIKE :kw';
        $params[':kw'] = "%{$keyword}%";
    }
    $wsql = implode(' AND ', $where);

    $countStmt = $db->prepare("SELECT COUNT(*) AS cnt FROM project p WHERE {$wsql}");
    $countStmt->execute($params);
    $total = (int)$countStmt->fetch()['cnt'];

    $offset = ($page - 1) * $page_size;
    $stmt = $db->prepare("
        SELECT p.pid, p.pname, p.description, p.max_members, p.status, p.deadline, p.created_at,
               (SELECT COUNT(*) FROM member m WHERE m.pid = p.pid) AS current_members,
               u.uid AS creator_uid, u.nickname AS creator_nickname,
               c.cid AS course_cid, c.cname AS course_cname
        FROM project p
        JOIN user u ON p.uid = u.uid
        JOIN course c ON p.cid = c.cid
        WHERE {$wsql}
        ORDER BY p.created_at DESC
        LIMIT :limit OFFSET :offset
    ");
    foreach ($params as $k => $v) {
        $stmt->bindValue($k, $v);
    }
    $stmt->bindValue(':limit', (int)$page_size, PDO::PARAM_INT);
    $stmt->bindValue(':offset', (int)$offset, PDO::PARAM_INT);
    $stmt->execute();
    $list = $stmt->fetchAll();

    // 批量获取技能标签
    if ($list) {
        $pids = array_column($list, 'pid');
        $placeholders = implode(',', array_fill(0, count($pids), '?'));
        $skillStmt = $db->prepare("
            SELECT ps.pid, s.sname
            FROM project_skill ps
            JOIN skill s ON ps.sid = s.sid
            WHERE ps.pid IN ({$placeholders})
        ");
        $skillStmt->execute($pids);
        $skillRows = $skillStmt->fetchAll();

        $skillMap = [];
        foreach ($skillRows as $sr) {
            $skillMap[$sr['pid']][] = $sr['sname'];
        }
        foreach ($list as &$r) {
            $r['skills'] = $skillMap[$r['pid']] ?? [];
            $r['status_text'] = [0 => '招募中', 1 => '已满', 2 => '进行中', 3 => '已结束'][$r['status']] ?? '';
        }
    }

    Response::success(['list' => $list, 'total' => $total, 'page' => $page, 'page_size' => $page_size]);
}

// PUT — 编辑项目
elseif ($_SERVER['REQUEST_METHOD'] === 'PUT') {
    $input = Validator::getJsonInput();
    if (empty($input['pid'])) {
        Response::badRequest('pid不能为空');
    }
    $pid = (int)$input['pid'];

    $checkStmt = $db->prepare("SELECT 1 FROM project WHERE pid = :pid AND is_deleted = 0");
    $checkStmt->execute([':pid' => $pid]);
    if (!$checkStmt->fetch()) {
        Response::notFound('项目不存在');
    }

    $fields = [];
    $params = [':pid' => $pid];
    foreach (['pname', 'description', 'deadline'] as $f) {
        if (array_key_exists($f, $input)) {
            $fields[] = "`{$f}` = :{$f}";
            $params[":{$f}"] = $input[$f];
        }
    }
    if (array_key_exists('max_members', $input)) {
        $v = (int)$input['max_members'];
        if ($v < 1 || $v > 20) Response::badRequest('人数范围1-20');
        $fields[] = 'max_members = :max_members';
        $params[':max_members'] = $v;
    }
    if (array_key_exists('status', $input)) {
        $v = (int)$input['status'];
        if (!in_array($v, [0, 1, 2, 3])) Response::badRequest('无效状态值');
        $fields[] = 'status = :status';
        $params[':status'] = $v;
    }
    if (array_key_exists('cid', $input)) {
        $v = (int)$input['cid'];
        $courseStmt = $db->prepare("SELECT 1 FROM course WHERE cid = :cid");
        $courseStmt->execute([':cid' => $v]);
        if (!$courseStmt->fetch()) Response::badRequest('课程不存在');
        $fields[] = 'cid = :cid';
        $params[':cid'] = $v;
    }
    if (empty($fields)) {
        Response::badRequest('无可更新的字段');
    }

    $stmt = $db->prepare("UPDATE project SET " . implode(', ', $fields) . " WHERE pid = :pid AND is_deleted = 0");
    $stmt->execute($params);
    Response::success(null, '更新成功');
}

// DELETE — 软删除项目
elseif ($_SERVER['REQUEST_METHOD'] === 'DELETE') {
    $input = Validator::getJsonInput();
    if (empty($input['pid'])) {
        Response::badRequest('pid不能为空');
    }
    $pid = (int)$input['pid'];

    $checkStmt = $db->prepare("SELECT 1 FROM project WHERE pid = :pid AND is_deleted = 0");
    $checkStmt->execute([':pid' => $pid]);
    if (!$checkStmt->fetch()) {
        Response::notFound('项目不存在');
    }

    $stmt = $db->prepare("UPDATE project SET is_deleted = 1 WHERE pid = :pid");
    $stmt->execute([':pid' => $pid]);
    Response::success(null, '项目已删除');
}

else {
    Response::error(405, '请求方法不允许');
}
