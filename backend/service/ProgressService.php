<?php
class ProgressService
{
    private $progressModel;

    public function __construct()
    {
        $this->progressModel = new Progress();
    }

    /**
     * 获取项目进度节点列表
     * @param int $pid
     * @return array
     */
    public function getListByProject($pid)
    {
        return $this->progressModel->getByProject($pid);
    }

    /**
     * 新增进度节点
     * @param array $data
     * @return array
     */
    public function create($data)
    {
        $prid = $this->progressModel->create($data);
        return ['success' => true, 'message' => '进度节点新增成功', 'prid' => $prid];
    }

    /**
     * 更新进度节点状态
     * @param int $prid
     * @param int $pid
     * @param int $status
     * @return array
     */
    public function updateStatus($prid, $pid, $status)
    {
        if (!$this->progressModel->belongsToProject($prid, $pid)) {
            return ['success' => false, 'message' => '进度节点不存在或不属于该项目'];
        }
        $this->progressModel->updateStatus($prid, $status);
        return ['success' => true, 'message' => '节点状态更新成功'];
    }
}
