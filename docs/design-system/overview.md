# KuberPilot Design System v1.0

## 概览

飞书蓝色系迭代设计方案，基于 #2563eb 主色建立完整设计体系。

## 文件清单

| 文件 | 说明 |
|------|------|
| `tokens.css` | 完整 CSS 令牌定义（色彩梯度、排版、间距、圆角、阴影、交互态、暗色主题） |
| `index.html` | 设计系统文档站（在线交互式浏览，含令牌参考、组件示例、页面模式、WCAG规范） |

## 核心决策

1. **主色**: #2563eb (Tailwind blue-600)，50-900 完整梯度
2. **排版**: Inter (UI) + Noto Sans SC (中文) + Cascadia Code (K8s/YAML/SQL)
3. **间距**: 4px base unit，1-24 scale
4. **页面模式**: Hero + Stats + Context Strip + Tabs + Workbench Card
5. **四大优先场景**: 任务工作台、AIOps对话、K8s管理、可观测性
6. **暗色主题**: 已定义 [data-theme="dark"] 令牌覆盖
7. **WCAG AA**: 4.5:1 对比度、focus ring、语义 HTML、44px touch target

## 开发者 Handoff

- 替换 `frontend/src/assets/main.css` 中散落的硬编码值为 `tokens.css` 变量引用
- 统一组件级样式到令牌系统（消除 rgba 硬编码）
- `index.html` 文档站可直接在浏览器打开查看完整规范
