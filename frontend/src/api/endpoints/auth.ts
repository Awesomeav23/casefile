import { api } from '../client'
import type { components } from '../schema'

type S = components['schemas']
export type User = S['UserOut']
export type Guest = S['GuestOut']
export type Me = S['MeOut']
export type AuthResult = S['AuthOut']
export type Claimed = S['ClaimedOut']

export const getMe = () => api.get<Me>('/auth/me/')

export const login = (body: { email: string; password: string }) =>
  api.post<AuthResult>('/auth/login/', body)

export const register = (body: { email: string; password: string; display_name: string }) =>
  api.post<AuthResult>('/auth/register/', body)

export const logout = () => api.post<void>('/auth/logout/')

export const requestPasswordReset = (body: { email: string }) =>
  api.post<S['DetailOut']>('/auth/password-reset/', body)

export const confirmPasswordReset = (body: { uid: string; token: string; new_password: string }) =>
  api.post<void>('/auth/password-reset/confirm/', body)
