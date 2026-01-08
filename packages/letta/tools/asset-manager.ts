/**
 * asset_manager - Manage multimedia assets for DSF stories and worlds
 *
 * Operations:
 * - save: Store asset file to S3
 * - load: Retrieve asset metadata
 * - list: Get all assets for a world/story
 * - delete: Remove asset
 *
 * Uses S3 for storage and PostgreSQL for metadata.
 */

import type { PrismaClient } from '@deep-sci-fi/db';

// ============================================================================
// Types
// ============================================================================

export interface AssetManagerParams {
  operation: 'save' | 'load' | 'list' | 'delete';
  asset_id?: string;
  world_id?: string;
  story_id?: string;
  segment_id?: string;
  data?: string; // Base64 data URL or raw base64
  type?: 'image' | 'audio' | 'video';
  category?: 'character' | 'background' | 'music' | 'sfx' | 'ui';
  description?: string;
  metadata?: Record<string, any>;
}

export interface AssetManagerResult {
  success: boolean;
  message: string;
  asset?: {
    id: string;
    type: string;
    category?: string;
    storagePath: string;
    url?: string;
    description?: string;
  };
  assets?: Array<{
    id: string;
    type: string;
    category?: string;
    storagePath: string;
    url?: string;
    description?: string;
  }>;
}

// ============================================================================
// Main Entry Point
// ============================================================================

export async function asset_manager(
  params: AssetManagerParams,
  context: { userId: string; db: PrismaClient }
): Promise<AssetManagerResult> {
  try {
    console.log(`[asset_manager] Operation: ${params.operation}`);

    if (!params.operation) {
      return {
        success: false,
        message: 'operation is required',
      };
    }

    switch (params.operation) {
      case 'save':
        return await saveAsset(params, context);
      case 'load':
        return await loadAsset(params, context);
      case 'list':
        return await listAssets(params, context);
      case 'delete':
        return await deleteAsset(params, context);
      default:
        return {
          success: false,
          message: `Unknown operation: ${params.operation}. Valid operations: save, load, list, delete`,
        };
    }
  } catch (error) {
    console.error('[asset_manager] Error:', error);
    return {
      success: false,
      message: `Error in asset_manager: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Operation: Save Asset
// ============================================================================

async function saveAsset(
  params: AssetManagerParams,
  context: { userId: string; db: PrismaClient }
): Promise<AssetManagerResult> {
  if (!params.data) {
    return {
      success: false,
      message: 'data is required for save operation (base64 or data URL)',
    };
  }

  if (!params.type) {
    return {
      success: false,
      message: 'type is required for save operation (image, audio, video)',
    };
  }

  // Extract base64 data
  let base64Data: string;
  let mimeType: string;

  if (params.data.startsWith('data:')) {
    const match = params.data.match(/^data:([^;]+);base64,(.+)$/);
    if (match) {
      mimeType = match[1];
      base64Data = match[2];
    } else {
      return {
        success: false,
        message: 'Invalid data URL format',
      };
    }
  } else {
    // Assume raw base64
    base64Data = params.data;
    mimeType = params.type === 'image' ? 'image/png' : params.type === 'audio' ? 'audio/mp3' : 'video/mp4';
  }

  // Generate storage path
  const timestamp = Date.now();
  const randomId = Math.random().toString(36).substring(2, 9);
  const extension = getExtensionFromMimeType(mimeType);
  const fileName = `${params.type}_${timestamp}_${randomId}.${extension}`;

  let storagePath: string;
  if (params.segment_id) {
    storagePath = `segments/${params.segment_id}/${fileName}`;
  } else if (params.story_id) {
    storagePath = `stories/${params.story_id}/${fileName}`;
  } else if (params.world_id) {
    storagePath = `worlds/${params.world_id}/${fileName}`;
  } else {
    storagePath = `uploads/${context.userId}/${fileName}`;
  }

  // Upload to S3
  let assetUrl: string | undefined;
  const s3Bucket = process.env.AWS_S3_BUCKET;
  const awsRegion = process.env.AWS_REGION || 'us-east-1';

  if (s3Bucket) {
    try {
      const { S3Client, PutObjectCommand } = await import('@aws-sdk/client-s3');

      const s3Client = new S3Client({ region: awsRegion });
      const buffer = Buffer.from(base64Data, 'base64');

      await s3Client.send(
        new PutObjectCommand({
          Bucket: s3Bucket,
          Key: storagePath,
          Body: buffer,
          ContentType: mimeType,
          CacheControl: 'max-age=31536000',
        })
      );

      const cloudfrontDomain = process.env.CLOUDFRONT_DOMAIN;
      if (cloudfrontDomain) {
        assetUrl = `https://${cloudfrontDomain}/${storagePath}`;
      } else {
        assetUrl = `https://${s3Bucket}.s3.${awsRegion}.amazonaws.com/${storagePath}`;
      }

      console.log(`[asset_manager] Uploaded to S3: ${storagePath}`);
    } catch (error) {
      console.error('[asset_manager] S3 upload failed:', error);
      return {
        success: false,
        message: `S3 upload failed: ${error instanceof Error ? error.message : String(error)}`,
      };
    }
  } else {
    console.warn('[asset_manager] AWS_S3_BUCKET not configured, asset not uploaded');
  }

  // Create asset record
  const asset = await context.db.asset.create({
    data: {
      type: params.type,
      category: params.category || null,
      storagePath,
      url: assetUrl || null,
      description: params.description || null,
      metadata: params.metadata || undefined,
      generated: false,
      worldId: params.world_id || null,
      storyId: params.story_id || null,
      segmentId: params.segment_id || null,
    },
    select: {
      id: true,
      type: true,
      category: true,
      storagePath: true,
      url: true,
      description: true,
    },
  });

  return {
    success: true,
    message: `Asset saved: ${asset.id}\nType: ${asset.type}\nPath: ${asset.storagePath}`,
    asset: {
      id: asset.id,
      type: asset.type,
      category: asset.category || undefined,
      storagePath: asset.storagePath,
      url: asset.url || undefined,
      description: asset.description || undefined,
    },
  };
}

