import { useMemo } from 'react'

type Permission = 'read' | 'write' | 'admin' | 'trading' | 'risk_management'

interface UserPermissions {
  permissions: Permission[]
  role: 'viewer' | 'trader' | 'admin' | 'superadmin'
}

// 模拟权限配置，实际应从后端API获取
const ROLE_PERMISSIONS: Record<string, Permission[]> = {
  viewer: ['read'],
  trader: ['read', 'write', 'trading'],
  admin: ['read', 'write', 'trading', 'risk_management'],
  superadmin: ['read', 'write', 'admin', 'trading', 'risk_management'],
}

export function usePermissions() {
  // 实际应从用户状态或API获取
  const userRole: UserPermissions['role'] = 'admin'
  const userPermissions = ROLE_PERMISSIONS[userRole] || []

  const hasPermission = (permission: Permission): boolean => {
    return userPermissions.includes(permission)
  }

  const hasAnyPermission = (permissions: Permission[]): boolean => {
    return permissions.some((p) => userPermissions.includes(p))
  }

  const hasAllPermissions = (permissions: Permission[]): boolean => {
    return permissions.every((p) => userPermissions.includes(p))
  }

  const canRead = () => hasPermission('read')
  const canWrite = () => hasPermission('write')
  const canTrade = () => hasPermission('trading')
  const canManageRisk = () => hasPermission('risk_management')
  const isAdmin = () => hasPermission('admin')

  return useMemo(
    () => ({
      role: userRole,
      permissions: userPermissions,
      hasPermission,
      hasAnyPermission,
      hasAllPermissions,
      canRead,
      canWrite,
      canTrade,
      canManageRisk,
      isAdmin,
    }),
    [userRole, userPermissions]
  )
}
