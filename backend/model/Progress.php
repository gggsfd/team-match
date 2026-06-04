<?php
class Progress
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * 获取项目的所有进度节点
     * @param int $pid
     * @return array
     */
    public function getByProject($pid)
    {
        $stmt = $this->db->prepare(
            "SELECT prid, pid, title, description, status, deadline, created_at, updated_at
             FROM progress
             WHERE pid = :pid
             ORDER BY deadline ASC, created_at ASC"
        );
        $stmt->execute([':pid' => $pid]);
        return $stmt->fetchAll();
    }

    /**
     * 新增进度节点
     * @param array $data
     * @return int
     */
    public function create($data)
    {
        $stmt = $this->db->prepare(
            "INSERT INTO progress (pid, title, description, deadline)
             VALUES (:pid, :title, :description, :deadline)"
        );
        $stmt->execute([
            ':pid'         => $data['pid'],
            ':title'       => $data['title'],
            ':description' => $data['description'] ?? null,
            ':deadline'    => $data['deadline'] ?? null,
        ]);
        return (int)$this->db->lastInsertId();
    }

    /**
     * 更新进度节点状态
     * @param int $prid
     * @param int $status
     * @return bool
     */
    public function updateStatus($prid, $status)
    {
        $stmt = $this->db->prepare("UPDATE progress SET status = :status WHERE prid = :prid");
        return $stmt->execute([':prid' => $prid, ':status' => $status]);
    }

    /**
     * 校验节点是否属于指定项目
     * @param int $prid
     * @param int $pid
     * @return bool
     */
    public function belongsToProject($prid, $pid)
    {
        $stmt = $this->db->prepare("SELECT 1 FROM progress WHERE prid = :prid AND pid = :pid LIMIT 1");
        $stmt->execute([':prid' => $prid, ':pid' => $pid]);
        return (bool)$stmt->fetch();
    }
}
