# @garden-asset-platform/frontend

## 安装依赖

```bash
npm install
```

## 开发运行

```bash
npm run dev
```

## 生产构建

```bash
npm run build
```

## 页面结构

```
/                   首页
/login              登录
/register           注册
/assets             资产列表
/assets/:id         资产详情
/assets/upload      上传资产
/trace              溯源查询
/license/apply      申请授权
/license/my         我的授权
/certificate/:id    存证证书
/admin              管理后台
  /admin/dashboard    仪表盘
  /admin/assets       资产管理
  /admin/watermark    水印管理
  /admin/license      授权审批
  /admin/blockchain   存证管理
  /admin/users        用户管理
```

## 组件结构

```
src/
├── components/
│   ├── common/
│   │   ├── EmptyState.vue
│   │   ├── LoadingWrapper.vue
│   │   ├── StatCard.vue
│   │   └── StatusTag.vue
│   └── index.js
├── constants/
│   └── index.js
├── utils/
│   └── index.js
├── api/
│   ├── index.js
│   └── modules.js
├── stores/
│   └── user.js
└── router/
    └── index.js
```