/**
 * TeamMatch 前端公共API模块
 * 所有页面必须引用此文件
 */

const API_BASE = 'http://localhost:8080';

// ==================== 工具函数 ====================
const util = {
    saveUser: function(data) {
        localStorage.setItem('user', JSON.stringify(data));
        localStorage.setItem('token', data.token || '');
        localStorage.setItem('role', data.role || 'member');
    },
    getUser: function() {
        var userStr = localStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    },
    getToken: function() {
        return localStorage.getItem('token') || '';
    },
    getRole: function() {
        return localStorage.getItem('role') || '';
    },
    clearUser: function() {
        localStorage.removeItem('user');
        localStorage.removeItem('token');
        localStorage.removeItem('role');
    },
    showToast: function(message, type) {
        type = type || 'info';
        var bgClass = 'bg-info';
        if (type === 'success') bgClass = 'bg-success';
        if (type === 'error') bgClass = 'bg-danger';
        if (type === 'warning') bgClass = 'bg-warning';

        var toast = $('<div class="toast-alert ' + bgClass + '">' + message + '</div>');
        $('body').append(toast);
        setTimeout(function() {
            toast.fadeOut(300, function() { $(this).remove(); });
        }, 3000);
    },
    handleResponse: function(res) {
        if (res.code === 401) {
            this.clearUser();
            window.location.href = 'login.html';
            throw new Error('登录已过期');
        }
        return res;
    },
    getQueryParam: function(name) {
        var urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(name);
    },
    formatDate: function(dateStr) {
        if (!dateStr) return '-';
        return dateStr.substring(0, 10);
    },
    formatDateTime: function(dateStr) {
        if (!dateStr) return '-';
        return dateStr;
    },
    // 项目状态映射
    projectStatusMap: {
        0: { text: '招募中', class: 'badge-success' },
        1: { text: '已满', class: 'badge-warning' },
        2: { text: '进行中', class: 'badge-primary' },
        3: { text: '已结束', class: 'badge-secondary' }
    },
    // 申请状态映射
    applicationStatusMap: {
        null: { text: '未申请', class: 'badge-secondary' },
        0: { text: '待处理', class: 'badge-warning' },
        1: { text: '已接受', class: 'badge-success' },
        2: { text: '已拒绝', class: 'badge-danger' },
        3: { text: '已取消', class: 'badge-secondary' }
    },
    // 进度状态映射
    progressStatusMap: {
        0: { text: '待完成', class: 'badge-secondary' },
        1: { text: '已完成', class: 'badge-success' }
    },
    // 技能分类映射
    skillCategoryMap: {
        '技术': 'badge-info',
        '设计': 'badge-warning',
        '管理': 'badge-primary',
        '其他': 'badge-secondary'
    },
    // 预置技能列表
    skillList: [
        { sid: 1, sname: '前端开发', category: '技术' },
        { sid: 2, sname: '后端开发', category: '技术' },
        { sid: 3, sname: '数据库设计', category: '技术' },
        { sid: 4, sname: 'UI设计', category: '设计' },
        { sid: 5, sname: '测试调试', category: '技术' },
        { sid: 6, sname: '文档编写', category: '管理' },
        { sid: 7, sname: '答辩演讲', category: '管理' },
        { sid: 8, sname: '算法实现', category: '技术' }
    ],
    // 生成星星HTML
    renderStars: function(proficiency) {
        var stars = '';
        for (var i = 1; i <= 5; i++) {
            stars += i <= proficiency ? '&#9733;' : '&#9734;';
        }
        return stars;
    },
    // 渲染导航栏
    renderNavbar: function(activePage) {
        var user = this.getUser();
        var role = this.getRole();
        var isAdmin = role === 'admin';
        var isLoggedIn = !!user;

        var navHtml = '<nav class="navbar navbar-expand-lg navbar-dark bg-dark">' +
            '<div class="container">' +
            '<a class="navbar-brand" href="index.html">TeamMatch</a>' +
            '<button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarNav">' +
            '<span class="navbar-toggler-icon"></span></button>' +
            '<div class="collapse navbar-collapse" id="navbarNav">' +
            '<ul class="navbar-nav mr-auto">' +
            '<li class="nav-item ' + (activePage === 'index' ? 'active' : '') + '">' +
            '<a class="nav-link" href="index.html">首页</a></li>' +
            '<li class="nav-item ' + (activePage === 'recommend' ? 'active' : '') + '">' +
            '<a class="nav-link" href="recommend.html">智能推荐</a></li>' +
            '<li class="nav-item ' + (activePage === 'publish' ? 'active' : '') + '">' +
            '<a class="nav-link" href="publish.html">发布项目</a></li>' +
            '</ul>' +
            '<ul class="navbar-nav">';

        if (isLoggedIn) {
            navHtml += '<li class="nav-item ' + (activePage === 'profile' ? 'active' : '') + '">' +
                '<a class="nav-link" href="profile.html">' + (user.nickname || user.username) + '</a></li>';
            if (isAdmin) {
                navHtml += '<li class="nav-item ' + (activePage === 'admin' ? 'active' : '') + '">' +
                    '<a class="nav-link" href="admin.html">管理后台</a></li>';
            }
            navHtml += '<li class="nav-item"><a class="nav-link" href="#" id="logoutBtn">退出</a></li>';
        } else {
            navHtml += '<li class="nav-item ' + (activePage === 'login' ? 'active' : '') + '">' +
                '<a class="nav-link" href="login.html">登录</a></li>';
        }

        navHtml += '</ul></div></div></nav>';
        return navHtml;
    },
    // 初始化导航栏（插入到body开头）
    initNavbar: function(activePage) {
        var navbar = this.renderNavbar(activePage);
        $('body').prepend(navbar);

        // 绑定退出事件
        $('#logoutBtn').on('click', function(e) {
            e.preventDefault();
            util.clearUser();
            window.location.href = 'login.html';
        });
    },
    // 检查登录状态
    requireLogin: function() {
        if (!this.getToken()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    },
    // 检查管理员权限
    requireAdmin: function() {
        if (!this.requireLogin()) return false;
        if (this.getRole() !== 'admin') {
            this.showToast('无权限访问', 'error');
            window.location.href = 'index.html';
            return false;
        }
        return true;
    }
};

// ==================== 请求封装 ====================
function request(method, path, data) {
    var url = API_BASE + path;
    var options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    var token = util.getToken();
    if (token) {
        options.headers['Authorization'] = 'Bearer ' + token;
    }

    if (data && (method === 'POST' || method === 'PUT' || method === 'DELETE')) {
        options.body = JSON.stringify(data);
    }

    return fetch(url, options)
        .then(function(response) {
            return response.json();
        })
        .then(function(res) {
            util.handleResponse(res);
            return res;
        })
        .catch(function(err) {
            if (err.message !== '登录已过期') {
                util.showToast('网络错误，请检查连接', 'error');
            }
            throw err;
        });
}

// ==================== API模块 ====================
const userApi = {
    register: function(data) {
        return request('POST', '/api/user/register', data);
    },
    login: function(data) {
        return request('POST', '/api/user/login', data);
    },
    getProfile: function() {
        return request('GET', '/api/user/profile');
    },
    updateProfile: function(data) {
        return request('PUT', '/api/user/profile', data);
    },
    getSkills: function() {
        return request('GET', '/api/user/skills');
    },
    addSkill: function(sid, proficiency) {
        return request('POST', '/api/user/skills', { sid: sid, proficiency: proficiency || 1 });
    },
    removeSkill: function(sid) {
        return request('DELETE', '/api/user/skills', { sid: sid });
    }
};

const courseApi = {
    getList: function(semester) {
        var params = semester ? '?semester=' + encodeURIComponent(semester) : '';
        return request('GET', '/api/courses' + params);
    }
};

const projectApi = {
    getList: function(params) {
        var query = '';
        if (params) {
            var parts = [];
            if (params.page) parts.push('page=' + params.page);
            if (params.page_size) parts.push('page_size=' + params.page_size);
            if (params.cid) parts.push('cid=' + params.cid);
            if (params.status !== undefined && params.status !== '') parts.push('status=' + params.status);
            if (params.keyword) parts.push('keyword=' + encodeURIComponent(params.keyword));
            if (parts.length > 0) query = '?' + parts.join('&');
        }
        return request('GET', '/api/projects' + query);
    },
    create: function(data) {
        return request('POST', '/api/projects', data);
    },
    getDetail: function(pid) {
        return request('GET', '/api/projects/' + pid);
    },
    apply: function(pid, message) {
        return request('POST', '/api/projects/' + pid + '/apply', { message: message || '' });
    },
    getApplications: function(pid) {
        return request('GET', '/api/projects/' + pid + '/applications');
    },
    getProgress: function(pid) {
        return request('GET', '/api/projects/' + pid + '/progress');
    },
    addProgress: function(pid, data) {
        return request('POST', '/api/projects/' + pid + '/progress', data);
    },
    updateProgress: function(pid, data) {
        return request('PUT', '/api/projects/' + pid + '/progress', data);
    }
};

const applicationApi = {
    handle: function(aid, action) {
        return request('PUT', '/api/applications/' + aid + '/handle', { action: action });
    }
};

const recommendApi = {
    getList: function(cid) {
        var params = cid ? '?cid=' + cid : '';
        return request('GET', '/api/recommendations' + params);
    }
};

const adminApi = {
    getUsers: function(params) {
        var query = '';
        if (params) {
            var parts = [];
            if (params.page) parts.push('page=' + params.page);
            if (params.page_size) parts.push('page_size=' + params.page_size);
            if (params.role) parts.push('role=' + params.role);
            if (params.is_active !== undefined) parts.push('is_active=' + params.is_active);
            if (params.keyword) parts.push('keyword=' + encodeURIComponent(params.keyword));
            if (parts.length > 0) query = '?' + parts.join('&');
        }
        return request('GET', '/api/admin/users' + query);
    },
    createUser: function(data) {
        return request('POST', '/api/admin/users', data);
    },
    updateUser: function(data) {
        return request('PUT', '/api/admin/users', data);
    },
    getStats: function() {
        return request('GET', '/api/admin/stats');
    }
};

// ==================== 全局对象 ====================
window.TeamMatch = {
    userApi: userApi,
    courseApi: courseApi,
    projectApi: projectApi,
    applicationApi: applicationApi,
    recommendApi: recommendApi,
    adminApi: adminApi,
    util: util
};
