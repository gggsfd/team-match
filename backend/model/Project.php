<?php
class Project
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * 创建项目
     * @param array $data
     * @return int|false
     */
    public function create($data)
    {
        $stmt = $this->db->prepare(
            "INSERT INTO project (cid, uid, pname, description, max_members, deadline)
             VALUES (:cid, :uid, :pname, :description, :max_members, :deadline)"
        );
        $stmt->execute([
            ':cid'         => $data['cid'],
            ':uid'         => $data['uid'],
            ':pname'       => $data['pname'],
            ':description' => $data['description'] ?? null,
            ':max_members' => $data['max_members'] ?? 4,
            ':deadline'    => $data['deadline'] ?? null,
        ]);
        return (int)$this->db->lastInsertId();
    }

    /**
     * 添加项目需求技能
     * @param int   $pid
     * @param int   $sid
     * @param int   $requiredCount
     * @return bool
     */
    public function addRequiredSkill($pid, $sid, $requiredCount = 1)
    {
        $stmt = $this->db->prepare(
            "INSERT INTO project_skill (pid, sid, required_count) VALUES (:pid, :sid, :required_count)"
        );
        return $stmt->execute([
            ':pid'            => $pid,
            ':sid'            => $sid,
            ':required_count' => $requiredCount,
        ]);
    }

    /**
     * 根据PID查询项目基本信息
     * @param int $pid
     * @return array|null
     */
    public function findById($pid)
    {
        $stmt = $this->db->prepare(
            "SELECT p.*, c.cname AS course_name, c.teacher AS course_teacher, c.semester,
                    u.nickname AS creator_nickname, u.username AS creator_username
             FROM project p
             JOIN course c ON p.cid = c.cid AND c.is_deleted = 0
             JOIN user u ON p.uid = u.uid AND u.is_deleted = 0
             WHERE p.pid = :pid AND p.is_deleted = 0"
        );
        $stmt->execute([':pid' => $pid]);
        $project = $stmt->fetch();
        return $project ?: null;
    }

    /**
     * 获取项目的需求技能列表
     * @param int $pid
     * @return array
     */
    public function getRequiredSkills($pid)
    {
        $stmt = $this->db->prepare(
            "SELECT ps.sid, s.sname, s.category, ps.required_count
             FROM project_skill ps
             JOIN skill s ON ps.sid = s.sid
             WHERE ps.pid = :pid"
        );
        $stmt->execute([':pid' => $pid]);
        return $stmt->fetchAll();
    }

    /**
     * 获取项目成员列表
     * @param int $pid
     * @return array
     */
    public function getMembers($pid)
    {
        $stmt = $this->db->prepare(
            "SELECT m.uid, u.nickname, u.avatar, m.role, m.join_time
             FROM member m
             JOIN user u ON m.uid = u.uid AND u.is_deleted = 0
             WHERE m.pid = :pid
             ORDER BY m.join_time ASC"
        );
        $stmt->execute([':pid' => $pid]);
        return $stmt->fetchAll();
    }

    /**
     * 获取当前成员人数
     * @param int $pid
     * @return int
     */
    public function getMemberCount($pid)
    {
        $stmt = $this->db->prepare("SELECT COUNT(*) AS cnt FROM member WHERE pid = :pid");
        $stmt->execute([':pid' => $pid]);
        $row = $stmt->fetch();
        return (int)$row['cnt'];
    }

    /**
     * 添加成员到项目
     * @param int    $pid
     * @param int    $uid
     * @param string $role
     * @return bool
     */
    public function addMember($pid, $uid, $role = 'member')
    {
        $stmt = $this->db->prepare(
            "INSERT INTO member (pid, uid, role) VALUES (:pid, :uid, :role)"
        );
        return $stmt->execute([
            ':pid'  => $pid,
            ':uid'  => $uid,
            ':role' => $role,
        ]);
    }

    /**
     * 更新项目状态
     * @param int $pid
     * @param int $status
     * @return bool
     */
    public function updateStatus($pid, $status)
    {
        $stmt = $this->db->prepare(
            "UPDATE project SET status = :status WHERE pid = :pid AND is_deleted = 0"
        );
        return $stmt->execute([':pid' => $pid, ':status' => $status]);
    }

    /**
     * 查询项目列表（支持筛选、搜索、分页）
     * @param array $filters
     * @param int   $page
     * @param int   $pageSize
     * @return array ['list' => [], 'total' => int]
     */
    public function getList($filters = [], $page = 1, $pageSize = 10)
    {
        $where = ["p.is_deleted = 0"];
        $params = [];

        if (!empty($filters['cid'])) {
            $where[] = "p.cid = :cid";
            $params[':cid'] = $filters['cid'];
        }
        if (isset($filters['status']) && $filters['status'] !== '') {
            $where[] = "p.status = :status";
            $params[':status'] = (int)$filters['status'];
        }
        if (!empty($filters['keyword'])) {
            $where[] = "p.pname LIKE :keyword";
            $params[':keyword'] = '%' . $filters['keyword'] . '%';
        }

        $whereSql = implode(' AND ', $where);

        $countSql = "SELECT COUNT(*) AS total FROM project p WHERE {$whereSql}";
        $countStmt = $this->db->prepare($countSql);
        $countStmt->execute($params);
        $total = (int)$countStmt->fetch()['total'];

        $offset = ($page - 1) * $pageSize;
        $listSql = "
            SELECT p.pid, p.pname, p.description, p.max_members, p.status, p.deadline, p.created_at,
                   (SELECT COUNT(*) FROM member m WHERE m.pid = p.pid) AS current_members,
                   u.uid AS creator_uid, u.nickname AS creator_nickname,
                   c.cid AS course_cid, c.cname AS course_cname
            FROM project p
            JOIN user u ON p.uid = u.uid AND u.is_deleted = 0
            JOIN course c ON p.cid = c.cid AND c.is_deleted = 0
            WHERE {$whereSql}
            ORDER BY p.created_at DESC
            LIMIT :limit OFFSET :offset
        ";
        $listStmt = $this->db->prepare($listSql);
        foreach ($params as $key => $val) {
            $listStmt->bindValue($key, $val);
        }
        $listStmt->bindValue(':limit', (int)$pageSize, PDO::PARAM_INT);
        $listStmt->bindValue(':offset', (int)$offset, PDO::PARAM_INT);
        $listStmt->execute();
        $list = $listStmt->fetchAll();

        foreach ($list as &$item) {
            $skillStmt = $this->db->prepare(
                "SELECT s.sname FROM project_skill ps JOIN skill s ON ps.sid = s.sid WHERE ps.pid = :pid"
            );
            $skillStmt->execute([':pid' => $item['pid']]);
            $item['skills'] = array_column($skillStmt->fetchAll(), 'sname');
        }

        return ['list' => $list, 'total' => $total];
    }
}
