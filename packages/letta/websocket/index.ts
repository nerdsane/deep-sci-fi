/**
 * WebSocket Module
 *
 * Provides polling-based communication between tools and browser clients.
 *
 * Architecture:
 * - Tools call broadcast() to queue messages for delivery
 * - Browser clients poll getPendingMessages() via /api/ws/poll endpoint
 * - Interactions from browser are queued via queueInteraction()
 * - Agents poll get_canvas_interactions tool to receive user actions
 *
 * For production, consider upgrading to:
 * - Server-Sent Events (SSE) for real-time without WebSocket complexity
 * - WebSocket for true bidirectional communication
 * - Redis pub/sub for multi-instance deployments
 */

export * from './manager';
export * from './types';
