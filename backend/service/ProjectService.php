<?php
class ProjectService
{
    private $projectModel;
    private $applicationModel;
    private $memberModel;

    public function __construct()
    {
        $this->projectModel = new Project();
        $this->applicationModel = new Application();
        $this->memberModel = new Member();
    }

    /**
     * 发布新项目（含需求技能设置和自动设为组长）
     * @param array $data
     * @return array ['success' => bool, 'message' => string, 'pid' => int|null]
     */
    public function create($data)
    {
        $db = Database::getInstance();
        $db->beginTransaction();

        try {
            $pid = $this->projectModel->create([
                'cid'         => $data['cid'],
                'uid'         => $data['uid'],
                'pname'       => $data['pname'],
                'description' => $data['description'] ?? null,
                'max_members' => $data['max_members'] ?? 4,
                'deadline'    => $data['deadline'] ?? null,
            ]);

            if (!$pid) {
                $db->rollBack();
                return ['success' => false, 'message' => '项目创建失败'];
            }

            foreach ($data['skill_ids'] as $sid) {
                $this->projectModel->addRequiredSkill($pid, $sid);
            }

            $this->projectModel->addMember($pid, $data['uid'], 'leader');

            $db->commit();
            return ['success' => true, 'message' => '项目发布成功', 'pid' => $pid];
        } catch (Exception $e) {
            $db->rollBack();
            return ['success' => false, 'message' => '发布失败：' . $e->getMessage()];
        }
    }

    /**
     * 获取项目列表（含筛选和分页）
     * @param array $filters
     * @param int   $page
     * @param int   $pageSize
     * @return array
     */
    public function getList($filters = [], $page = 1, $pageSize = 10)
    {
        return $this->projectModel->getList($filters, $page, $pageSize);
    }

    /**
     * 获取项目详情（含技能、成员、当前用户申请状态）
     * @param int      $pid
     * @param int|null $currentUid
     * @return array|null
     */
    public function getDetail($pid, $currentUid = null)
    {
        $project = $this->projectModel->findById($pid);
        if (!$project) {
            return null;
        }

        $project['required_skills'] = $this->projectModel->getRequiredSkills($pid);
        $project['members'] = $this->projectModel->getMembers($pid);
        $project['current_members'] = count($project['members']);
        $project['status_text'] = $this->getStatusText($project['status']);

        $project['course'] = [
            'cid'     => $project['cid'],
            'cname'   => $project['course_name'],
            'teacher' => $project['course_teacher'],
        ];

        $project['creator'] = [
            'uid'      => $project['uid'],
            'nickname' => $project['creator_nickname'],
        ];

        if ($currentUid !== null) {
            $project['my_application_status'] = $this->applicationModel->getMyApplicationStatus($pid, $currentUid);
        } else {
            $project['my_application_status'] = null;
        }

        $skillStmt = Database::getInstance()->prepare(
            "SELECT s.sname FROM project_skill ps JOIN skill s ON ps.sid = s.sid WHERE ps.pid = :pid"
        );
        $skillStmt->execute([':pid' => $pid]);
        $project['skills'] = array_column($skillStmt->fetchAll(), 'sname');

        return $project;
    }

    /**
     * 获取状态文本
     * @param int $status
     * @return string
     */
    private function getStatusText($status)
    {
        $map = [0 => '招募中', 1 => '已满', 2 => '进行中', 3 => '已结束'];
        return $map[(int)$status] ?? '未知';
    }
}
