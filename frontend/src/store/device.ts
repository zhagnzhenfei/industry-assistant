import storage from './storage'
import proxyWithPersist, { PersistStrategy } from './valtio-persist'

const state = proxyWithPersist({
  name: 'device',
  version: 0,
  getStorage: () => storage,
  persistStrategies: {
    useDeepsearch: PersistStrategy.SingleFile,
  },
  migrations: {},

  initialState: {
    chatting: false,
    useDeepsearch: false,
  },
})

const actions = {
  setChatting(chatting: boolean) {
    state.chatting = chatting
  },
  setUseDeepsearch(useDeepsearch: boolean) {
    state.useDeepsearch = useDeepsearch
  },
}

export const deviceState = state
export const deviceActions = actions