// ============================================================================
// Operation: Load Asset
// ============================================================================

async function loadAsset(
  params: AssetManagerParams,
  context: { userId: string; db: PrismaClient }
): Promise<AssetManagerResult> {
  if (!params.asset_id) {
    return {
      success: false,
      message: 'asset_id is required for load operation',
    };
  }

  const asset = await context.db.asset.findUnique({
    where: { id: params.asset_id },
    select: {
      id: true,
      type: true,
      category: true,
      storagePath: true,
      url: true,
      description: true,
      metadata: true,
    },
  });

  if (!asset) {
    return {
      success: false,
      message: `Asset not found: ${params.asset_id}`,
    };
  }

  return {
    success: true,
    message: `Asset loaded: ${asset.id}\nType: ${asset.type}\nURL: ${asset.url || 'Not available'}`,
    asset: {
      id: asset.id,
      type: asset.type,
      category: asset.category || undefined,
      storagePath: asset.storagePath,
      url: asset.url || undefined,
      description: asset.description || undefined,
    },
  };
}

// ============================================================================
// Operation: List Assets
// ============================================================================

async function listAssets(
  params: AssetManagerParams,
  context: { userId: string; db: PrismaClient }
): Promise<AssetManagerResult> {
  const where: Record<string, any> = {};

  if (params.segment_id) {
    where.segmentId = params.segment_id;
  } else if (params.story_id) {
    where.storyId = params.story_id;
  } else if (params.world_id) {
    where.worldId = params.world_id;
  }

  if (params.type) {
    where.type = params.type;
  }

  if (params.category) {
    where.category = params.category;
  }

  const assets = await context.db.asset.findMany({
    where,
    select: {
      id: true,
      type: true,
      category: true,
      storagePath: true,
      url: true,
      description: true,
    },
    orderBy: { createdAt: 'desc' },
    take: 100,
  });

  const summary =
    assets.length > 0
      ? `Found ${assets.length} assets:\n${assets.map((a) => `  - ${a.id}: ${a.type} (${a.category || 'uncategorized'})`).join('\n')}`
      : 'No assets found';

  return {
    success: true,
    message: summary,
    assets: assets.map((a) => ({
      id: a.id,
      type: a.type,
      category: a.category || undefined,
      storagePath: a.storagePath,
      url: a.url || undefined,
      description: a.description || undefined,
    })),
  };
}

