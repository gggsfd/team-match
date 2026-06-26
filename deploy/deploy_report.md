
## TeamMatch 服务器部署报告

### 服务器信息
- **公网IP**: 8.138.252.49
- **操作系统**: ubuntu
- **部署时间**: 2026-06-19 18:26:17

### 软件版本
| 软件 | 版本 |
|------|------|
| PHP | PHP 8.4.22 (cli) (built: Jun  6 2026 06:34:31) (NTS) |
| MySQL | 未安装 |
| Nginx | bash: line 1: nginx: command not found |
| Python3 | Python 3.10.12 |
| Git | git version 2.34.1 |

### 服务状态
| 服务 | 状态 |
|------|------|
| Nginx | inactive
inactive |
| MySQL | inactive
inactive |
| PHP-FPM | inactive
inactive |
| SSH | active |

### 安全配置
- **防火墙**: 仅开放 22(SSH), 80(HTTP), 443(HTTPS), 8080
- **SSH**: Root仅允许密钥登录, 最大尝试3次, 禁用X11转发, 空密码禁止
- **PHP**: expose_php=Off, display_errors=Off, log_errors=On

### 端口监听
```
LISTEN 0      128          0.0.0.0:22        0.0.0.0:*    users:(("sshd",pid=24021,fd=3))           
LISTEN 0      128             [::]:22           [::]:*    users:(("sshd",pid=24021,fd=4))          
```

### HTTP状态码: 200

### API测试
```
<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><head>
<title>404 Not Found</title>
</head><body>
<h1>Not Found</h1>
<p>The requested URL was not found on this server.</p>
<hr>
<address>Apach
```

### 数据库
```

```

### 访问地址
- **前端首页**: http://8.138.252.49/
- **管理后台**: http://8.138.252.49/frontend/admin.html
- **API接口**: http://8.138.252.49/api/courses
- **Python开发服务器**: http://8.138.252.49:8080/frontend/index.html (需手动启动server.py)

### 项目目录
- **项目根目录**: /opt/teammatch
- **日志目录**: /opt/teammatch/logs
- **用户**: teammatch

### 数据库连接信息
- **数据库名**: team_match
- **用户名**: teammatch
- **密码**: Tm@2024#Secure
- **Root密码**: Root@Tm#2024#Admin (请及时修改)
