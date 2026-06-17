/**
 * TeamMatch 前端公共工具库
 * 基于 fetch 封装的 API 请求模块
 */
(function () {
  window.TeamMatch = window.TeamMatch || {};
  console.log('[TeamMatch] api.js loaded');

  // 自动适配：同端口下后端也由 Python 服务器处理 /api/ 路径
  const API_BASE = '';
  let authToken = localStorage.getItem('token') || null;

  // fetch 超时包装（默认 10 秒）
  function fetchWithTimeout(url, opts, timeoutMs) {
    timeoutMs = timeoutMs || 10000;
    return new Promise(function(resolve, reject) {
      var timer = setTimeout(function() {
        reject(new Error('请求超时，请检查网络或刷新重试'));
      }, timeoutMs);
      fetch(url, opts).then(function(res) {
        clearTimeout(timer);
        resolve(res);
      }).catch(function(err) {
        clearTimeout(timer);
        reject(err);
      });
    });
  }

  // 通用 fetch 封装（带重试）
  async function request(method, path, body, params, retryCount) {
    retryCount = retryCount || 0;
    var url = API_BASE + path;
    if (params) {
      var qs = new URLSearchParams(params).toString();
      if (qs) url += '?' + qs;
    }
    var opts = { method: method, credentials: 'include' };
    if (authToken) {
      opts.headers = { 'Authorization': 'Bearer ' + authToken };
    }
    if (body && (method === 'POST' || method === 'PUT' || method === 'DELETE')) {
      opts.headers = Object.assign({}, opts.headers || {}, { 'Content-Type': 'application/json' });
      opts.body = JSON.stringify(body);
    }

    try {
      var res = await fetchWithTimeout(url, opts, 10000);
      var data = await res.json();
      handleResponse(data);
      return data;
    } catch (err) {
      if (err._redirect) throw err;
      if (retryCount < 1) {
        console.warn('[TeamMatch] 请求失败，正在重试:', path, err.message);
        await new Promise(function(r) { setTimeout(r, 800); });
        return request(method, path, body, params, retryCount + 1);
      }
      throw err;
    }
  }

  function handleResponse(res) {
    if (res && res.code === 401) {
      authToken = null;
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      localStorage.removeItem('role');
      if (window.location.pathname.indexOf('login.html') === -1 &&
          window.location.pathname.indexOf('register.html') === -1) {
        // 抛出异常中止当前请求链，防止后续 API 调用在页面跳转时被浏览器 abort
        var e = new Error('登录已过期，请重新登录');
        e._redirect = true;
        window.location.href = 'login.html';
        throw e;
      }
    }
  }

  window.TeamMatch.api = {
    get: function(path, params) { return request('GET', path, null, params); },
    post: function(path, body) { return request('POST', path, body); },
    put: function(path, body) { return request('PUT', path, body); },
    del: function(path, body) { return request('DELETE', path, body); },
  };

  // ============ 用户 API ============
  window.TeamMatch.userApi = {
    register: function(data) { return window.TeamMatch.api.post('/api/user/register', data); },
    login: function(data) { return window.TeamMatch.api.post('/api/user/login', data); },
    getProfile: function() { return window.TeamMatch.api.get('/api/user/profile'); },
    updateProfile: function(data) { return window.TeamMatch.api.put('/api/user/profile', data); },
    getSkills: function() { return window.TeamMatch.api.get('/api/user/skills'); },
    addSkill: function(sid, proficiency) { return window.TeamMatch.api.post('/api/user/skills', { sid: sid, proficiency: proficiency || 1 }); },
    removeSkill: function(sid) { return window.TeamMatch.api.del('/api/user/skills', { sid: sid }); },
  };

  // ============ 课程 API ============
  window.TeamMatch.courseApi = {
    getList: function(semester) { return window.TeamMatch.api.get('/api/courses', semester ? { semester: semester } : null); },
  };

  // ============ 项目 API ============
  window.TeamMatch.projectApi = {
    getList: function(params) { return window.TeamMatch.api.get('/api/projects', params); },
    create: function(data) { return window.TeamMatch.api.post('/api/projects', data); },
    getDetail: function(pid) { return window.TeamMatch.api.get('/api/projects/' + pid); },
    apply: function(pid, message) { return window.TeamMatch.api.post('/api/projects/' + pid + '/apply', { message: message }); },
    getApplications: function(pid) { return window.TeamMatch.api.get('/api/projects/' + pid + '/applications'); },
    getProgress: function(pid) { return window.TeamMatch.api.get('/api/projects/' + pid + '/progress'); },
    addProgress: function(pid, data) { return window.TeamMatch.api.post('/api/projects/' + pid + '/progress', data); },
    updateProgress: function(pid, data) { return window.TeamMatch.api.put('/api/projects/' + pid + '/progress', data); },
  };

  // ============ 申请 API ============
  window.TeamMatch.applicationApi = {
    handle: function(aid, action) { return window.TeamMatch.api.put('/api/applications/' + aid + '/handle', { action: action }); },
  };

  // ============ 推荐 API ============
  window.TeamMatch.recommendApi = {
    getList: function(cid) { return window.TeamMatch.api.get('/api/recommendations', cid ? { cid: cid } : null); },
  };

  // ============ 管理员 API ============
  window.TeamMatch.adminApi = {
    getUsers: function(params) { return window.TeamMatch.api.get('/api/admin/users', params); },
    createUser: function(data) { return window.TeamMatch.api.post('/api/admin/users', data); },
    updateUser: function(data) { return window.TeamMatch.api.put('/api/admin/users', data); },
    getStats: function() { return window.TeamMatch.api.get('/api/admin/stats'); },
  };

  // ============ 通用工具 ============
  window.TeamMatch.util = {
    getStatusText: function(status) { return ({ 0: '招募中', 1: '已满', 2: '进行中', 3: '已结束' })[status] || '未知'; },
    getStatusClass: function(status) { return ({ 0: 'badge-success', 1: 'badge-warning', 2: 'badge-primary', 3: 'badge-secondary' })[status] || 'badge-secondary'; },
    getAppStatusText: function(s) { return ({ 0: '待处理', 1: '已接受', 2: '已拒绝', 3: '已取消' })[s] || ''; },
    isLoggedIn: function() { return !!localStorage.getItem('user'); },
    getUser: function() { try { return JSON.parse(localStorage.getItem('user')); } catch (e) { return null; } },
    saveUser: function(u) { localStorage.setItem('user', JSON.stringify(u)); localStorage.setItem('role', u.role || 'member'); if (u.token) localStorage.setItem('token', u.token); authToken = u.token || null; },
    getRole: function() { return localStorage.getItem('role') || 'member'; },
    isAdmin: function() { return localStorage.getItem('role') === 'admin'; },
    logout: function() { localStorage.removeItem('user'); localStorage.removeItem('token'); localStorage.removeItem('role'); authToken = null; window.location.href = 'login.html'; },
    showToast: function(msg, type) {
      var t = document.createElement('div');
      t.className = 'toast toast-' + (type || 'info');
      t.textContent = msg;
      t.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;padding:12px 24px;border-radius:6px;color:#fff;animation:fadeIn 0.3s;';
      t.style.background = type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#17a2b8';
      document.body.appendChild(t);
      setTimeout(function() { t.style.opacity = '0'; t.style.transition = '0.3s'; setTimeout(function() { t.remove(); }, 300); }, 2500);
    },
    // 加载状态管理
    setLoading: function(el, isLoading) {
      var container = typeof el === 'string' ? document.querySelector(el) : el;
      if (!container) return;
      if (isLoading) {
        container.innerHTML = '<div class="text-center py-5 text-muted"><div class="spinner-border text-primary mb-2" role="status"></div><div>加载中...</div></div>';
      }
    },
    showError: function(el, msg, onRetry) {
      var container = typeof el === 'string' ? document.querySelector(el) : el;
      if (!container) return;
      var html = '<div class="text-center py-5 text-muted"><div style="font-size:2.5rem">⚠️</div><div class="mb-2">' + (msg || '加载失败') + '</div>';
      if (onRetry) {
        html += '<button class="btn btn-outline-primary btn-sm" id="retryBtn">重新加载</button>';
      }
      html += '</div>';
      container.innerHTML = html;
      if (onRetry) {
        var btn = container.querySelector('#retryBtn');
        if (btn) btn.onclick = onRetry;
      }
    },
  };

  // 页面初始化：检查登录态并渲染导航
  document.addEventListener('DOMContentLoaded', function () {
    var user = window.TeamMatch.util.getUser();
    var navUser = document.getElementById('nav-user-info');
    if (navUser && user) {
      var html = '<span class="navbar-text mr-3">' + user.nickname + '</span>';
      if (user.role === 'admin') {
        html += '<a class="btn btn-outline-warning btn-sm mr-2" href="admin.html">管理后台</a>';
      }
      html += '<a class="btn btn-outline-light btn-sm" href="profile.html">个人中心</a>' +
        '<button class="btn btn-outline-danger btn-sm ml-2" onclick="TeamMatch.util.logout()">退出</button>';
      navUser.innerHTML = html;
    }
  });
})();

// Toast 动画
var style = document.createElement('style');
style.textContent = '@keyframes fadeIn{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}';
document.head.appendChild(style);
