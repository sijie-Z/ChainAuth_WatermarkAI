# 园林资产平台前端

基于Vue 3的数字资产管理系统前端

## 技术栈

- Vue 3.4
- Vite 5
- Element Plus
- Pinia
- Vue Router
- Axios

## 安装步骤

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build
```

## 项目结构

```
frontend/
├── public/              # 静态资源
├── src/
│   ├── main.js         # 入口文件
│   ├── App.vue         # 根组件
│   ├── router/         # 路由配置
│   ├── stores/         # 状态管理
│   ├── api/            # API封装
│   └── views/          # 页面组件
│       ├── home/       # 首页
│       ├── asset/      # 资产页面
│       ├── trace/      # 溯源页面
│       ├── license/    # 授权页面
│       ├── certificate/# 证书页面
│       └── admin/      # 管理后台
└── package.json
```

## 页面路由

- /home - 首页
- /login - 登录
- /register - 注册
- /assets - 资产列表
- /assets/:id - 资产详情
- /assets/upload - 上传资产
- /trace - 溯源查询
- /license/apply - 申请授权
- /license/my - 我的授权
- /admin/* - 管理后台