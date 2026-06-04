<?php
class Validator
{
    /**
     * 校验必填字段
     * @param array $data   待校验数据
     * @param array $fields 必填字段列表
     * @return array ['valid' => bool, 'message' => string]
     */
    public static function required($data, $fields)
    {
        foreach ($fields as $field) {
            if (!isset($data[$field]) || (is_string($data[$field]) && trim($data[$field]) === '')) {
                return ['valid' => false, 'message' => "{$field}不能为空"];
            }
        }
        return ['valid' => true, 'message' => ''];
    }

    /**
     * 校验字符串长度
     * @param string $value
     * @param int    $min
     * @param int    $max
     * @param string $fieldName
     * @return array
     */
    public static function length($value, $min, $max, $fieldName = '')
    {
        $len = mb_strlen($value, 'UTF-8');
        if ($len < $min || $len > $max) {
            $label = $fieldName ?: '字段';
            return ['valid' => false, 'message' => "{$label}长度必须在{$min}-{$max}之间"];
        }
        return ['valid' => true, 'message' => ''];
    }

    /**
     * 校验是否为有效正整数
     * @param mixed  $value
     * @param string $fieldName
     * @return array
     */
    public static function isInt($value, $fieldName = '')
    {
        if (!is_numeric($value) || intval($value) != $value || intval($value) <= 0) {
            $label = $fieldName ?: '参数';
            return ['valid' => false, 'message' => "{$label}必须为正整数"];
        }
        return ['valid' => true, 'message' => ''];
    }

    /**
     * 校验是否为有效整数（允许0和负数）
     * @param mixed  $value
     * @param string $fieldName
     * @return array
     */
    public static function isAnyInt($value, $fieldName = '')
    {
        if (!is_numeric($value) || intval($value) != $value) {
            $label = $fieldName ?: '参数';
            return ['valid' => false, 'message' => "{$label}必须为整数"];
        }
        return ['valid' => true, 'message' => ''];
    }

    /**
     * 校验是否为数组且非空
     * @param mixed  $value
     * @param string $fieldName
     * @return array
     */
    public static function isNonEmptyArray($value, $fieldName = '')
    {
        if (!is_array($value) || count($value) === 0) {
            $label = $fieldName ?: '参数';
            return ['valid' => false, 'message' => "{$label}必须为非空数组"];
        }
        return ['valid' => true, 'message' => ''];
    }

    /**
     * 获取POST请求的JSON Body
     * @return array
     */
    public static function getJsonInput()
    {
        $input = file_get_contents('php://input');
        $data = json_decode($input, true);
        if (!is_array($data)) {
            $data = [];
        }
        return $data;
    }
}
