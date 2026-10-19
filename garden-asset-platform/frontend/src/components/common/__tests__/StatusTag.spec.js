import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusTag from '@/components/common/StatusTag.vue'

describe('StatusTag', () => {
  it('renders the mapped label and success tone', () => {
    const wrapper = mount(StatusTag, { props: { status: 'embedded' } })
    expect(wrapper.text()).toContain('已嵌入')
    expect(wrapper.classes()).toContain('success')
  })

  it('renders danger for rejected', () => {
    const wrapper = mount(StatusTag, { props: { status: 'rejected' } })
    expect(wrapper.text()).toContain('已拒绝')
    expect(wrapper.classes()).toContain('error')
  })

  it('falls back to the raw status with neutral tone', () => {
    const wrapper = mount(StatusTag, { props: { status: 'mystery' } })
    expect(wrapper.text()).toContain('mystery')
    expect(wrapper.classes()).toContain('neutral')
  })
})
