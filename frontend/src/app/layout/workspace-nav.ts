import type { Component } from 'vue'
import {
  Activity,
  AlertTriangle,
  FileSearch,
  Gauge,
  LayoutDashboard,
  List,
  ShieldAlert,
  Zap,
} from 'lucide-vue-next'
import type { WorkspaceTabKind } from './presets'
import type { PaneKind } from './panes'

/** Icon per workspace tab — vertical nav rail (DSH-style sidebar). */
export const WORKSPACE_NAV_ICONS: Readonly<Record<WorkspaceTabKind, Component>> = {
  sld: LayoutDashboard,
  state: Activity,
  measurements: Gauge,
  energization: Zap,
  'alarm-list': List,
  alarms: ShieldAlert,
  anomalies: AlertTriangle,
  evidence: FileSearch,
}

export function workspaceNavIcon(kind: PaneKind): Component {
  return WORKSPACE_NAV_ICONS[kind as WorkspaceTabKind]
}
