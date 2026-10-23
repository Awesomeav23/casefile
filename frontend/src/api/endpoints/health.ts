import { api } from '../client'
import type { components } from '../schema'

export type Health = components['schemas']['Health']

export const getHealth = () => api.get<Health>('/health/')
