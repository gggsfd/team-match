<?php
class User
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * 根据用户名查找用户（含软删除过滤）
     * @param string $username
     * @return array|null
     */
    public function findByUsername($username)
    {
        $stmt = $this->db->prepare(
            "SELECT uid, username, password, nickname, email, phone, avatar, credit_score, role, is_active, created_at
             FROM user WHERE username = :username AND is_deleted = 0"
        );
        $stmt->execute([':username' => $username]);
        $user = $stmt->fetch();
        return $user ?: null;
    }

    /**
     * 根据UID查找用户
     * @param int $uid
     * @return array|null
     */
    public function findByUid($uid)
    {
        $stmt = $this->db->prepare(
            "SELECT uid, username, nickname, email, phone, avatar, credit_score, role, is_active, created_at
             FROM user WHERE uid = :uid AND is_deleted = 0"
        );
        $stmt->execute([':uid' => $uid]);
        $user = $stmt->fetch();
        return $user ?: null;
    }

    /**
     * 创建新用户
     * @param array $data
     * @return int|false 返回新用户UID或false
     */
    public function create($data)
    {
        $stmt = $this->db->prepare(
            "INSERT INTO user (username, password, nickname, email, phone)
             VALUES (:username, :password, :nickname, :email, :phone)"
        );
        $stmt->execute([
            ':username' => $data['username'],
            ':password' => $data['password'],
            ':nickname' => $data['nickname'],
            ':email'    => $data['email'] ?? null,
            ':phone'    => $data['phone'] ?? null,
        ]);
        return (int)$this->db->lastInsertId();
    }

    /**
     * 更新用户资料
     * @param int   $uid
     * @param array $data
     * @return bool
     */
    public function updateProfile($uid, $data)
    {
        $fields = [];
        $params = [':uid' => $uid];

        if (isset($data['nickname'])) {
            $fields[] = 'nickname = :nickname';
            $params[':nickname'] = $data['nickname'];
        }
        if (array_key_exists('email', $data)) {
            $fields[] = 'email = :email';
            $params[':email'] = $data['email'];
        }
        if (array_key_exists('phone', $data)) {
            $fields[] = 'phone = :phone';
            $params[':phone'] = $data['phone'];
        }
        if (isset($data['avatar'])) {
            $fields[] = 'avatar = :avatar';
            $params[':avatar'] = $data['avatar'];
        }

        if (empty($fields)) {
            return false;
        }

        $sql = "UPDATE user SET " . implode(', ', $fields) . " WHERE uid = :uid AND is_deleted = 0";
        $stmt = $this->db->prepare($sql);
        return $stmt->execute($params);
    }

    /**
     * 获取用户的技能列表（含关联查询）
     * @param int $uid
     * @return array
     */
    public function getSkills($uid)
    {
        $stmt = $this->db->prepare(
            "SELECT s.sid, s.sname, s.category, us.proficiency
             FROM user_skill us
             JOIN skill s ON us.sid = s.sid
             WHERE us.uid = :uid
             ORDER BY us.created_at ASC"
        );
        $stmt->execute([':uid' => $uid]);
        return $stmt->fetchAll();
    }

    /**
     * 获取所有可选技能标签
     * @return array
     */
    public function getAllSkills()
    {
        $stmt = $this->db->query("SELECT sid, sname, category FROM skill ORDER BY sid ASC");
        return $stmt->fetchAll();
    }
}
