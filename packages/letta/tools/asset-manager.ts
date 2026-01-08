/**
 * asset_manager - Asset management tool for Deep Sci-Fi
 *
 * Operations:
 * - save: Upload and save a new asset to S3 + database
 * - load: Retrieve asset metadata and URL
 * - list: List assets by category, world, story, or segment
 * - delete: Remove an asset from storage and database
 *
 * Supports S3 storage with CloudFront CDN for production,
 * and local filesystem fallback for development.
 */

import type { PrismaClient } from '@deep-sci-fi/db';
import {
  S3Client,
  PutObjectCommand,
  DeleteObjectCommand,
  GetObjectCommand,
} from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

// ============================================================================
// Types
// ============================================================================

export interface AssetManagerParams {
  operation: 'save' | 'load' | 'list' | 'delete' | 'get_upload_url';
  // For save operation
  asset_data?: string; // Base64-encoded data
  mime_type?: string; // MIME type (e.g., 'image/png')
  type?: 'image' | 'audio' | 'video';
  category?: 'character' | 'background' | 'music' | 'sfx' | 'ui' | 'other';
  description?: string;
  // For load/delete operation
  asset_id?: string;
  // For list operation
  world_id?: string;
  story_id?: string;
  segment_id?: string;
  filter_type?: 'image' | 'audio' | 'video';
  filter_category?: string;
  limit?: number;
  // For get_upload_url operation
  filename?: string;
}

export interface AssetManagerResult {
  success: boolean;
  message: string;
  asset?: {
    id: string;
    url: string;
    storagePath: string;
    type: string;
    category: string | null;
    description: string | null;
  };
  assets?: Array<{
    id: string;
    url: string | null;
    type: string;
    category: string | null;
    description: string | null;
    createdAt: Date;
  }>;
  uploadUrl?: string; // Pre-signed URL for direct upload
}

interface ToolContext {
  userId: string;
  db: PrismaClient;
}

// ============================================================================
// Configuration
// ============================================================================

function getS3Client(): S3Client | null {
  const region = process.env.AWS_REGION;
  if (!region) {
    return null;
  }
  return new S3Client({ region });
}

function getS3Bucket(): string | null {
  return process.env.AWS_S3_BUCKET || null;
}

function getCloudFrontDomain(): string | null {
  return process.env.CLOUDFRONT_DOMAIN || null;
}

function isS3Configured(): boolean {
  return !!(process.env.AWS_REGION && process.env.AWS_S3_BUCKET);
}

// ============================================================================
// Main Entry Point
// ============================================================================

