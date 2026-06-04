<?php
class Member
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * 检查用户是否已是某项目成员
     * @param int $pid
     * @param int $uid
     * @return bool
     */
    public function isMember($pid, $uid)
    {
        $stmt = $this->db->prepare("SELECT 1 FROM member WHERE pid = :pid AND uid = :uid LIMIT 1");
        $stmt->execute([':pid' => $pid, ':uid' => $uid]);
        return (bool)$stmt->fetch();
    }

    /**
     * 获取用户参与的所有项目
     * @param int $uid
     * @return array
     */
    public function getProjectsByUser($uid)
    {
        $stmt = $this->db->prepare(
            "SELECT m.pid, m.role, m.join_time, p.pname, p.status
             FROM member m
             JOIN project p ON m.pid = p.pid AND p.is_deleted = 0
             WHERE m.uid = :uid
             ORDER BY m.join_time DESC"
        );
        $stmt->execute([':uid' => $uid]);
        return $stmt->fetchAll();
    }
}
