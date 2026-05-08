/**
 * 全局组件注册
 */
import StatCard from './common/StatCard.vue'
import StatusTag from './common/StatusTag.vue'
import EmptyState from './common/EmptyState.vue'
import ErrorBoundary from './common/ErrorBoundary.vue'

export { StatCard, StatusTag, EmptyState, ErrorBoundary }

export default {
  install(app) {
    app.component('StatCard', StatCard)
    app.component('StatusTag', StatusTag)
    app.component('EmptyState', EmptyState)
    app.component('ErrorBoundary', ErrorBoundary)
  }
}
