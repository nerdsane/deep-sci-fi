/**
 * image_generator - AI image generation tool for Deep Sci-Fi
 *
 * Generates images using Google Gemini (preferred) or OpenAI (fallback).
 * Automatically saves generated images to S3 and creates database records.
 *
 * Providers:
 * - Google Gemini Imagen 3 (preferred): Best quality, conversational editing
 * - OpenAI DALL-E 3 (fallback): Alternative provider
 */

import type { PrismaClient } from '@deep-sci-fi/db';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';

// ============================================================================
// Types
// ============================================================================

export interface ImageGeneratorParams {
  prompt: string;
  category?: 'character' | 'background' | 'scene' | 'object' | 'ui' | 'other';
  style?: string; // Style guidance (e.g., "photorealistic", "anime", "concept art")
  aspect_ratio?: '1:1' | '16:9' | '9:16' | '4:3' | '3:4';
  world_id?: string; // Associate with a world
  story_id?: string; // Associate with a story
  segment_id?: string; // Associate with a story segment
  description?: string; // Human-readable description for the asset
}

export interface ImageGeneratorResult {
  success: boolean;
  message: string;
  asset?: {
    id: string;
    url: string;
    storagePath: string;
    category: string;
    prompt: string;
  };
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

function getProvider(): 'google' | 'openai' | null {
  if (process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY) {
    return 'google';
  }
  if (process.env.OPENAI_API_KEY) {
    return 'openai';
  }
  return null;
}

// ============================================================================
// Main Entry Point
// ============================================================================

export async function image_generator(
  params: ImageGeneratorParams,
  context: ToolContext
): Promise<ImageGeneratorResult> {
  try {
    console.log(`[image_generator] Generating image with prompt: ${params.prompt.substring(0, 100)}...`);

    // Validate prompt
    if (!params.prompt || params.prompt.trim().length === 0) {
      return {
        success: false,
        message: 'prompt is required and cannot be empty',
      };
    }

    // Determine provider
    const provider = getProvider();
    if (!provider) {
      return {
        success: false,
        message: 'No image generation API key configured. Set GOOGLE_API_KEY or OPENAI_API_KEY.',
      };
    }

    // Build enhanced prompt with style
    const enhancedPrompt = buildEnhancedPrompt(params);

    // Generate image
    let imageData: { base64: string; mimeType: string };
    try {
      if (provider === 'google') {
        imageData = await generateWithGoogle(enhancedPrompt, params);
      } else {
        imageData = await generateWithOpenAI(enhancedPrompt, params);
      }
    } catch (error) {
      console.error(`[image_generator] Generation failed with ${provider}:`, error);
      return {
        success: false,
        message: `Image generation failed: ${error instanceof Error ? error.message : String(error)}`,
      };
    }

    // Save to storage and create asset record
    const asset = await saveAsset(imageData, params, context);

    console.log(`[image_generator] Image generated and saved: ${asset.id}`);

    return {
      success: true,
      message: `Image generated successfully\nAsset ID: ${asset.id}\nCategory: ${asset.category}\nURL: ${asset.url}`,
      asset,
    };
  } catch (error) {
    console.error('[image_generator] Error:', error);
    return {
      success: false,
      message: `Error in image_generator: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Prompt Building
// ============================================================================

function buildEnhancedPrompt(params: ImageGeneratorParams): string {
  const parts: string[] = [params.prompt];

  // Add style guidance
  if (params.style) {
    parts.push(`Style: ${params.style}`);
  }

  // Add category-specific enhancements
  switch (params.category) {
    case 'character':
      parts.push('Focus on the character design, personality conveyed through appearance.');
      break;
    case 'background':
      parts.push('Create an atmospheric environment suitable for storytelling.');
      break;
    case 'scene':
      parts.push('Capture the dramatic moment with compelling composition.');
      break;
  }

  return parts.join('. ');
}

// ============================================================================
// Google Gemini Image Generation
// ============================================================================

async function generateWithGoogle(
  prompt: string,
  params: ImageGeneratorParams
): Promise<{ base64: string; mimeType: string }> {
  const apiKey = process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error('GOOGLE_API_KEY or GEMINI_API_KEY is required');
  }

  // Use Imagen 3 model for high-quality image generation
  const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key=${apiKey}`;

  // Map aspect ratio to Imagen format
  const aspectRatioMap: Record<string, string> = {
    '1:1': '1:1',
    '16:9': '16:9',
    '9:16': '9:16',
    '4:3': '4:3',
    '3:4': '3:4',
  };

  const requestBody = {
    instances: [
      {
        prompt: prompt,
      },
    ],
    parameters: {
      sampleCount: 1,
      aspectRatio: aspectRatioMap[params.aspect_ratio || '1:1'] || '1:1',
      personGeneration: 'allow_adult',
      safetySetting: 'block_only_high',
    },
  };

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Imagen API error (${response.status}): ${errorText}`);
  }

  const data = await response.json();

  // Extract base64 image from response
  const predictions = data.predictions;
  if (!predictions || predictions.length === 0) {
    throw new Error('No image generated - empty predictions');
  }

  const imageBytes = predictions[0].bytesBase64Encoded;
  if (!imageBytes) {
    throw new Error('No image data in response');
  }

  return {
    base64: imageBytes,
    mimeType: 'image/png',
  };
}

// ============================================================================
// OpenAI DALL-E Image Generation
// ============================================================================

async function generateWithOpenAI(
  prompt: string,
  params: ImageGeneratorParams
): Promise<{ base64: string; mimeType: string }> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error('OPENAI_API_KEY is required');
  }

  // Map aspect ratio to DALL-E size
  const sizeMap: Record<string, string> = {
    '1:1': '1024x1024',
    '16:9': '1792x1024',
    '9:16': '1024x1792',
    '4:3': '1024x1024', // DALL-E 3 doesn't support 4:3, fallback to 1:1
    '3:4': '1024x1024', // DALL-E 3 doesn't support 3:4, fallback to 1:1
  };

  const response = await fetch('https://api.openai.com/v1/images/generations', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: 'dall-e-3',
      prompt: prompt,
      n: 1,
      size: sizeMap[params.aspect_ratio || '1:1'] || '1024x1024',
      quality: 'hd',
      response_format: 'b64_json',
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`OpenAI API error (${response.status}): ${errorText}`);
  }

  const data = await response.json();

  if (!data.data || data.data.length === 0 || !data.data[0].b64_json) {
    throw new Error('No image data in OpenAI response');
  }

  return {
    base64: data.data[0].b64_json,
    mimeType: 'image/png',
  };
}

// ============================================================================
// Asset Storage
// ============================================================================

async function saveAsset(
  imageData: { base64: string; mimeType: string },
  params: ImageGeneratorParams,
  context: ToolContext
): Promise<{
  id: string;
  url: string;
  storagePath: string;
  category: string;
  prompt: string;
}> {
  const category = params.category || 'other';
  const extension = imageData.mimeType === 'image/png' ? 'png' : 'jpg';
  const timestamp = Date.now();
  const randomSuffix = Math.random().toString(36).substring(2, 8);

  // Generate storage path
  const storagePath = `images/${category}/${timestamp}-${randomSuffix}.${extension}`;

  // Convert base64 to buffer
  const imageBuffer = Buffer.from(imageData.base64, 'base64');

  // Try S3 upload first, fall back to local storage info
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
          Body: imageBuffer,
          ContentType: imageData.mimeType,
          CacheControl: 'public, max-age=31536000',
          Metadata: {
            prompt: params.prompt.substring(0, 256), // S3 metadata has size limits
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

      console.log(`[image_generator] Uploaded to S3: ${storagePath}`);
    } catch (error) {
      console.error('[image_generator] S3 upload failed:', error);
      throw new Error(`Failed to upload to S3: ${error instanceof Error ? error.message : String(error)}`);
    }
  } else {
    // Local development mode - use API route
    url = `/api/assets/${storagePath}`;
    console.log(`[image_generator] Local mode, asset will be served from: ${url}`);
  }

  // Create asset record in database
  const asset = await context.db.asset.create({
    data: {
      type: 'image',
      category: category,
      storagePath: storagePath,
      url: url,
      description: params.description || null,
      generated: true,
      prompt: params.prompt,
      metadata: {
        aspectRatio: params.aspect_ratio || '1:1',
        style: params.style || null,
        mimeType: imageData.mimeType,
        sizeBytes: imageBuffer.length,
      },
      worldId: params.world_id || null,
      storyId: params.story_id || null,
      segmentId: params.segment_id || null,
    },
    select: {
      id: true,
      url: true,
      storagePath: true,
      category: true,
      prompt: true,
    },
  });

  return {
    id: asset.id,
    url: asset.url || url,
    storagePath: asset.storagePath,
    category: asset.category || category,
    prompt: asset.prompt || params.prompt,
  };
}

// ============================================================================
// Tool Definition for Letta SDK
// ============================================================================

export const imageGeneratorTool = {
  name: 'image_generator',
  description:
    'Generate AI images for worlds, stories, and scenes. Uses Google Imagen 3 (preferred) or OpenAI DALL-E 3. Images are automatically saved to storage and associated with the specified world/story/segment.',
  parameters: {
    type: 'object',
    properties: {
      prompt: {
        type: 'string',
        description:
          'Detailed description of the image to generate. Be specific about visual elements, composition, lighting, and mood.',
      },
      category: {
        type: 'string',
        enum: ['character', 'background', 'scene', 'object', 'ui', 'other'],
        description: 'Type of image being generated (helps with organization and prompt enhancement)',
      },
      style: {
        type: 'string',
        description:
          'Visual style guidance (e.g., "photorealistic", "anime", "concept art", "oil painting", "digital illustration")',
      },
      aspect_ratio: {
        type: 'string',
        enum: ['1:1', '16:9', '9:16', '4:3', '3:4'],
        description: 'Aspect ratio of the generated image (default: 1:1)',
      },
      world_id: {
        type: 'string',
        description: 'Database ID of the world to associate this image with',
      },
      story_id: {
        type: 'string',
        description: 'Database ID of the story to associate this image with',
      },
      segment_id: {
        type: 'string',
        description: 'Database ID of the story segment to associate this image with',
      },
      description: {
        type: 'string',
        description: 'Human-readable description for the asset (for cataloging)',
      },
    },
    required: ['prompt'],
  },
};
