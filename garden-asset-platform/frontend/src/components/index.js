/**
 * 全局组件注册
 */
import StatCard from './common/StatCard.vue'
import StatusTag from './common/StatusTag.vue'
import EmptyState from './common/EmptyState.vue'

export { StatCard, StatusTag, EmptyState }

export default {
  install(app) {
    app.component('StatCard', StatCard)
    app.component('StatusTag', StatusTag)
    app.component('EmptyState', EmptyState)
  }
}
