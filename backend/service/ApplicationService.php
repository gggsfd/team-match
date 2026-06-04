<?php
class ApplicationService
{
    private $applicationModel;
    private $memberModel;
    private $projectModel;

    public function __construct()
    {
        $this->applicationModel = new Application();
        $this->memberModel = new Member();
        $this->projectModel = new Project();
    }

    /**
     * 发起入组申请
     * @param int    $pid
     * @param int    $uid
     * @param string $message
     * @return array ['success' => bool, 'message' => string, 'aid' => int|null]
     */
    public function apply($pid, $uid, $message = null)
    {
        $project = $this->projectModel->findById($pid);
        if (!$project) {
            return ['success' => false, 'message' => '项目不存在'];
        }

        if ((int)$project['status'] !== 0) {
            return ['success' => false, 'message' => '该项目已结束招募'];
        }

        if ((int)$project['uid'] === (int)$uid) {
            return ['success' => false, 'message' => '不可申请自己创建的项目'];
        }

        if ($this->memberModel->isMember($pid, $uid)) {
            return ['success' => false, 'message' => '您已是该项目成员，无需重复申请'];
        }

        if ($this->applicationModel->hasPendingApplication($pid, $uid)) {
            return ['success' => false, 'message' => '您已申请过该项目，请勿重复申请'];
        }

        $aid = $this->applicationModel->create($pid, $uid, $message);
        return $aid ? ['success' => true, 'message' => '申请已提交，请等待组长审核', 'aid' => $aid]
                    : ['success' => false, 'message' => '申请提交失败'];
    }

    /**
     * 获取项目申请列表（组长视角）
     * @param int $pid
     * @return array
     */
    public function getApplicationsByProject($pid)
    {
        return $this->applicationModel->getListByProject($pid, 0);
    }

    /**
     * 审批入组申请（通过/拒绝）
     * @param int    $aid         申请ID
     * @param int    $operatorUid 操作者UID
     * @param string $action      'accept' 或 'reject'
     * @return array
     */
    public function handleApplication($aid, $operatorUid, $action)
    {
        $app = $this->applicationModel->findById($aid);
        if (!$app) {
            return ['success' => false, 'message' => '申请不存在'];
        }

        if ((int)$app['leader_uid'] !== (int)$operatorUid) {
            return ['success' => false, 'message' => '仅项目组长可审批申请'];
        }

        if ((int)$app['status'] !== 0) {
            return ['success' => false, 'message' => '该申请已处理'];
        }

        $db = Database::getInstance();
        $db->beginTransaction();

        try {
            if ($action === 'accept') {
                $currentMembers = $this->projectModel->getMemberCount($app['pid']);
                if ($currentMembers >= (int)$app['max_members']) {
                    $db->rollBack();
                    return ['success' => false, 'message' => '项目已满员，无法通过申请'];
                }

                $this->applicationModel->updateStatus($aid, 1);
                $this->projectModel->addMember($app['pid'], $app['uid'], 'member');

                $newCount = $currentMembers + 1;
                $statusChanged = false;
                if ($newCount >= (int)$app['max_members']) {
                    $this->projectModel->updateStatus($app['pid'], 1);
                    $statusChanged = true;
                }

                $db->commit();
                return [
                    'success' => true,
                    'message' => '申请已通过，成员已加入项目',
                    'project_status_changed' => $statusChanged,
                ];
            } else {
                $this->applicationModel->updateStatus($aid, 2);
                $db->commit();
                return ['success' => true, 'message' => '申请已拒绝'];
            }
        } catch (Exception $e) {
            $db->rollBack();
            return ['success' => false, 'message' => '操作失败：' . $e->getMessage()];
        }
    }
}
