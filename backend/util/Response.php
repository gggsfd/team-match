<?php
class Response
{
    /**
     * 统一JSON响应
     * @param int    $code    HTTP状态码
     * @param string $message 提示信息
     * @param mixed  $data    响应数据
     */
    public static function json($code, $message = '', $data = null)
    {
        http_response_code($code);
        header('Content-Type: application/json; charset=utf-8');
        header('Access-Control-Allow-Origin: *');
        header('Access-Control-Allow-Credentials: true');
        header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
        header('Access-Control-Allow-Headers: Content-Type');

        $response = [
            'code'    => $code,
            'message' => $message,
            'data'    => $data,
        ];
        echo json_encode($response, JSON_UNESCAPED_UNICODE);
        exit;
    }

    /**
     * 成功响应 (200)
     * @param mixed  $data
     * @param string $message
     */
    public static function success($data = null, $message = 'success')
    {
        self::json(200, $message, $data);
    }

    /**
     * 错误响应
     * @param int    $code
     * @param string $message
     */
    public static function error($code, $message)
    {
        self::json($code, $message, null);
    }

    /**
     * 资源不存在 (404)
     * @param string $message
     */
    public static function notFound($message = '资源不存在')
    {
        self::json(404, $message, null);
    }

    /**
     * 无权限 (403)
     * @param string $message
     */
    public static function forbidden($message = '无权限执行此操作')
    {
        self::json(403, $message, null);
    }

    /**
     * 参数错误 (400)
     * @param string $message
     */
    public static function badRequest($message = '请求参数有误')
    {
        self::json(400, $message, null);
    }

    /**
     * 未登录 (401)
     * @param string $message
     */
    public static function unauthorized($message = '请先登录')
    {
        self::json(401, $message, null);
    }

    /**
     * 服务器错误 (500)
     * @param string $message
     */
    public static function serverError($message = '服务器内部异常')
    {
        self::json(500, $message, null);
    }
}
