import {
  pgTable,
  uuid,
  text,
  timestamp,
  integer,
  jsonb,
  varchar,
  boolean,
  index,
} from 'drizzle-orm/pg-core'
import { relations } from 'drizzle-orm'

// Users table - supports both human and agent users
export const users = pgTable(
  'platform_users',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    type: varchar('type', { length: 10 }).notNull().$type<'human' | 'agent'>(),
    name: varchar('name', { length: 255 }).notNull(),
    avatarUrl: text('avatar_url'),
    apiKeyHash: varchar('api_key_hash', { length: 128 }), // For agent users
    callbackUrl: text('callback_url'), // For agent webhooks
    createdAt: timestamp('created_at').defaultNow().notNull(),
    lastActiveAt: timestamp('last_active_at'),
  },
  (table) => ({
    typeIdx: index('user_type_idx').on(table.type),
  })
)

// API keys for agent users
export const apiKeys = pgTable(
  'platform_api_keys',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    userId: uuid('user_id')
      .references(() => users.id, { onDelete: 'cascade' })
      .notNull(),
    keyHash: varchar('key_hash', { length: 128 }).notNull(),
    keyPrefix: varchar('key_prefix', { length: 10 }).notNull(), // For identification
    name: varchar('name', { length: 100 }),
    createdAt: timestamp('created_at').defaultNow().notNull(),
    lastUsedAt: timestamp('last_used_at'),
    expiresAt: timestamp('expires_at'),
    isRevoked: boolean('is_revoked').default(false),
  },
  (table) => ({
    userIdx: index('api_key_user_idx').on(table.userId),
  })
)

// Worlds - AI-created futures
export const worlds = pgTable(
  'platform_worlds',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    name: varchar('name', { length: 255 }).notNull(),
    premise: text('premise').notNull(),
    yearSetting: integer('year_setting').notNull(),
    causalChain: jsonb('causal_chain')
      .default([])
      .$type<{ year: number; event: string; consequence: string }[]>(),
    createdBy: uuid('created_by')
      .references(() => users.id)
      .notNull(),
    createdAt: timestamp('created_at').defaultNow().notNull(),
    updatedAt: timestamp('updated_at').defaultNow().notNull(),
    isActive: boolean('is_active').default(true),
    // Cached counts for performance
    dwellerCount: integer('dweller_count').default(0),
    storyCount: integer('story_count').default(0),
    followerCount: integer('follower_count').default(0),
  },
  (table) => ({
    activeIdx: index('world_active_idx').on(table.isActive),
    createdAtIdx: index('world_created_at_idx').on(table.createdAt),
  })
)

// Dwellers - agents living in worlds
export const dwellers = pgTable(
  'platform_dwellers',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    worldId: uuid('world_id')
      .references(() => worlds.id, { onDelete: 'cascade' })
      .notNull(),
    agentId: uuid('agent_id')
      .references(() => users.id)
      .notNull(),
    persona: jsonb('persona').notNull().$type<{
      name: string
      role: string
      background: string
      beliefs: string[]
      memories: string[]
    }>(),
    joinedAt: timestamp('joined_at').defaultNow().notNull(),
    isActive: boolean('is_active').default(true),
  },
  (table) => ({
    worldIdx: index('dweller_world_idx').on(table.worldId),
    agentIdx: index('dweller_agent_idx').on(table.agentId),
  })
)

// Conversations between dwellers
export const conversations = pgTable(
  'platform_conversations',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    worldId: uuid('world_id')
      .references(() => worlds.id, { onDelete: 'cascade' })
      .notNull(),
    participants: jsonb('participants').notNull().$type<string[]>(), // Dweller IDs
    startedAt: timestamp('started_at').defaultNow().notNull(),
    updatedAt: timestamp('updated_at').defaultNow().notNull(),
    isActive: boolean('is_active').default(true),
  },
  (table) => ({
    worldIdx: index('conversation_world_idx').on(table.worldId),
    updatedIdx: index('conversation_updated_idx').on(table.updatedAt),
  })
)

// Messages in conversations
export const conversationMessages = pgTable(
  'platform_conversation_messages',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    conversationId: uuid('conversation_id')
      .references(() => conversations.id, { onDelete: 'cascade' })
      .notNull(),
    dwellerId: uuid('dweller_id')
      .references(() => dwellers.id)
      .notNull(),
    content: text('content').notNull(),
    timestamp: timestamp('timestamp').defaultNow().notNull(),
  },
  (table) => ({
    convIdx: index('message_conversation_idx').on(table.conversationId),
    timestampIdx: index('message_timestamp_idx').on(table.timestamp),
  })
)

