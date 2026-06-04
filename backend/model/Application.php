<?php
class Application
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * 创建入组申请
     * @param int    $pid
     * @param int    $uid
     * @param string $message
     * @return int|false
     */
    public function create($pid, $uid, $message = null)
    {
        $stmt = $this->db->prepare(
            "INSERT INTO application (pid, uid, message, status) VALUES (:pid, :uid, :message, 0)"
        );
        $stmt->execute([
            ':pid'     => $pid,
            ':uid'     => $uid,
            ':message' => $message,
        ]);
        return (int)$this->db->lastInsertId();
    }

    /**
     * 检查用户是否已存在待处理申请
     * @param int $pid
     * @param int $uid
     * @return bool
     */
    public function hasPendingApplication($pid, $uid)
    {
        $stmt = $this->db->prepare(
            "SELECT 1 FROM application WHERE pid = :pid AND uid = :uid AND status = 0 LIMIT 1"
        );
        $stmt->execute([':pid' => $pid, ':uid' => $uid]);
        return (bool)$stmt->fetch();
    }

    /**
     * 获取用户对项目的最新申请状态
     * @param int $pid
     * @param int $uid
     * @return int|null
     */
    public function getMyApplicationStatus($pid, $uid)
    {
        $stmt = $this->db->prepare(
            "SELECT status FROM application WHERE pid = :pid AND uid = :uid ORDER BY aid DESC LIMIT 1"
        );
        $stmt->execute([':pid' => $pid, ':uid' => $uid]);
        $row = $stmt->fetch();
        return $row ? (int)$row['status'] : null;
    }

    /**
     * 根据AID查找申请
     * @param int $aid
     * @return array|null
     */
    public function findById($aid)
    {
        $stmt = $this->db->prepare(
            "SELECT a.*, p.uid AS leader_uid, p.pid, p.max_members, p.status AS project_status
             FROM application a
             JOIN project p ON a.pid = p.pid AND p.is_deleted = 0
             WHERE a.aid = :aid"
        );
        $stmt->execute([':aid' => $aid]);
        $app = $stmt->fetch();
        return $app ?: null;
    }

    /**
     * 获取项目的申请列表（含申请人技能）
     * @param int $pid
     * @param int $status 筛选状态，null表示全部
     * @return array
     */
    public function getListByProject($pid, $status = null)
    {
        $sql = "
            SELECT a.aid, a.uid, a.message, a.status, a.apply_time, a.handle_time,
                   u.nickname, u.avatar
            FROM application a
            JOIN user u ON a.uid = u.uid AND u.is_deleted = 0
            WHERE a.pid = :pid
        ";
        $params = [':pid' => $pid];

        if ($status !== null) {
            $sql .= " AND a.status = :status";
            $params[':status'] = $status;
        }

        $sql .= " ORDER BY a.apply_time DESC";
        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        $applications = $stmt->fetchAll();

        foreach ($applications as &$app) {
            $skillStmt = $this->db->prepare(
                "SELECT s.sid, s.sname, us.proficiency
                 FROM user_skill us
                 JOIN skill s ON us.sid = s.sid
                 WHERE us.uid = :uid"
            );
            $skillStmt->execute([':uid' => $app['uid']]);
            $app['skills'] = $skillStmt->fetchAll();
        }

        return $applications;
    }

    /**
     * 更新申请状态
     * @param int $aid
     * @param int $status
     * @return bool
     */
    public function updateStatus($aid, $status)
    {
        if ($status === 1 || $status === 2) {
            $stmt = $this->db->prepare(
                "UPDATE application SET status = :status, handle_time = NOW() WHERE aid = :aid"
            );
        } else {
            $stmt = $this->db->prepare(
                "UPDATE application SET status = :status WHERE aid = :aid"
            );
        }
        return $stmt->execute([':aid' => $aid, ':status' => $status]);
    }
}