// ============================================================================
// Operation: Delete Asset
// ============================================================================

async function deleteAsset(
  params: AssetManagerParams,
  context: { userId: string; db: PrismaClient }
): Promise<AssetManagerResult> {
  if (!params.asset_id) {
    return {
      success: false,
      message: 'asset_id is required for delete operation',
    };
  }

  // Find asset first
  const asset = await context.db.asset.findUnique({
    where: { id: params.asset_id },
    select: {
      id: true,
      storagePath: true,
    },
  });

  if (!asset) {
    return {
      success: false,
      message: `Asset not found: ${params.asset_id}`,
    };
  }

  // Delete from S3 if configured
  const s3Bucket = process.env.AWS_S3_BUCKET;
  const awsRegion = process.env.AWS_REGION || 'us-east-1';

  if (s3Bucket) {
    try {
      const { S3Client, DeleteObjectCommand } = await import('@aws-sdk/client-s3');

      const s3Client = new S3Client({ region: awsRegion });

      await s3Client.send(
        new DeleteObjectCommand({
          Bucket: s3Bucket,
          Key: asset.storagePath,
        })
      );

      console.log(`[asset_manager] Deleted from S3: ${asset.storagePath}`);
    } catch (error) {
      console.error('[asset_manager] S3 delete failed:', error);
      // Continue with database deletion
    }
  }

  // Delete from database
  await context.db.asset.delete({
    where: { id: params.asset_id },
  });

  return {
    success: true,
    message: `Asset deleted: ${params.asset_id}`,
  };
}

// ============================================================================
// Helper Functions
// ============================================================================

function getExtensionFromMimeType(mimeType: string): string {
  const extensions: Record<string, string> = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg',
    'image/gif': 'gif',
    'image/webp': 'webp',
    'audio/mp3': 'mp3',
    'audio/mpeg': 'mp3',
    'audio/wav': 'wav',
    'audio/ogg': 'ogg',
    'video/mp4': 'mp4',
    'video/webm': 'webm',
  };

  return extensions[mimeType] || 'bin';
}

// ============================================================================
// Tool Definition for Letta SDK
// ============================================================================

export const assetManagerTool = {
  name: 'asset_manager',
  description:
    'Manage multimedia assets (images, audio, video) stored in S3. Operations: save, load, list, delete.',
  parameters: {
    type: 'object',
    properties: {
      operation: {
        type: 'string',
        enum: ['save', 'load', 'list', 'delete'],
        description: 'Operation to perform',
      },
      asset_id: {
        type: 'string',
        description: 'Asset ID (required for load, delete)',
      },
      world_id: {
        type: 'string',
        description: 'World ID to associate/filter assets',
      },
      story_id: {
        type: 'string',
        description: 'Story ID to associate/filter assets',
      },
      segment_id: {
        type: 'string',
        description: 'Segment ID to associate/filter assets',
      },
      data: {
        type: 'string',
        description: 'Base64 data or data URL (required for save)',
      },
      type: {
        type: 'string',
        enum: ['image', 'audio', 'video'],
        description: 'Asset type (required for save)',
      },
      category: {
        type: 'string',
        enum: ['character', 'background', 'music', 'sfx', 'ui'],
        description: 'Asset category',
      },
      description: {
        type: 'string',
        description: 'Asset description',
      },
    },
    required: ['operation'],
  },
};
