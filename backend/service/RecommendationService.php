<?php
class RecommendationService
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * 获取当前用户的智能推荐项目列表
     * @param int      $uid 当前用户ID
     * @param int|null $cid 课程筛选（可选）
     * @return array 推荐项目列表，按匹配度降序
     */
    public function getRecommendations($uid, $cid = null)
    {
        $sql = "
            SELECT
                p.pid, p.pname, p.description,
                p.max_members, p.deadline, p.created_at,
                (SELECT COUNT(*) FROM member m WHERE m.pid = p.pid) AS current_members,
                COUNT(DISTINCT ps.sid) AS need_skills,
                COUNT(DISTINCT CASE WHEN us.uid = :uid THEN us.sid END) AS matched_skills,
                ROUND(
                    COUNT(DISTINCT CASE WHEN us.uid = :uid2 THEN us.sid END) * 100.0
                    / NULLIF(COUNT(DISTINCT ps.sid), 0), 2
                ) AS match_rate,
                GROUP_CONCAT(DISTINCT CASE WHEN us.uid = :uid3 THEN sk.sname END SEPARATOR '、') AS matched_skill_names,
                GROUP_CONCAT(DISTINCT CASE WHEN us_all.uid IS NULL THEN s_all.sname END SEPARATOR '、') AS unmatched_skill_names,
                c.cid AS course_cid,
                c.cname AS course_cname,
                u.uid AS creator_uid,
                u.nickname AS creator_nickname
            FROM project p
            JOIN course c ON p.cid = c.cid AND c.is_deleted = 0
            JOIN user u ON p.uid = u.uid AND u.is_deleted = 0
            JOIN project_skill ps ON p.pid = ps.pid
            LEFT JOIN user_skill us ON ps.sid = us.sid AND us.uid = :uid4
            LEFT JOIN user_skill us_all ON ps.sid = us_all.sid
            LEFT JOIN skill sk ON us.sid = sk.sid
            LEFT JOIN skill s_all ON ps.sid = s_all.sid
            WHERE p.status = 0
              AND p.is_deleted = 0
              AND p.pid NOT IN (SELECT mm.pid FROM member mm WHERE mm.uid = :uid5)
              AND p.pid NOT IN (SELECT aa.pid FROM application aa WHERE aa.uid = :uid6 AND aa.status = 0)
        ";

        $params = [
            ':uid'  => $uid, ':uid2' => $uid, ':uid3' => $uid,
            ':uid4' => $uid, ':uid5' => $uid, ':uid6' => $uid,
        ];

        if ($cid !== null && $cid !== '') {
            $sql .= " AND p.cid = :cid";
            $params[':cid'] = (int)$cid;
        }

        $sql .= "
            GROUP BY p.pid, c.cid, c.cname, u.uid, u.nickname
            HAVING matched_skills > 0
            ORDER BY match_rate DESC, p.created_at DESC
        ";

        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        $results = $stmt->fetchAll();

        foreach ($results as &$item) {
            $item['matched_skills'] = $item['matched_skill_names']
                ? explode('、', $item['matched_skill_names']) : [];
            $item['unmatched_skills'] = $item['unmatched_skill_names']
                ? explode('、', $item['unmatched_skill_names']) : [];
            $item['match_rate'] = (float)$item['match_rate'];

            $skillStmt = $this->db->prepare(
                "SELECT s.sname FROM project_skill ps JOIN skill s ON ps.sid = s.sid WHERE ps.pid = :pid"
            );
            $skillStmt->execute([':pid' => $item['pid']]);
            $item['skills'] = array_column($skillStmt->fetchAll(), 'sname');

            unset($item['matched_skill_names'], $item['unmatched_skill_names']);
        }

        return $results;
    }
}
