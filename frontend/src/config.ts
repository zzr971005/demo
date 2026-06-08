// 前端配置文件

/// <reference types="vite/client" />

export const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '/api';

export const WS_URL = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000/ws';

export const APP_NAME = '期货自动进化因子挖掘系统';

export const APP_VERSION = '1.0.0';
