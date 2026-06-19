"""
TeamMatch 后端模拟服务器 v2.0（Python）
======== 支持完整的RBAC权限 ========
"""
import http.server, json, os, hashlib, re, sqlite3, threading, time
from urllib.parse import urlparse, parse_qs
from datetime import datetime

PORT = 8080
ROOT = os.path.dirname(os.path.abspath(__file__))
SALT = 'team_match_salt'
DB_FILE = os.path.join(ROOT, '_team_match.db')

def hp(username, password):
    return hashlib.md5(f"{username}{password}{SALT}".encode()).hexdigest()

class DB:
    def __init__(self):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        self._file = DB_FILE
        self._local = threading.local()
        # 初始化连接
        c = self.conn
        c.execute("PRAGMA foreign_keys = ON")
        self._tables()
        self._seed()
        # 启用 WAL 模式提升并发性能
        c.execute("PRAGMA journal_mode=WAL")

    @property
    def conn(self):
        """每个线程独立的数据库连接"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self._file)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA foreign_keys = ON")
            self._local.conn.execute("PRAGMA busy_timeout=5000")
        return self._local.conn

    def execute(self, sql, params=()):
        """数据库查询"""
        return self.conn.execute(sql, params)

    def commit(self):
        """提交事务"""
        self.conn.commit()

    def _tables(self):
        self.conn.executescript("""
            CREATE TABLE user (uid INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL, nickname TEXT NOT NULL, email TEXT, phone TEXT, avatar TEXT,
                credit_score INTEGER DEFAULT 100, role TEXT DEFAULT 'member', is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, is_deleted INTEGER DEFAULT 0);
            CREATE TABLE course (cid INTEGER PRIMARY KEY AUTOINCREMENT, cname TEXT NOT NULL,
                teacher TEXT, semester TEXT NOT NULL, description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, is_deleted INTEGER DEFAULT 0);
            CREATE TABLE skill (sid INTEGER PRIMARY KEY AUTOINCREMENT, sname TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE user_skill (uid INTEGER, sid INTEGER, proficiency INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(uid, sid),
                FOREIGN KEY(uid) REFERENCES user(uid) ON DELETE CASCADE,
                FOREIGN KEY(sid) REFERENCES skill(sid) ON DELETE CASCADE);
            CREATE TABLE project (pid INTEGER PRIMARY KEY AUTOINCREMENT, cid INTEGER NOT NULL,
                uid INTEGER NOT NULL, pname TEXT NOT NULL, description TEXT,
                max_members INTEGER DEFAULT 4, status INTEGER DEFAULT 0, deadline TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, is_deleted INTEGER DEFAULT 0,
                FOREIGN KEY(cid) REFERENCES course(cid) ON DELETE CASCADE,
                FOREIGN KEY(uid) REFERENCES user(uid) ON DELETE CASCADE);
            CREATE TABLE project_skill (pid INTEGER, sid INTEGER, required_count INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(pid, sid),
                FOREIGN KEY(pid) REFERENCES project(pid) ON DELETE CASCADE,
                FOREIGN KEY(sid) REFERENCES skill(sid) ON DELETE CASCADE);
            CREATE TABLE application (aid INTEGER PRIMARY KEY AUTOINCREMENT,
                pid INTEGER NOT NULL, uid INTEGER NOT NULL, message TEXT, status INTEGER DEFAULT 0,
                apply_time DATETIME DEFAULT CURRENT_TIMESTAMP, handle_time DATETIME,
                FOREIGN KEY(pid) REFERENCES project(pid) ON DELETE CASCADE,
                FOREIGN KEY(uid) REFERENCES user(uid) ON DELETE CASCADE);
            CREATE TABLE member (mid INTEGER PRIMARY KEY AUTOINCREMENT,
                pid INTEGER NOT NULL, uid INTEGER NOT NULL, role TEXT DEFAULT 'member',
                join_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(pid) REFERENCES project(pid) ON DELETE CASCADE,
                FOREIGN KEY(uid) REFERENCES user(uid) ON DELETE CASCADE, UNIQUE(pid, uid));
            CREATE TABLE progress (prid INTEGER PRIMARY KEY AUTOINCREMENT,
                pid INTEGER NOT NULL, title TEXT NOT NULL, description TEXT, status INTEGER DEFAULT 0,
                deadline TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(pid) REFERENCES project(pid) ON DELETE CASCADE);
            CREATE TABLE sessions (token TEXT PRIMARY KEY, uid INTEGER, username TEXT, role TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
            -- ★ 性能索引：加速过滤、排序和关联查询
            CREATE INDEX idx_project_status_del ON project(status, is_deleted);
            CREATE INDEX idx_project_cid ON project(cid);
            CREATE INDEX idx_project_created ON project(created_at DESC);
            CREATE INDEX idx_application_pid_uid ON application(pid, uid);
            CREATE INDEX idx_application_pid_status ON application(pid, status);
            CREATE INDEX idx_member_pid ON member(pid);
            CREATE INDEX idx_progress_pid_deadline ON progress(pid, deadline);
            CREATE INDEX idx_sessions_token ON sessions(token);
        """)

    def _seed(self):
        # Skills (10个常用技能)
        for s in [('前端开发','技术'),('后端开发','技术'),('数据库设计','技术'),('UI设计','设计'),
            ('测试调试','技术'),('文档编写','管理'),('答辩演讲','管理'),('算法实现','技术'),
            ('项目管理','管理'),('数据分析','技术')]:
            self.conn.execute("INSERT INTO skill(sname,category) VALUES(?,?)", s)
        # Courses (4门课程)
        for c in [('软件工程课程设计','张教授','2025-2026-2','软件工程实践课程，要求学生组队完成一个完整的软件项目'),
            ('数据库系统原理','李教授','2025-2026-2','数据库理论课程，配套课程设计需完成一个数据库应用系统'),
            ('人工智能导论','王教授','2025-2026-2','人工智能基础课程，含团队大作业和期末答辩'),
            ('移动应用开发','赵教授','2025-2026-2','跨平台移动应用开发实践，要求交付可上架的应用产品')]:
            self.conn.execute("INSERT INTO course(cname,teacher,semester,description) VALUES(?,?,?,?)", c)
        # Users (1管理员 + 15普通用户)
        users = [('admin001','系统管理员','admin@t.com','13800000000','admin',100,1),
            ('2024001','张三','zs@qq.com','13800001111','member',98,1),
            ('2024002','李四','ls@qq.com','13800002222','member',95,1),
            ('2024003','王五','ww@qq.com','13800003333','member',100,1),
            ('2024004','赵六','zl@qq.com','13800004444','member',85,1),
            ('2024005','孙七','sq@qq.com','13800005555','member',92,1),
            ('2024006','周八','zb@qq.com','13800006666','member',78,1),
            ('2024007','吴九','wj@qq.com','13800007777','member',100,1),
            ('2024008','郑十','zs2@qq.com','13800008888','member',90,1),
            ('2024009','陈一','cy@qq.com','13800009999','member',88,0),
            ('2024010','刘二','le@qq.com','13800010000','member',95,1),
            ('2024011','黄三','hs@qq.com','13800011111','member',70,1),
            ('2024012','杨四','ys@qq.com','13800012222','member',99,1),
            ('2024013','马五','mw@qq.com','13800013333','member',88,1),
            ('2024014','林六','ll@qq.com','13800014444','member',92,1),
            ('2024015','何七','hq@qq.com','13800015555','member',85,1)]
        for i,(un,nn,em,ph,ro,cs,ia) in enumerate(users, 1):
            self.conn.execute("INSERT INTO user(uid,username,password,nickname,email,phone,role,credit_score,is_active) VALUES(?,?,?,?,?,?,?,?,?)",
                (i, un, hp(un, '123456'), nn, em, ph, ro, cs, ia))
        # User skills（每个用户2~4项技能，突出不同特长）
        us = [(2,1,5),(2,2,4),(2,3,3),(3,4,5),(3,1,3),(4,2,4),(4,5,4),(4,7,5),
            (5,1,4),(5,4,3),(5,6,5),(5,7,4),(6,2,5),(6,3,4),(6,8,3),(6,9,5),
            (7,5,5),(7,6,4),(7,9,3),(8,1,5),(8,2,4),(8,3,3),(8,4,4),(8,5,3),
            (9,2,3),(9,8,5),(9,10,4),(10,1,3),(10,4,4),(11,6,5),(11,7,5),(11,9,4),
            (12,2,3),(12,5,3),(13,1,4),(13,3,3),(13,10,5),
            (14,1,4),(14,5,5),(14,6,3),  # 马五：前端+测试+文档
            (15,2,5),(15,3,4),(15,8,4),  # 林六：后端+数据库+算法
            (16,4,4),(16,7,5),(16,9,4)]  # 何七：UI+答辩+项目管理
        for uid,sid,pf in us: self.conn.execute("INSERT INTO user_skill(uid,sid,proficiency) VALUES(?,?,?)", (uid,sid,pf))
        # Projects（12个，覆盖4种状态：0招募中×6 / 1已满×2 / 2进行中×2 / 3已结束×2）
        for p in [(1,2,'智慧校园小程序','开发面向全校师生的智慧校园服务小程序，包含课表查询、成绩管理、校园导航等功能',4,0,'2025-07-01'),
            (1,5,'在线代码评测平台','搭建支持多种编程语言的在线代码提交与自动评测系统，包含题库管理和分数统计',5,0,'2025-07-10'),
            (2,6,'数据库课程设计管理系统','实现学生选题、教师审核、进度跟踪、成绩管理的数据库课程设计全流程平台',4,0,'2025-07-05'),
            (3,4,'AI垃圾分类识别','基于图像识别的智能垃圾分类系统，包含模型训练、Web部署和移动端适配',5,2,'2025-06-20'),
            (1,7,'校园二手交易平台','为校内学生提供便捷的二手物品发布、搜索、交易确认功能',3,3,'2025-06-01'),
            # ★ 新增7个项目
            (2,13,'在线考试系统','自动组卷、在线答题、自动评分、成绩分析的一体化在线考试平台',4,1,'2025-06-25'),
            (1,11,'校园活动管理平台','社团活动发布、报名审核、扫码签到、数据统计的全流程管理平台',4,1,'2025-06-28'),
            (3,8,'机器学习模型可视化','训练过程可视化、模型结构展示、推理结果可解释性分析工具',5,0,'2025-07-15'),
            (2,9,'学生成绩分析系统','多维度成绩统计、学期趋势分析、学业预警推送功能',4,0,'2025-07-08'),
            (3,12,'智能课表推荐','基于协同过滤和课程标签的个性化课表推荐引擎',4,2,'2025-06-30'),
            (1,3,'图书馆座位预约','实时座位状态查看、分时段预约、扫码签到签退系统',4,3,'2025-05-30'),
            (4,2,'校园导航App','校园建筑搜索、路径规划、AR实景导航的跨平台移动应用',5,0,'2025-07-20')]:
            self.conn.execute("INSERT INTO project(cid,uid,pname,description,max_members,status,deadline) VALUES(?,?,?,?,?,?,?)", p)
        # Project skills
        for ps in [(1,1,1),(1,2,1),(1,4,1),(2,2,2),(2,1,1),(2,8,1),(2,5,1),(3,3,1),(3,1,1),(3,2,1),(3,6,1),
            (4,8,2),(4,2,1),(4,1,1),(4,10,1),(5,1,1),(5,2,1),
            (6,1,1),(6,2,1),(6,3,1),(6,5,1),
            (7,1,1),(7,2,1),(7,4,1),(7,6,1),
            (8,1,1),(8,2,1),(8,8,1),(8,10,1),
            (9,3,1),(9,2,1),(9,10,1),
            (10,2,1),(10,8,1),(10,10,1),(10,1,1),
            (11,1,1),(11,2,1),(11,3,1),(11,6,1),
            (12,1,2),(12,2,1),(12,4,1),(12,6,1)]:
            self.conn.execute("INSERT INTO project_skill(pid,sid,required_count) VALUES(?,?,?)", ps)
        # Members（组长+组员关系）
        for m in [(1,2,'leader'),(1,3,'member'),(2,5,'leader'),(3,6,'leader'),(3,8,'member'),
            (4,4,'leader'),(4,2,'member'),(4,11,'member'),(5,7,'leader'),(5,5,'member'),(5,9,'member'),
            (6,13,'leader'),(6,11,'member'),(6,14,'member'),(6,16,'member'),
            (7,11,'leader'),(7,9,'member'),(7,15,'member'),(7,16,'member'),
            (8,8,'leader'),
            (9,9,'leader'),
            (10,12,'leader'),(10,16,'member'),
            (11,3,'leader'),(11,7,'member'),(11,14,'member'),(11,15,'member'),
            (12,2,'leader')]:
            self.conn.execute("INSERT INTO member(pid,uid,role) VALUES(?,?,?)", m)
        # Applications（覆盖 待处理/已接受/已拒绝 三种状态）
        for a in [(1,3,'擅长UI设计和前端开发，希望能加入项目！',1,'2025-06-02 09:00','2025-06-03 10:00'),
            (1,5,'我有前端开发和文档编写经验，需要组队完成课程设计',0,'2025-06-10 14:00',None),
            (1,6,'我了解小程序开发，后端能力强',2,'2025-06-05 11:00','2025-06-06 09:00'),
            (2,4,'我有丰富的后端开发经验，做过类似的评测系统',0,'2025-06-11 08:00',None),
            (2,8,'全栈工程师，可以负责前端和后端联调',0,'2025-06-11 09:30',None),
            (3,9,'我的数据库设计能力很强，算法也是优势',0,'2025-06-09 16:00',None),
            (3,10,'希望加入学习，虽然经验不多但愿意努力',0,'2025-06-10 10:00',None),
            (4,11,'答辩演讲和文档编写能力突出',1,'2025-06-01 15:00','2025-06-02 10:00'),
            (1,13,'前端开发4星，做过类似项目',0,'2025-06-12 08:00',None),
            (6,14,'测试和文档经验丰富，曾参与在线教育平台开发',1,'2025-06-01 10:00','2025-06-02 14:00'),
            (6,16,'UI设计4星，答辩能力强，能承担项目展示环节',1,'2025-06-03 09:00','2025-06-04 11:00'),
            (7,9,'后端和算法能力强，有管理系统开发经验',1,'2025-06-01 08:00','2025-06-03 16:00'),
            (7,15,'数据库设计经验丰富，参加过数学建模竞赛',1,'2025-06-02 10:00','2025-06-04 09:00'),
            (7,16,'UI设计和答辩专长，曾获校级优秀展示奖',1,'2025-06-03 11:00','2025-06-05 15:00'),
            (7,7,'测试经验丰富，熟悉自动化测试流程',2,'2025-06-06 14:00','2025-06-07 10:00'),
            (8,15,'算法能力强，熟练使用TensorFlow和PyTorch',0,'2025-06-12 09:00',None),
            (8,14,'前端可视化经验丰富，精通D3.js和ECharts',0,'2025-06-13 15:00',None),
            (9,12,'后端开发3星，想通过项目提升技术水平',0,'2025-06-11 10:00',None),
            (10,16,'答辩和UI设计专长，擅长PPT制作和项目演示',1,'2025-05-20 14:00','2025-05-22 10:00'),
            (11,7,'测试和项目管理经验丰富，想锻炼团队协作能力',1,'2025-04-01 09:00','2025-04-02 15:00'),
            (11,14,'前端测试经验丰富，熟悉Jest和Selenium',1,'2025-04-03 10:00','2025-04-04 11:00'),
            (11,15,'数据库设计和后端开发基础扎实',1,'2025-04-05 14:00','2025-04-06 10:00'),
            (11,12,'后端开发基础，想参与实际项目积累经验',2,'2025-04-07 14:00','2025-04-08 09:00'),
            (12,16,'UI设计4星加答辩5星，适合做展示汇报',0,'2025-06-13 10:00',None),
            (12,6,'算法和项目管理双修，项目经验全面',0,'2025-06-14 16:00',None)]:
            self.conn.execute("INSERT INTO application(pid,uid,message,status,apply_time,handle_time) VALUES(?,?,?,?,?,?)", a)
        # Progress（每个项目2~5个进度节点，覆盖完成/未完成状态）
        for pg in [(1,'需求分析完成','完成系统需求文档并通过老师审核',1,'2025-06-10'),
            (1,'数据库设计','完成ER图绘制和建表脚本编写',0,'2025-06-18'),
            (1,'前端页面开发','完成所有静态页面的HTML+CSS开发',0,'2025-06-25'),
            (4,'数据集收集','收集并标注不少于5000张垃圾分类图片',1,'2025-05-20'),
            (4,'模型训练','使用CNN训练分类模型，准确率达到90%以上',1,'2025-06-01'),
            (4,'Web端部署','将模型部署到Web端，支持图片上传识别',0,'2025-06-15'),
            (4,'移动端适配','适配移动端页面，优化响应式布局',0,'2025-06-25'),
            (2,'系统架构设计','完成在线评测引擎架构设计文档',0,'2025-06-15'),
            (6,'需求分析与评审','在线考试系统需求文档，含自动组卷算法设计',1,'2025-05-20'),
            (6,'数据库设计','题库表、试卷表、答卷表、成绩表的完整设计',1,'2025-06-01'),
            (6,'后端核心开发','组卷算法引擎、自动评分逻辑、防作弊机制',0,'2025-06-15'),
            (6,'前端双端开发','考生答题端和管理员后台双端页面开发',0,'2025-06-22'),
            (7,'原型设计','活动管理平台Axure原型，已通过老师审核',1,'2025-06-05'),
            (7,'前端框架搭建','管理端Dashboard页面框架搭建完成',1,'2025-06-12'),
            (7,'后端接口开发','活动CRUD、报名管理、签到系统接口开发',0,'2025-06-20'),
            (7,'数据统计模块','活动参与数据可视化统计模块',0,'2025-06-26'),
            (8,'技术选型','确定前端React+D3.js，后端Flask+TensorFlow Serving',1,'2025-06-10'),
            (8,'数据接口设计','模型训练日志和评估指标的JSON接口规范',0,'2025-06-25'),
            (9,'数据模型设计','多维度成绩统计模型与学业预警规则设计',0,'2025-06-20'),
            (10,'推荐算法设计','基于协同过滤和课程标签的混合推荐算法',1,'2025-05-25'),
            (10,'数据采集与清洗','爬取历年课程数据并清洗、特征工程处理',1,'2025-06-05'),
            (10,'推荐API开发','RESTful推荐接口：课表生成、课程评分预测',0,'2025-06-18'),
            (10,'前端可视化','课表时间轴展示、推荐理由可解释性面板',0,'2025-06-28'),
            (11,'需求分析','座位预约核心需求：时段管理、黑名单机制',1,'2025-04-10'),
            (11,'数据库设计','座位表、预约表、签到表、黑名单表设计',1,'2025-04-20'),
            (11,'后端开发','预约逻辑引擎：时段冲突检测、自动释放、违约记录',1,'2025-05-01'),
            (11,'前端开发','图书馆座位地图、预约日历、扫码签到页面',1,'2025-05-15'),
            (11,'测试与部署','全系统集成测试、压力测试、上线部署',1,'2025-05-28'),
            (12,'需求调研','发放200份问卷，收集校园导航核心需求',1,'2025-06-05'),
            (12,'地图数据采集','校园建筑坐标、道路网络、POI标注数据采集',0,'2025-06-20')]:
            self.conn.execute("INSERT INTO progress(pid,title,description,status,deadline) VALUES(?,?,?,?,?)", pg)
        self.conn.commit()

    def d(self, r): return dict(r) if r else None
    def ds(self, rs): return [dict(r) for r in rs]

db = DB()

def get_uid(headers):
    auth = headers.get('Authorization','')
    if auth.startswith('Bearer '):
        row = db.execute("SELECT uid,role FROM sessions WHERE token=?", (auth[7:],)).fetchone()
        return (row['uid'], row['role']) if row else (None, None)
    return (None, None)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kw):
        super().__init__(*args, directory=ROOT, **kw)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        super().end_headers()

    def do_OPTIONS(self): self.send_response(204); self.end_headers()

    def _json(self, code, msg='', data=None):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps({'code':code,'message':msg,'data':data}, ensure_ascii=False).encode())

    def _body(self):
        try: n = int(self.headers.get('Content-Length',0)); return json.loads(self.rfile.read(n)) if n else {}
        except: return {}

    def do_GET(self): self._route()
    def do_POST(self): self._route()
    def do_PUT(self): self._route()
    def do_DELETE(self): self._route()

    def _route(self):
        path = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)

        # Static files
        if not path.startswith('/api/'):
            # Redirect root and /frontend to /frontend/index.html so relative resources load correctly
            if path in ('/', ''):
                self.send_response(302)
                self.send_header('Location', '/frontend/index.html')
                self.end_headers()
                return
            if path.rstrip('/') == '/frontend':
                self.send_response(302)
                self.send_header('Location', '/frontend/index.html')
                self.end_headers()
                return
            # Prevent directory traversal
            clean = os.path.normpath(path.lstrip('/'))
            if clean.startswith('..') or clean.startswith('~'):
                self._json(403, '禁止访问')
                return
            fp = os.path.join(ROOT, clean)
            fp = os.path.normpath(fp)
            if not fp.startswith(ROOT):
                self._json(403, '禁止访问')
                return
            if os.path.isfile(fp):
                self.send_response(200)
                ct = {'html':'text/html','css':'text/css','js':'application/javascript'}
                ext = fp.rsplit('.',1)[-1]
                self.send_header('Content-Type', f'{ct.get(ext,"text/plain")}; charset=utf-8')
                # ★ 优化：第三方库长缓存，业务代码短缓存
                if '/lib/' in fp.replace('\\', '/'):
                    self.send_header('Cache-Control', 'public, max-age=604800, immutable')
                else:
                    self.send_header('Cache-Control', 'no-cache')
                fs = os.path.getsize(fp)
                self.send_header('Content-Length', str(fs))
                self.end_headers()
                with open(fp,'rb') as f: self.wfile.write(f.read())
            else: self._json(404, '文件不存在')
            return

        # Auth check for API
        uid, role = get_uid(self.headers)
        # Exact-match public routes (no auth required for any method)
        public_exact = {'/api/user/register', '/api/user/login', '/api/courses'}
        # GET-only public routes (POST/PUT/DELETE still require auth)
        public_get = {'/api/projects'}
        is_public = path in public_exact or bool(re.match(r'^/api/projects/\d+$', path))
        is_public = is_public or (path in public_get and self.command == 'GET')
        if not is_public and not uid:
            self._json(401, '请先登录'); return

        # Routes
        rmap = {
            r'^/api/user/register$': self._register,
            r'^/api/user/login$': self._login,
            r'^/api/user/profile$': self._profile,
            r'^/api/user/skills$': self._skills,
            r'^/api/courses$': self._courses,
            r'^/api/projects$': self._projects,
            r'^/api/projects/(\d+)$': self._proj_detail,
            r'^/api/projects/(\d+)/apply$': self._apply,
            r'^/api/projects/(\d+)/applications$': self._apps,
            r'^/api/projects/(\d+)/progress$': self._progress,
            r'^/api/applications/(\d+)/handle$': self._handle,
            r'^/api/recommendations$': self._recommend,
            # ★ 管理员接口
            r'^/api/admin/users$': self._admin_users,
            r'^/api/admin/stats$': self._admin_stats,
            r'^/api/admin/projects$': self._admin_projects,
        }
        for pat, fn in rmap.items():
            m = re.match(pat, path)
            if m:
                try:
                    fn(uid, role, int(m.group(1)) if m.lastindex else None, qs)
                except Exception as ex:
                    print(f"[API ERROR] {path}: {ex}")
                    self._json(500, '服务器内部错误，请稍后重试')
                return
        self._json(404, '接口不存在')

    # ====== USER APIS ======
    def _register(self, uid, role, _, __):
        if self.command != 'POST': return self._json(405)
        b = self._body()
        un = b.get('username','').strip(); pw = b.get('password',''); nn = b.get('nickname','').strip()
        if not un or not pw or not nn: return self._json(400, '必填字段不能为空')
        if len(pw) < 6 or len(pw) > 20: return self._json(400, '密码长度6-20位')
        if db.execute("SELECT 1 FROM user WHERE username=? AND is_deleted=0", (un,)).fetchone():
            return self._json(400, '用户名已存在')
        cur = db.execute("INSERT INTO user(username,password,nickname,email,phone,role,is_active) VALUES(?,?,?,?,?,?,?)",
            (un, hp(un,pw), nn, b.get('email'), b.get('phone'), 'member', 1))
        db.commit()
        self._json(200, '注册成功', {'uid': cur.lastrowid, 'username': un, 'nickname': nn})

    def _login(self, uid, role, _, __):
        if self.command != 'POST': return self._json(405)
        b = self._body()
        u = db.d(db.execute("SELECT * FROM user WHERE username=? AND password=? AND is_deleted=0",
            (b.get('username','').strip(), hp(b.get('username','').strip(), b.get('password','')))).fetchone())
        if not u: return self._json(400, '用户名或密码错误')
        if not u['is_active']: return self._json(400, '账号已被禁用，请联系管理员')
        token = hashlib.md5(f"{u['uid']}{time.time()}".encode()).hexdigest()
        db.execute("INSERT INTO sessions(token,uid,username,role) VALUES(?,?,?,?)", (token, u['uid'], u['username'], u['role']))
        db.commit()
        self._json(200, '登录成功', {'uid': u['uid'], 'username': u['username'], 'nickname': u['nickname'],
            'email': u['email'], 'phone': u['phone'], 'avatar': u['avatar'],
            'credit_score': u['credit_score'], 'role': u['role'], 'is_active': u['is_active'],
            'created_at': u['created_at'], 'token': token})

    def _profile(self, uid, role, _, __):
        if self.command == 'GET':
            u = db.d(db.execute("SELECT uid,username,nickname,email,phone,avatar,credit_score,role,is_active,created_at FROM user WHERE uid=? AND is_deleted=0", (uid,)).fetchone())
            if not u: return self._json(404)
            u['skills'] = db.ds(db.execute("SELECT s.sid,s.sname,s.category,us.proficiency FROM user_skill us JOIN skill s ON us.sid=s.sid WHERE us.uid=?", (uid,)))
            u['projects'] = db.ds(db.execute("SELECT m.pid,m.role,m.join_time,p.pname,p.status FROM member m JOIN project p ON m.pid=p.pid WHERE m.uid=?", (uid,)))
            self._json(200, 'success', u)
        elif self.command == 'PUT':
            b = self._body(); fs = []; vs = []
            for f in ['nickname','email','phone']:
                if f in b: fs.append(f'{f}=?'); vs.append(b[f])
            if not fs: return self._json(400, '无可更新的字段')
            vs.append(uid)
            db.execute(f"UPDATE user SET {','.join(fs)} WHERE uid=?", vs)
            db.commit()
            self._json(200, '资料更新成功')
        else: self._json(405)

    def _skills(self, uid, role, _, __):
        if self.command == 'GET':
            self._json(200, 'success', db.ds(db.execute("SELECT s.sid,s.sname,s.category,us.proficiency FROM user_skill us JOIN skill s ON us.sid=s.sid WHERE us.uid=?", (uid,))))
        elif self.command == 'POST':
            b = self._body(); sid = b.get('sid')
            if not sid: return self._json(400, 'sid不能为空')
            if not db.execute("SELECT 1 FROM skill WHERE sid=?", (sid,)).fetchone(): return self._json(400, '技能标签不存在')
            if db.execute("SELECT 1 FROM user_skill WHERE uid=? AND sid=?", (uid,sid)).fetchone(): return self._json(400, '您已拥有该技能')
            db.execute("INSERT INTO user_skill(uid,sid,proficiency) VALUES(?,?,?)", (uid,sid,max(1,min(5,int(b.get('proficiency',1))))))
            db.commit(); self._json(200, '技能添加成功')
        elif self.command == 'DELETE':
            b = self._body(); sid = b.get('sid')
            if not sid: return self._json(400, 'sid不能为空')
            if not db.execute("SELECT 1 FROM user_skill WHERE uid=? AND sid=?", (uid,sid)).fetchone(): return self._json(400, '您尚未拥有该技能')
            db.execute("DELETE FROM user_skill WHERE uid=? AND sid=?", (uid,sid))
            db.commit(); self._json(200, '技能删除成功')
        else: self._json(405)

    # ====== COURSE + PROJECT APIS ======
    def _courses(self, uid, role, _, qs):
        sem = qs.get('semester',[None])[0]
        sql = "SELECT c.*,(SELECT COUNT(*) FROM project p WHERE p.cid=c.cid AND p.is_deleted=0) AS project_count FROM course c WHERE c.is_deleted=0"
        if sem: sql += " AND c.semester=?"; rows = db.ds(db.execute(sql, (sem,)))
        else: rows = db.ds(db.execute(sql))
        self._json(200, 'success', rows)

    def _projects(self, uid, role, _, qs):
        if self.command == 'GET':
            cid = qs.get('cid',[None])[0]; st = qs.get('status',[None])[0]; kw = qs.get('keyword',[None])[0]
            pg = max(1,int(qs.get('page',[1])[0])); ps = max(1,min(50,int(qs.get('page_size',[10])[0])))
            w = ["p.is_deleted=0"]; v = []
            if cid: w.append("p.cid=?"); v.append(int(cid))
            if st is not None and st!='': w.append("p.status=?"); v.append(int(st))
            if kw: w.append("p.pname LIKE ?"); v.append(f'%{kw}%')
            ws = " AND ".join(w)
            total = db.execute(f"SELECT COUNT(*) AS cnt FROM project p WHERE {ws}", v).fetchone()['cnt']
            rows = db.ds(db.execute(f"""
                SELECT p.pid,p.pname,p.description,p.max_members,p.status,p.deadline,p.created_at,
                    (SELECT COUNT(*) FROM member m WHERE m.pid=p.pid) AS current_members,
                    u.uid AS creator_uid,u.nickname AS creator_nickname,c.cid AS course_cid,c.cname AS course_cname
                FROM project p JOIN user u ON p.uid=u.uid JOIN course c ON p.cid=c.cid
                WHERE {ws} ORDER BY p.created_at DESC LIMIT ? OFFSET ?
            """, v+[ps,(pg-1)*ps]))
            # ★ 优化：批量查询所有项目的技能标签（1次查询替代N次）
            if rows:
                pids = tuple(r['pid'] for r in rows)
                placeholders = ','.join(['?'] * len(pids))
                skill_rows = db.ds(db.execute(
                    f"SELECT ps.pid, s.sname FROM project_skill ps JOIN skill s ON ps.sid=s.sid WHERE ps.pid IN ({placeholders})", pids))
                skill_map = {}
                for sr in skill_rows:
                    skill_map.setdefault(sr['pid'], []).append(sr['sname'])
                for r in rows:
                    r['skills'] = skill_map.get(r['pid'], [])
            self._json(200, 'success', {'list':rows,'total':total,'page':pg,'page_size':ps})
        elif self.command == 'POST':
            b = self._body(); cid = b.get('cid'); pname = (b.get('pname') or '').strip(); sids = b.get('skill_ids',[])
            if not cid or not pname or not isinstance(sids,list) or len(sids)==0: return self._json(400, '必填字段缺失')
            if not db.execute("SELECT 1 FROM course WHERE cid=?", (cid,)).fetchone(): return self._json(400, '课程不存在')
            cur = db.execute("INSERT INTO project(cid,uid,pname,description,max_members,deadline) VALUES(?,?,?,?,?,?)",
                (cid, uid, pname, b.get('description'), b.get('max_members',4), b.get('deadline')))
            pid = cur.lastrowid
            for s in sids: db.execute("INSERT INTO project_skill(pid,sid) VALUES(?,?)", (pid,s))
            db.execute("INSERT INTO member(pid,uid,role) VALUES(?,?,?)", (pid, uid, 'leader'))
            db.commit()
            self._json(200, '项目发布成功', {'pid': pid})
        else: self._json(405)

    def _proj_detail(self, uid, role, pid, _):
        if self.command != 'GET': return self._json(405)
        p = db.d(db.execute("""SELECT p.*,c.cname AS course_name,c.teacher AS course_teacher,
            u.nickname AS creator_nickname FROM project p JOIN course c ON p.cid=c.cid JOIN user u ON p.uid=u.uid
            WHERE p.pid=? AND p.is_deleted=0""", (pid,)).fetchone())
        if not p: return self._json(404, '项目不存在')
        # ★ 优化：合并required_skills和members查询，从5次→3次查询
        p['required_skills'] = db.ds(db.execute("SELECT ps.sid,s.sname,s.category,ps.required_count FROM project_skill ps JOIN skill s ON ps.sid=s.sid WHERE ps.pid=?", (pid,)))
        p['members'] = db.ds(db.execute("SELECT m.uid,u.nickname,u.avatar,m.role,m.join_time FROM member m JOIN user u ON m.uid=u.uid WHERE m.pid=?", (pid,)))
        p['current_members'] = len(p['members'])
        p['status_text'] = {0:'招募中',1:'已满',2:'进行中',3:'已结束'}.get(p['status'],'')
        p['course'] = {'cid':p['cid'],'cname':p['course_name'],'teacher':p['course_teacher']}
        p['creator'] = {'uid':p['uid'],'nickname':p['creator_nickname']}
        # ★ 复用已查询的required_skills数据，不再单独查skills
        p['skills'] = [x['sname'] for x in p['required_skills']]
        if uid:
            a = db.execute("SELECT status FROM application WHERE pid=? AND uid=? ORDER BY aid DESC LIMIT 1", (pid,uid)).fetchone()
            p['my_application_status'] = a['status'] if a else None
        else: p['my_application_status'] = None
        self._json(200, 'success', p)

    def _apply(self, uid, role, pid, _):
        if self.command != 'POST': return self._json(405)
        p = db.d(db.execute("SELECT * FROM project WHERE pid=? AND is_deleted=0", (pid,)).fetchone())
        if not p: return self._json(400, '项目不存在')
        if p['status'] != 0: return self._json(400, '项目已结束招募')
        if p['uid'] == uid: return self._json(400, '不可申请自己创建的项目')
        if db.execute("SELECT 1 FROM member WHERE pid=? AND uid=?", (pid,uid)).fetchone(): return self._json(400, '您已是成员')
        if db.execute("SELECT 1 FROM application WHERE pid=? AND uid=? AND status=0", (pid,uid)).fetchone(): return self._json(400, '您已申请过')
        b = self._body()
        cur = db.execute("INSERT INTO application(pid,uid,message) VALUES(?,?,?)", (pid, uid, b.get('message')))
        db.commit()
        self._json(200, '申请已提交', {'aid': cur.lastrowid})

    def _apps(self, uid, role, pid, _):
        if self.command != 'GET': return self._json(405)
        p = db.execute("SELECT uid FROM project WHERE pid=?", (pid,)).fetchone()
        if not p or p['uid'] != uid: return self._json(403, '仅组长可查看')
        apps = db.ds(db.execute("SELECT a.aid,a.uid,u.nickname,u.avatar,a.message,a.status,a.apply_time FROM application a JOIN user u ON a.uid=u.uid WHERE a.pid=? AND a.status=0 ORDER BY a.apply_time DESC", (pid,)))
        for a in apps: a['skills'] = db.ds(db.execute("SELECT s.sid,s.sname,us.proficiency FROM user_skill us JOIN skill s ON us.sid=s.sid WHERE us.uid=?", (a['uid'],)))
        self._json(200, 'success', apps)

    def _handle(self, uid, role, aid, _):
        if self.command != 'PUT': return self._json(405)
        a = db.d(db.execute("SELECT a.*,p.uid AS leader_uid,p.max_members,(SELECT COUNT(*) FROM member m WHERE m.pid=a.pid) AS cur FROM application a JOIN project p ON a.pid=p.pid WHERE a.aid=?", (aid,)).fetchone())
        if not a: return self._json(400, '申请不存在')
        if a['leader_uid'] != uid: return self._json(403, '仅组长可审批')
        if a['status'] != 0: return self._json(400, '该申请已处理')
        b = self._body(); act = b.get('action','')
        if act not in ('accept','reject'): return self._json(400, 'action必须为accept或reject')
        if act == 'accept':
            if a['cur'] >= a['max_members']: return self._json(400, '项目已满员')
            db.execute("UPDATE application SET status=1,handle_time=CURRENT_TIMESTAMP WHERE aid=?", (aid,))
            db.execute("INSERT INTO member(pid,uid,role) VALUES(?,?,?)", (a['pid'], a['uid'], 'member'))
            chg = False
            if a['cur']+1 >= a['max_members']:
                db.execute("UPDATE project SET status=1 WHERE pid=? AND status=0", (a['pid'],)); chg = True
            db.commit(); self._json(200, '已通过', {'project_status_changed': chg})
        else:
            db.execute("UPDATE application SET status=2,handle_time=CURRENT_TIMESTAMP WHERE aid=?", (aid,))
            db.commit(); self._json(200, '已拒绝')

    def _progress(self, uid, role, pid, _):
        if self.command == 'GET':
            self._json(200, 'success', db.ds(db.execute("SELECT * FROM progress WHERE pid=? ORDER BY deadline,created_at", (pid,))))
        elif self.command == 'POST':
            p = db.execute("SELECT uid FROM project WHERE pid=?", (pid,)).fetchone()
            if not p or p['uid'] != uid: return self._json(403, '仅组长可操作')
            b = self._body(); t = (b.get('title') or '').strip()
            if not t: return self._json(400, 'title不能为空')
            cur = db.execute("INSERT INTO progress(pid,title,description,deadline) VALUES(?,?,?,?)", (pid,t,b.get('description'),b.get('deadline')))
            db.commit(); self._json(200, '新增成功', {'prid': cur.lastrowid})
        elif self.command == 'PUT':
            p = db.execute("SELECT uid FROM project WHERE pid=?", (pid,)).fetchone()
            if not p or p['uid'] != uid: return self._json(403, '仅组长可操作')
            b = self._body()
            if not b.get('prid') or b.get('status') is None: return self._json(400, 'prid和status必填')
            if not db.execute("SELECT 1 FROM progress WHERE prid=? AND pid=?", (b['prid'],pid)).fetchone(): return self._json(400, '节点不存在')
            db.execute("UPDATE progress SET status=? WHERE prid=?", (b['status'],b['prid']))
            db.commit(); self._json(200, '状态更新成功')
        else: self._json(405)

    def _recommend(self, uid, role, _, qs):
        if self.command != 'GET': return self._json(405)
        cid = qs.get('cid',[None])[0]
        sql = """SELECT p.pid,p.pname,p.description,p.max_members,p.deadline,p.created_at,
            (SELECT COUNT(*) FROM member m WHERE m.pid=p.pid) AS cur,
            c.cid AS course_cid,c.cname AS course_cname,u.uid AS creator_uid,u.nickname AS creator_nickname
            FROM project p JOIN course c ON p.cid=c.cid JOIN user u ON p.uid=u.uid
            WHERE p.status=0 AND p.is_deleted=0 AND p.pid NOT IN (SELECT pid FROM member WHERE uid=?)
            AND p.pid NOT IN (SELECT pid FROM application WHERE uid=? AND status=0)"""
        v = [uid, uid]
        if cid: sql += " AND p.cid=?"; v.append(int(cid))
        rows = db.ds(db.execute(sql, v))
        usk = set(r['sid'] for r in db.execute("SELECT sid FROM user_skill WHERE uid=?", (uid,)))
        res = []
        # ★ 优化：批量获取所有项目技能，替代每个项目单独查询
        if rows:
            all_pids = tuple(p['pid'] for p in rows)
            placeholders = ','.join(['?'] * len(all_pids))
            all_skill_rows = db.ds(db.execute(
                f"SELECT ps.pid, s.sname, s.sid FROM project_skill ps JOIN skill s ON ps.sid=s.sid WHERE ps.pid IN ({placeholders})", all_pids))
            pid_skills_map = {}
            for sr in all_skill_rows:
                pid_skills_map.setdefault(sr['pid'], []).append(sr)
        for p in rows:
            ps = pid_skills_map.get(p['pid'], [])
            all_s = [s['sid'] for s in ps]
            mt = [s for s in ps if s['sid'] in usk]
            um = [s for s in ps if s['sid'] not in usk]
            if not all_s: continue
            rate = round(len(mt)/len(all_s)*100,2)
            if rate == 0: continue
            p['match_rate'] = rate
            p['matched_skills'] = [s['sname'] for s in mt]
            p['unmatched_skills'] = [s['sname'] for s in um]
            p['skills'] = [s['sname'] for s in ps]
            p['course'] = {'cid':p['course_cid'],'cname':p['course_cname']}
            p['creator'] = {'uid':p['creator_uid'],'nickname':p['creator_nickname']}
            p['current_members'] = p.pop('cur'); p['status_text'] = '招募中'
            res.append(p)
        res.sort(key=lambda x: x['match_rate'], reverse=True)
        self._json(200, 'success', res)

    # ====== ★ ADMIN APIS ★ ======
    def _admin_users(self, uid, role, _, qs):
        if role != 'admin': return self._json(403, '仅管理员可访问')

        if self.command == 'GET':
            r = qs.get('role',[None])[0]; ia = qs.get('is_active',[None])[0]; kw = qs.get('keyword',[None])[0]
            pg = max(1,int(qs.get('page',[1])[0])); ps = max(1,min(50,int(qs.get('page_size',[15])[0])))
            w = ["u.is_deleted=0"]; v = []
            if r and r!='': w.append("u.role=?"); v.append(r)
            if ia is not None and ia!='': w.append("u.is_active=?"); v.append(int(ia))
            if kw: w.append("(u.username LIKE ? OR u.nickname LIKE ?)"); v.extend([f'%{kw}%', f'%{kw}%'])
            ws = " AND ".join(w)
            total = db.execute(f"SELECT COUNT(*) AS cnt FROM user u WHERE {ws}", v).fetchone()['cnt']
            rows = db.ds(db.execute(f"""
                SELECT u.uid,u.username,u.nickname,u.email,u.phone,u.role,u.is_active,u.credit_score,u.created_at,
                    (SELECT COUNT(*) FROM user_skill us WHERE us.uid=u.uid) AS skill_count,
                    (SELECT COUNT(*) FROM member m WHERE m.uid=u.uid) AS project_count
                FROM user u WHERE {ws} ORDER BY u.is_active DESC, u.uid ASC LIMIT ? OFFSET ?
            """, v+[ps,(pg-1)*ps]))
            self._json(200, 'success', {'list':rows,'total':total,'page':pg,'page_size':ps})

        elif self.command == 'POST':
            b = self._body(); un = (b.get('username') or '').strip(); pw = b.get('password',''); nn = (b.get('nickname') or '').strip()
            if not un or not pw or not nn: return self._json(400, '必填字段不能为空')
            if len(pw) < 6: return self._json(400, '密码至少6位')
            if db.execute("SELECT 1 FROM user WHERE username=?", (un,)).fetchone(): return self._json(400, '用户名已存在')
            cur = db.execute("INSERT INTO user(username,password,nickname,email,phone,role,credit_score,is_active) VALUES(?,?,?,?,?,?,?,?)",
                (un, hp(un,pw), nn, b.get('email'), b.get('phone'), b.get('role','member'), b.get('credit_score',100), b.get('is_active',1)))
            db.commit()
            self._json(200, '用户创建成功', {'uid': cur.lastrowid})

        elif self.command == 'PUT':
            b = self._body(); tid = b.get('uid')
            if not tid: return self._json(400, 'uid不能为空')
            if tid == uid: return self._json(400, '不可修改自己的信息')
            fs = []; vs = []
            for f in ['nickname','email','phone','role']:
                if f in b: fs.append(f'{f}=?'); vs.append(b[f])
            if 'credit_score' in b: fs.append('credit_score=?'); vs.append(int(b['credit_score']))
            if 'is_active' in b: fs.append('is_active=?'); vs.append(int(b['is_active']))
            if not fs: return self._json(400, '无可更新的字段')
            vs.append(tid)
            db.execute(f"UPDATE user SET {','.join(fs)} WHERE uid=? AND is_deleted=0", vs)
            db.commit(); self._json(200, '更新成功')

        else: self._json(405)

    def _admin_stats(self, uid, role, _, __):
        """获取管理后台统计信息"""
        if role != 'admin': return self._json(403, '仅管理员可访问')
        total_users = db.execute("SELECT COUNT(*) AS c FROM user WHERE is_deleted=0").fetchone()['c']
        active_users = db.execute("SELECT COUNT(*) AS c FROM user WHERE is_deleted=0 AND is_active=1").fetchone()['c']
        admin_count = db.execute("SELECT COUNT(*) AS c FROM user WHERE is_deleted=0 AND role='admin'").fetchone()['c']
        total_projects = db.execute("SELECT COUNT(*) AS c FROM project WHERE is_deleted=0").fetchone()['c']
        recruiting = db.execute("SELECT COUNT(*) AS c FROM project WHERE is_deleted=0 AND status=0").fetchone()['c']
        in_progress = db.execute("SELECT COUNT(*) AS c FROM project WHERE is_deleted=0 AND status=2").fetchone()['c']
        pending_apps = db.execute("SELECT COUNT(*) AS c FROM application WHERE status=0").fetchone()['c']
        self._json(200, 'success', {
            'total_users': total_users, 'active_users': active_users, 'admin_count': admin_count,
            'total_projects': total_projects, 'recruiting': recruiting, 'in_progress': in_progress,
            'pending_applications': pending_apps
        })

    def _admin_projects(self, uid, role, _, qs):
        """管理员项目管理：列表/编辑/删除"""
        if role != 'admin': return self._json(403, '仅管理员可访问')

        if self.command == 'GET':
            cid = qs.get('cid',[None])[0]; st = qs.get('status',[None])[0]; kw = qs.get('keyword',[None])[0]
            pg = max(1,int(qs.get('page',[1])[0])); ps = max(1,min(50,int(qs.get('page_size',[15])[0])))
            w = ["p.is_deleted=0"]; v = []
            if cid: w.append("p.cid=?"); v.append(int(cid))
            if st is not None and st!='': w.append("p.status=?"); v.append(int(st))
            if kw: w.append("p.pname LIKE ?"); v.append(f'%{kw}%')
            ws = " AND ".join(w)
            total = db.execute(f"SELECT COUNT(*) AS cnt FROM project p WHERE {ws}", v).fetchone()['cnt']
            rows = db.ds(db.execute(f"""
                SELECT p.pid,p.pname,p.description,p.max_members,p.status,p.deadline,p.created_at,
                    (SELECT COUNT(*) FROM member m WHERE m.pid=p.pid) AS current_members,
                    u.uid AS creator_uid,u.nickname AS creator_nickname,
                    c.cid AS course_cid,c.cname AS course_cname
                FROM project p JOIN user u ON p.uid=u.uid JOIN course c ON p.cid=c.cid
                WHERE {ws} ORDER BY p.created_at DESC LIMIT ? OFFSET ?
            """, v+[ps,(pg-1)*ps]))
            # 批量获取技能
            if rows:
                pids = tuple(r['pid'] for r in rows)
                placeholders = ','.join(['?'] * len(pids))
                skill_rows = db.ds(db.execute(
                    f"SELECT ps.pid, s.sname FROM project_skill ps JOIN skill s ON ps.sid=s.sid WHERE ps.pid IN ({placeholders})", pids))
                skill_map = {}
                for sr in skill_rows:
                    skill_map.setdefault(sr['pid'], []).append(sr['sname'])
                for r in rows:
                    r['skills'] = skill_map.get(r['pid'], [])
                    r['status_text'] = {0:'招募中',1:'已满',2:'进行中',3:'已结束'}.get(r['status'],'')
            self._json(200, 'success', {'list':rows,'total':total,'page':pg,'page_size':ps})

        elif self.command == 'PUT':
            b = self._body(); pid = b.get('pid')
            if not pid: return self._json(400, 'pid不能为空')
            if not db.execute("SELECT 1 FROM project WHERE pid=? AND is_deleted=0", (pid,)).fetchone():
                return self._json(404, '项目不存在')
            fs = []; vs = []
            for f in ['pname','description','deadline']:
                if f in b: fs.append(f'{f}=?'); vs.append(b[f])
            if 'max_members' in b:
                vv = int(b['max_members'])
                if vv < 1 or vv > 20: return self._json(400, '人数范围1-20')
                fs.append('max_members=?'); vs.append(vv)
            if 'status' in b:
                vv = int(b['status'])
                if vv not in (0,1,2,3): return self._json(400, '无效状态值')
                fs.append('status=?'); vs.append(vv)
            if 'cid' in b:
                if not db.execute("SELECT 1 FROM course WHERE cid=?", (int(b['cid']),)).fetchone():
                    return self._json(400, '课程不存在')
                fs.append('cid=?'); vs.append(int(b['cid']))
            if not fs: return self._json(400, '无可更新的字段')
            vs.append(pid)
            db.execute(f"UPDATE project SET {','.join(fs)} WHERE pid=? AND is_deleted=0", vs)
            db.commit(); self._json(200, '更新成功')

        elif self.command == 'DELETE':
            b = self._body(); pid = b.get('pid')
            if not pid: return self._json(400, 'pid不能为空')
            if not db.execute("SELECT 1 FROM project WHERE pid=? AND is_deleted=0", (pid,)).fetchone():
                return self._json(404, '项目不存在')
            db.execute("UPDATE project SET is_deleted=1 WHERE pid=?", (pid,))
            db.commit(); self._json(200, '项目已删除')

        else: self._json(405)

    def log_message(self, *a): pass

if __name__ == '__main__':
    print(f"TeamMatch v2.0 启动!")
    print(f"  前端: http://localhost:{PORT}/frontend/index.html")
    print(f"  管理员: http://localhost:{PORT}/frontend/admin.html")
    print(f"  管理员账号: admin001 / 123456")
    srv = http.server.HTTPServer(('0.0.0.0', PORT), Handler)
    try: srv.serve_forever()
    except KeyboardInterrupt: srv.server_close(); print("\n已停止")