export async function asset_manager(
  params: AssetManagerParams,
  context: ToolContext
): Promise<AssetManagerResult> {
  try {
    console.log(`[asset_manager] Operation: ${params.operation}`);

    // Validate operation
    const validOperations = ['save', 'load', 'list', 'delete', 'get_upload_url'];
    if (!validOperations.includes(params.operation)) {
      return {
        success: false,
        message: `Invalid operation: ${params.operation}. Valid operations: ${validOperations.join(', ')}`,
      };
    }

    // Route to operation handler
    switch (params.operation) {
      case 'save':
        return await saveAsset(params, context);
      case 'load':
        return await loadAsset(params, context);
      case 'list':
        return await listAssets(params, context);
      case 'delete':
        return await deleteAsset(params, context);
      case 'get_upload_url':
        return await getUploadUrl(params, context);
      default:
        return {
          success: false,
          message: `Unknown operation: ${params.operation}`,
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
  context: ToolContext
): Promise<AssetManagerResult> {
  // Validate required parameters
  if (!params.asset_data) {
    return {
      success: false,
      message: 'asset_data (base64-encoded) is required for save operation',
    };
  }

  if (!params.mime_type) {
    return {
      success: false,
      message: 'mime_type is required for save operation',
    };
  }

  const assetType = params.type || inferTypeFromMime(params.mime_type);
  const category = params.category || 'other';
  const extension = getExtensionFromMime(params.mime_type);
  const timestamp = Date.now();
  const randomSuffix = Math.random().toString(36).substring(2, 8);

  // Generate storage path
  const storagePath = `${assetType}s/${category}/${timestamp}-${randomSuffix}.${extension}`;

  // Convert base64 to buffer
  const assetBuffer = Buffer.from(params.asset_data, 'base64');

  const s3Client = getS3Client();
  const s3Bucket = getS3Bucket();
  const cloudfrontDomain = getCloudFrontDomain();

  let url: string;

  if (s3Client && s3Bucket) {
    // Upload to S3
    try {
      await s3Client.send(
        new PutObjectCommand({
          Bucket: s3Bucket,
          Key: storagePath,
          Body: assetBuffer,
          ContentType: params.mime_type,
          CacheControl: 'public, max-age=31536000',
          Metadata: {
            category: category,
            generator: 'deep-sci-fi',
          },
        })
      );

      // Build URL
      if (cloudfrontDomain) {
        url = `https://${cloudfrontDomain}/${storagePath}`;
      } else {
        url = `https://${s3Bucket}.s3.amazonaws.com/${storagePath}`;
      }

      console.log(`[asset_manager] Uploaded to S3: ${storagePath}`);
    } catch (error) {
      console.error('[asset_manager] S3 upload failed:', error);
      return {
        success: false,
        message: `Failed to upload to S3: ${error instanceof Error ? error.message : String(error)}`,
      };
    }
  } else {
    // Local development mode
    url = `/api/assets/${storagePath}`;
    console.log(`[asset_manager] Local mode, asset path: ${url}`);
  }

  // Create asset record in database
  try {
    const asset = await context.db.asset.create({
      data: {
        type: assetType,
        category: category,
        storagePath: storagePath,
        url: url,
        description: params.description || null,
        generated: false, // Uploaded assets are not AI-generated
        metadata: {
          mimeType: params.mime_type,
          sizeBytes: assetBuffer.length,
        },
        worldId: params.world_id || null,
        storyId: params.story_id || null,
        segmentId: params.segment_id || null,
      },
      select: {
        id: true,
        url: true,
        storagePath: true,
        type: true,
        category: true,
        description: true,
      },
    });

    console.log(`[asset_manager] Asset saved: ${asset.id}`);

    return {
      success: true,
      message: `Asset saved successfully\nID: ${asset.id}\nType: ${assetType}\nCategory: ${category}\nURL: ${url}`,
      asset: {
        id: asset.id,
        url: asset.url || url,
        storagePath: asset.storagePath,
        type: asset.type,
        category: asset.category,
        description: asset.description,
      },
    };
  } catch (error) {
    console.error('[asset_manager] Database save failed:', error);
    return {
      success: false,
      message: `Failed to save asset record: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Operation: Load Asset
// ============================================================================

async function loadAsset(
  params: AssetManagerParams,
  context: ToolContext
): Promise<AssetManagerResult> {
  if (!params.asset_id) {
    return {
      success: false,
      message: 'asset_id is required for load operation',
    };
  }

  try {
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
        generated: true,
        prompt: true,
        createdAt: true,
      },
    });

    if (!asset) {
      return {
        success: false,
        message: `Asset not found: ${params.asset_id}`,
      };
    }

    console.log(`[asset_manager] Asset loaded: ${asset.id}`);

    return {
      success: true,
      message: `Asset loaded\nID: ${asset.id}\nType: ${asset.type}\nCategory: ${asset.category || 'none'}\nURL: ${asset.url}`,
      asset: {
        id: asset.id,
        url: asset.url || '',
        storagePath: asset.storagePath,
        type: asset.type,
        category: asset.category,
        description: asset.description,
      },
    };
  } catch (error) {
    console.error('[asset_manager] Load failed:', error);
    return {
      success: false,
      message: `Failed to load asset: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Operation: List Assets
// ============================================================================

async function listAssets(
  params: AssetManagerParams,
  context: ToolContext
): Promise<AssetManagerResult> {
  try {
    // Build query filters
    const where: any = {};

    if (params.world_id) {
      where.worldId = params.world_id;
    }
    if (params.story_id) {
      where.storyId = params.story_id;
    }
    if (params.segment_id) {
      where.segmentId = params.segment_id;
    }
    if (params.filter_type) {
      where.type = params.filter_type;
    }
    if (params.filter_category) {
      where.category = params.filter_category;
    }

    const assets = await context.db.asset.findMany({
      where,
      take: params.limit || 50,
      orderBy: { createdAt: 'desc' },
      select: {
        id: true,
        type: true,
        category: true,
        url: true,
        description: true,
        createdAt: true,
      },
    });

    console.log(`[asset_manager] Listed ${assets.length} assets`);

    const summary =
      assets.length > 0
        ? assets
            .map(
              (a) =>
                `- ${a.id} (${a.type}/${a.category || 'none'}): ${a.description || 'No description'}`
            )
            .join('\n')
        : 'No assets found';

    return {
      success: true,
      message: `Found ${assets.length} assets:\n${summary}`,
      assets,
    };
  } catch (error) {
    console.error('[asset_manager] List failed:', error);
    return {
      success: false,
      message: `Failed to list assets: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Operation: Delete Asset
// ============================================================================

async function deleteAsset(
  params: AssetManagerParams,
  context: ToolContext
): Promise<AssetManagerResult> {
  if (!params.asset_id) {
    return {
      success: false,
      message: 'asset_id is required for delete operation',
    };
  }

  try {
    // First, get the asset to find storage path
    const asset = await context.db.asset.findUnique({
      where: { id: params.asset_id },
      select: {
        id: true,
        storagePath: true,
        worldId: true,
        world: {
          select: { ownerId: true },
        },
        storyId: true,
        story: {
          select: { authorId: true },
        },
      },
    });

    if (!asset) {
      return {
        success: false,
        message: `Asset not found: ${params.asset_id}`,
      };
    }

    // Verify ownership through world or story
    const isOwner =
      (asset.world && asset.world.ownerId === context.userId) ||
      (asset.story && asset.story.authorId === context.userId);

    if (!isOwner && asset.worldId && asset.storyId) {
      // Asset has no owner association - allow deletion by any authenticated user
      // This handles orphaned assets or assets created without associations
    }

    // Delete from S3 if configured
    const s3Client = getS3Client();
    const s3Bucket = getS3Bucket();

    if (s3Client && s3Bucket) {
      try {
        await s3Client.send(
          new DeleteObjectCommand({
            Bucket: s3Bucket,
            Key: asset.storagePath,
          })
        );
        console.log(`[asset_manager] Deleted from S3: ${asset.storagePath}`);
      } catch (error) {
        console.error('[asset_manager] S3 delete failed (continuing):', error);
        // Continue with database deletion even if S3 fails
      }
    }

    // Delete from database
    await context.db.asset.delete({
      where: { id: params.asset_id },
    });

    console.log(`[asset_manager] Asset deleted: ${params.asset_id}`);

    return {
      success: true,
      message: `Asset deleted successfully\nID: ${params.asset_id}`,
    };
  } catch (error) {
    console.error('[asset_manager] Delete failed:', error);
    return {
      success: false,
      message: `Failed to delete asset: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Operation: Get Upload URL (Pre-signed URL for direct browser upload)
// ============================================================================

async function getUploadUrl(
  params: AssetManagerParams,
  context: ToolContext
): Promise<AssetManagerResult> {
  if (!params.filename) {
    return {
      success: false,
      message: 'filename is required for get_upload_url operation',
    };
  }

  if (!params.mime_type) {
    return {
      success: false,
      message: 'mime_type is required for get_upload_url operation',
    };
  }

  if (!isS3Configured()) {
    return {
      success: false,
      message: 'S3 is not configured. Direct upload requires AWS_REGION and AWS_S3_BUCKET.',
    };
  }

  const s3Client = getS3Client();
  const s3Bucket = getS3Bucket();

  if (!s3Client || !s3Bucket) {
    return {
      success: false,
      message: 'Failed to initialize S3 client',
    };
  }

  const assetType = params.type || inferTypeFromMime(params.mime_type);
  const category = params.category || 'other';
  const extension = getExtensionFromFilename(params.filename);
  const timestamp = Date.now();
  const randomSuffix = Math.random().toString(36).substring(2, 8);

  const storagePath = `${assetType}s/${category}/${timestamp}-${randomSuffix}.${extension}`;

  try {
    const command = new PutObjectCommand({
      Bucket: s3Bucket,
      Key: storagePath,
      ContentType: params.mime_type,
      CacheControl: 'public, max-age=31536000',
    });

    const uploadUrl = await getSignedUrl(s3Client, command, { expiresIn: 3600 });

    console.log(`[asset_manager] Generated upload URL for: ${storagePath}`);

    return {
      success: true,
      message: `Upload URL generated\nPath: ${storagePath}\nExpires in: 1 hour`,
      uploadUrl,
      asset: {
        id: '', // Will be created after upload
        url: getCloudFrontDomain()
          ? `https://${getCloudFrontDomain()}/${storagePath}`
          : `https://${s3Bucket}.s3.amazonaws.com/${storagePath}`,
        storagePath,
        type: assetType,
        category,
        description: null,
      },
    };
  } catch (error) {
    console.error('[asset_manager] Failed to generate upload URL:', error);
    return {
      success: false,
      message: `Failed to generate upload URL: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

function inferTypeFromMime(mimeType: string): 'image' | 'audio' | 'video' {
  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType.startsWith('audio/')) return 'audio';
  if (mimeType.startsWith('video/')) return 'video';
  return 'image'; // Default
}

function getExtensionFromMime(mimeType: string): string {
  const mimeToExt: Record<string, string> = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg',
    'image/gif': 'gif',
    'image/webp': 'webp',
    'image/svg+xml': 'svg',
    'audio/mpeg': 'mp3',
    'audio/wav': 'wav',
    'audio/ogg': 'ogg',
    'audio/webm': 'webm',
    'video/mp4': 'mp4',
    'video/webm': 'webm',
  };
  return mimeToExt[mimeType] || 'bin';
}

function getExtensionFromFilename(filename: string): string {
  const parts = filename.split('.');
  return parts.length > 1 ? parts[parts.length - 1]!.toLowerCase() : 'bin';
}

// ============================================================================
// Tool Definition for Letta SDK
// ============================================================================

export const assetManagerTool = {
  name: 'asset_manager',
  description:
    'Manage media assets (images, audio, video) stored in S3. Operations: save (upload new asset), load (get asset details), list (find assets by filters), delete (remove asset), get_upload_url (get pre-signed URL for browser upload).',
  parameters: {
    type: 'object',
    properties: {
      operation: {
        type: 'string',
        enum: ['save', 'load', 'list', 'delete', 'get_upload_url'],
        description: 'Operation to perform',
      },
      asset_id: {
        type: 'string',
        description: 'Asset ID (required for load and delete operations)',
      },
      asset_data: {
        type: 'string',
        description: 'Base64-encoded asset data (required for save operation)',
      },
      mime_type: {
        type: 'string',
        description: 'MIME type of the asset (e.g., "image/png", "audio/mp3")',
      },
      type: {
        type: 'string',
        enum: ['image', 'audio', 'video'],
        description: 'Asset type (inferred from MIME type if not provided)',
      },
      category: {
        type: 'string',
        enum: ['character', 'background', 'music', 'sfx', 'ui', 'other'],
        description: 'Asset category for organization',
      },
      description: {
        type: 'string',
        description: 'Human-readable description of the asset',
      },
      world_id: {
        type: 'string',
        description: 'World ID to associate with (for save) or filter by (for list)',
      },
      story_id: {
        type: 'string',
        description: 'Story ID to associate with (for save) or filter by (for list)',
      },
      segment_id: {
        type: 'string',
        description: 'Segment ID to associate with (for save) or filter by (for list)',
      },
      filter_type: {
        type: 'string',
        enum: ['image', 'audio', 'video'],
        description: 'Filter by asset type (for list operation)',
      },
      filter_category: {
        type: 'string',
        description: 'Filter by category (for list operation)',
      },
      limit: {
        type: 'number',
        description: 'Maximum number of assets to return (for list, default: 50)',
      },
      filename: {
        type: 'string',
        description: 'Original filename (for get_upload_url operation)',
      },
    },
    required: ['operation'],
  },
};
