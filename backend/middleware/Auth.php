<?php
class Auth
{
    /**
     * 校验当前请求是否已登录，未登录直接返回401并退出
     * @return array ['uid' => int, 'username' => string]
     */
    public static function requireLogin()
    {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        if (!isset($_SESSION['uid'])) {
            Response::unauthorized('请先登录');
            exit;
        }
        return [
            'uid'      => $_SESSION['uid'],
            'username' => $_SESSION['username'] ?? ''
        ];
    }

    /**
     * 获取当前登录用户ID（不强制要求登录，返回null表示未登录）
     * @return int|null
     */
    public static function getCurrentUid()
    {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        return $_SESSION['uid'] ?? null;
    }

    /**
     * 校验当前用户是否为指定项目的组长
     * @param int $pid 项目ID
     * @param int $uid 用户ID
     * @return bool
     */
    public static function isProjectLeader($pid, $uid)
    {
        $db = Database::getInstance();
        $stmt = $db->prepare("SELECT uid FROM project WHERE pid = :pid AND is_deleted = 0");
        $stmt->execute([':pid' => $pid]);
        $project = $stmt->fetch();
        return $project && (int)$project['uid'] === (int)$uid;
    }

    /**
     * 校验当前用户是否为项目成员（组长或组员）
     * @param int $pid 项目ID
     * @param int $uid 用户ID
     * @return bool
     */
    public static function isProjectMember($pid, $uid)
    {
        $db = Database::getInstance();
        $stmt = $db->prepare("SELECT 1 FROM member WHERE pid = :pid AND uid = :uid LIMIT 1");
        $stmt->execute([':pid' => $pid, ':uid' => $uid]);
        return (bool)$stmt->fetch();
    }

    /**
     * 校验当前用户是否为项目组长（含requireLogin检查），不是则返回403
     * @param int $pid 项目ID
     */
    public static function requireProjectLeader($pid)
    {
        $user = self::requireLogin();
        if (!self::isProjectLeader($pid, $user['uid'])) {
            Response::forbidden('仅项目组长可执行此操作');
            exit;
        }
        return $user;
    }
}
