<?php
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $semester = $_GET['semester'] ?? null;
    $courseService = new CourseService();
    $courses = $courseService->getList($semester);
    Response::success($courses);
} else {
    Response::error(405, '请求方法不允许');
}
