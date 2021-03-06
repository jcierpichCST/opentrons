// @flow

import type {
  StartDiscoveryAction,
  FinishDiscoveryAction,
  RemoveRobotAction,
} from './types'

export const DISCOVERY_START: 'discovery:START' = 'discovery:START'

export const DISCOVERY_FINISH: 'discovery:FINISH' = 'discovery:FINISH'

export const DISCOVERY_UPDATE_LIST: 'discovery:UPDATE_LIST' =
  'discovery:UPDATE_LIST'

export const DISCOVERY_REMOVE: 'discovery:REMOVE' = 'discovery:REMOVE'

export function startDiscovery(
  timeout: number | null = null
): StartDiscoveryAction {
  return {
    type: DISCOVERY_START,
    payload: { timeout },
    meta: { shell: true },
  }
}

export function finishDiscovery(): FinishDiscoveryAction {
  return { type: DISCOVERY_FINISH, meta: { shell: true } }
}

export function removeRobot(robotName: string): RemoveRobotAction {
  return {
    type: DISCOVERY_REMOVE,
    payload: { robotName },
    meta: { shell: true },
  }
}
