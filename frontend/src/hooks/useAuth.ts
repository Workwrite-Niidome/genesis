'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/stores/authStore'

export function useAuth() {
  const { resident, token, isLoading, error, fetchMe, logout, clearError } =
    useAuthStore()

  useEffect(() => {
    if (token && !resident && !isLoading) {
      fetchMe()
    }
  }, [token, resident, isLoading, fetchMe])

  return {
    resident,
    token,
    isLoading,
    error,
    isAuthenticated: !!resident,
    logout,
    clearError,
  }
}

export function useRequireAuth() {
  const auth = useAuth()

  useEffect(() => {
    if (!auth.isLoading && !auth.isAuthenticated) {
      window.location.href = '/auth'
    }
  }, [auth.isLoading, auth.isAuthenticated])

  return auth
}
