<?php
define('PASSWORD_SALT', 'team_match_salt');

class UserService
{
    private $userModel;

    public function __construct()
    {
        $this->userModel = new User();
    }

    /**
     * 用户注册
     * @param array $data
     * @return array ['success' => bool, 'message' => string, 'uid' => int|null]
     */
    public function register($data)
    {
        $existing = $this->userModel->findByUsername($data['username']);
        if ($existing) {
            return ['success' => false, 'message' => '用户名已存在'];
        }

        $hashedPassword = $this->hashPassword($data['username'], $data['password']);

        $uid = $this->userModel->create([
            'username' => $data['username'],
            'password' => $hashedPassword,
            'nickname' => $data['nickname'],
            'email'    => $data['email'] ?? null,
            'phone'    => $data['phone'] ?? null,
        ]);

        return $uid ? ['success' => true, 'message' => '注册成功', 'uid' => $uid]
                    : ['success' => false, 'message' => '注册失败'];
    }

    /**
     * 用户登录
     * @param string $username
     * @param string $password
     * @return array ['success' => bool, 'message' => string, 'user' => array|null]
     */
    public function login($username, $password)
    {
        $user = $this->userModel->findByUsername($username);
        if (!$user) {
            return ['success' => false, 'message' => '用户名或密码错误'];
        }

        $hashedInput = $this->hashPassword($username, $password);
        if ($user['password'] !== $hashedInput) {
            return ['success' => false, 'message' => '用户名或密码错误'];
        }

        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        $_SESSION['uid'] = $user['uid'];
        $_SESSION['username'] = $user['username'];
        $_SESSION['role'] = $user['role'] ?? 'member';

        unset($user['password']);
        return ['success' => true, 'message' => '登录成功', 'user' => $user];
    }

    /**
     * 获取用户完整资料（含技能）
     * @param int $uid
     * @return array|null
     */
    public function getProfile($uid)
    {
        $user = $this->userModel->findByUid($uid);
        if (!$user) {
            return null;
        }
        $user['skills'] = $this->userModel->getSkills($uid);

        $memberModel = new Member();
        $user['projects'] = $memberModel->getProjectsByUser($uid);

        return $user;
    }

    /**
     * 修改用户资料
     * @param int   $uid
     * @param array $data
     * @return array ['success' => bool, 'message' => string]
     */
    public function updateProfile($uid, $data)
    {
        $result = $this->userModel->updateProfile($uid, $data);
        return $result ? ['success' => true, 'message' => '资料更新成功']
                       : ['success' => false, 'message' => '资料更新失败'];
    }

    /**
     * 密码加密
     * @param string $username
     * @param string $password
     * @return string
     */
    private function hashPassword($username, $password)
    {
        return md5($username . $password . PASSWORD_SALT);
    }
}
