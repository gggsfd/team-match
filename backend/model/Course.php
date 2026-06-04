<?php
class Course
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * 获取所有课程列表（可选按学期筛选），含每个课程下的项目数
     * @param string|null $semester
     * @return array
     */
    public function getAll($semester = null)
    {
        $sql = "SELECT c.*,
                       (SELECT COUNT(*) FROM project p WHERE p.cid = c.cid AND p.is_deleted = 0) AS project_count
                FROM course c
                WHERE c.is_deleted = 0";
        $params = [];

        if ($semester !== null && $semester !== '') {
            $sql .= " AND c.semester = :semester";
            $params[':semester'] = $semester;
        }

        $sql .= " ORDER BY c.created_at DESC";
        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll();
    }

    /**
     * 根据CID查找课程
     * @param int $cid
     * @return array|null
     */
    public function findById($cid)
    {
        $stmt = $this->db->prepare("SELECT * FROM course WHERE cid = :cid AND is_deleted = 0");
        $stmt->execute([':cid' => $cid]);
        $course = $stmt->fetch();
        return $course ?: null;
    }
}
