<?php
class CourseService
{
    private $courseModel;

    public function __construct()
    {
        $this->courseModel = new Course();
    }

    /**
     * 获取课程列表
     * @param string|null $semester
     * @return array
     */
    public function getList($semester = null)
    {
        return $this->courseModel->getAll($semester);
    }
}
