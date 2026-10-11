import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'
import { describe, expect, it } from 'vitest'

import { useConnectivity } from './useConnectivity'

const Sonda = defineComponent({
  setup() {
    const { online } = useConnectivity()
    return () => h('span', online.value ? 'online' : 'offline')
  },
})

function definirOnline(valor: boolean): void {
  Object.defineProperty(window.navigator, 'onLine', { configurable: true, value: valor })
}

describe('useConnectivity', () => {
  it('reage aos eventos online e offline', async () => {
    definirOnline(true)
    const wrapper = mount(Sonda)
    expect(wrapper.text()).toBe('online')

    definirOnline(false)
    window.dispatchEvent(new Event('offline'))
    await nextTick()
    expect(wrapper.text()).toBe('offline')

    definirOnline(true)
    window.dispatchEvent(new Event('online'))
    await nextTick()
    expect(wrapper.text()).toBe('online')

    wrapper.unmount()
  })
})
