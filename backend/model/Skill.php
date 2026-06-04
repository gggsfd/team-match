<?php
class Skill
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * 获取所有技能标签
     * @return array
     */
    public function getAll()
    {
        $stmt = $this->db->query("SELECT sid, sname, category FROM skill ORDER BY sid ASC");
        return $stmt->fetchAll();
    }

    /**
     * 根据SID查找技能
     * @param int $sid
     * @return array|null
     */
    public function findById($sid)
    {
        $stmt = $this->db->prepare("SELECT sid, sname, category FROM skill WHERE sid = :sid");
        $stmt->execute([':sid' => $sid]);
        $skill = $stmt->fetch();
        return $skill ?: null;
    }

    /**
     * 为用户添加技能
     * @param int $uid
     * @param int $sid
     * @param int $proficiency
     * @return bool
     */
    public function addUserSkill($uid, $sid, $proficiency = 1)
    {
        $stmt = $this->db->prepare(
            "INSERT INTO user_skill (uid, sid, proficiency) VALUES (:uid, :sid, :proficiency)"
        );
        return $stmt->execute([
            ':uid'         => $uid,
            ':sid'         => $sid,
            ':proficiency' => $proficiency,
        ]);
    }

    /**
     * 删除用户技能
     * @param int $uid
     * @param int $sid
     * @return bool
     */
    public function removeUserSkill($uid, $sid)
    {
        $stmt = $this->db->prepare("DELETE FROM user_skill WHERE uid = :uid AND sid = :sid");
        return $stmt->execute([':uid' => $uid, ':sid' => $sid]);
    }

    /**
     * 检查用户是否已拥有某技能
     * @param int $uid
     * @param int $sid
     * @return bool
     */
    public function hasUserSkill($uid, $sid)
    {
        $stmt = $this->db->prepare("SELECT 1 FROM user_skill WHERE uid = :uid AND sid = :sid LIMIT 1");
        $stmt->execute([':uid' => $uid, ':sid' => $sid]);
        return (bool)$stmt->fetch();
    }
}