// Stories - videos created by storyteller agents
export const stories = pgTable(
  'platform_stories',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    worldId: uuid('world_id')
      .references(() => worlds.id, { onDelete: 'cascade' })
      .notNull(),
    type: varchar('type', { length: 10 }).notNull().$type<'short' | 'long'>(),
    title: varchar('title', { length: 255 }).notNull(),
    description: text('description'),
    videoUrl: text('video_url'),
    thumbnailUrl: text('thumbnail_url'),
    transcript: text('transcript'),
    durationSeconds: integer('duration_seconds').default(0),
    createdBy: uuid('created_by')
      .references(() => users.id)
      .notNull(),
    createdAt: timestamp('created_at').defaultNow().notNull(),
    // Engagement metrics
    viewCount: integer('view_count').default(0),
    reactionCounts: jsonb('reaction_counts')
      .default({ fire: 0, mind: 0, heart: 0, thinking: 0 })
      .$type<{ fire: number; mind: number; heart: number; thinking: number }>(),
    // Generation metadata
    generationStatus: varchar('generation_status', { length: 20 })
      .default('pending')
      .$type<'pending' | 'generating' | 'complete' | 'failed'>(),
    generationJobId: varchar('generation_job_id', { length: 255 }),
    generationError: text('generation_error'),
  },
  (table) => ({
    worldIdx: index('story_world_idx').on(table.worldId),
    createdAtIdx: index('story_created_at_idx').on(table.createdAt),
    typeIdx: index('story_type_idx').on(table.type),
  })
)

// Social interactions - reactions, follows
export const socialInteractions = pgTable(
  'platform_social_interactions',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    userId: uuid('user_id')
      .references(() => users.id, { onDelete: 'cascade' })
      .notNull(),
    targetType: varchar('target_type', { length: 20 })
      .notNull()
      .$type<'story' | 'world' | 'conversation' | 'user'>(),
    targetId: uuid('target_id').notNull(),
    interactionType: varchar('interaction_type', { length: 20 })
      .notNull()
      .$type<'react' | 'follow' | 'share'>(),
    data: jsonb('data'), // For reactions: { type: 'fire' | 'mind' | ... }
    createdAt: timestamp('created_at').defaultNow().notNull(),
  },
  (table) => ({
    userIdx: index('social_user_idx').on(table.userId),
    targetIdx: index('social_target_idx').on(table.targetType, table.targetId),
    uniqueInteraction: index('social_unique_idx').on(
      table.userId,
      table.targetType,
      table.targetId,
      table.interactionType
    ),
  })
)

// Comments
export const comments = pgTable(
  'platform_comments',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    userId: uuid('user_id')
      .references(() => users.id, { onDelete: 'cascade' })
      .notNull(),
    targetType: varchar('target_type', { length: 20 })
      .notNull()
      .$type<'story' | 'world' | 'conversation'>(),
    targetId: uuid('target_id').notNull(),
    content: text('content').notNull(),
    parentId: uuid('parent_id'), // Self-reference for threads
    createdAt: timestamp('created_at').defaultNow().notNull(),
    updatedAt: timestamp('updated_at').defaultNow().notNull(),
    isDeleted: boolean('is_deleted').default(false),
  },
  (table) => ({
    userIdx: index('comment_user_idx').on(table.userId),
    targetIdx: index('comment_target_idx').on(table.targetType, table.targetId),
    parentIdx: index('comment_parent_idx').on(table.parentId),
    createdAtIdx: index('comment_created_at_idx').on(table.createdAt),
  })
)

// Drizzle relations
export const usersRelations = relations(users, ({ many }) => ({
  apiKeys: many(apiKeys),
  worlds: many(worlds),
  dwellers: many(dwellers),
  stories: many(stories),
  comments: many(comments),
  interactions: many(socialInteractions),
}))

export const worldsRelations = relations(worlds, ({ one, many }) => ({
  creator: one(users, {
    fields: [worlds.createdBy],
    references: [users.id],
  }),
  dwellers: many(dwellers),
  conversations: many(conversations),
  stories: many(stories),
}))

export const dwellersRelations = relations(dwellers, ({ one, many }) => ({
  world: one(worlds, {
    fields: [dwellers.worldId],
    references: [worlds.id],
  }),
  agent: one(users, {
    fields: [dwellers.agentId],
    references: [users.id],
  }),
  messages: many(conversationMessages),
}))

export const conversationsRelations = relations(
  conversations,
  ({ one, many }) => ({
    world: one(worlds, {
      fields: [conversations.worldId],
      references: [worlds.id],
    }),
    messages: many(conversationMessages),
  })
)

export const storiesRelations = relations(stories, ({ one }) => ({
  world: one(worlds, {
    fields: [stories.worldId],
    references: [worlds.id],
  }),
  creator: one(users, {
    fields: [stories.createdBy],
    references: [users.id],
  }),
}))

export const commentsRelations = relations(comments, ({ one }) => ({
  user: one(users, {
    fields: [comments.userId],
    references: [users.id],
  }),
  parent: one(comments, {
    fields: [comments.parentId],
    references: [comments.id],
  }),
}))
