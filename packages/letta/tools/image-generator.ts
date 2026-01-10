/**
 * image_generator - Generate images using AI models (Google Gemini or OpenAI)
 *
 * Generates images from text prompts and optionally saves them to S3 as assets.
 *
 * Default Provider Selection:
 * - Google (preferred): Uses gemini-2.0-flash-exp if GOOGLE_API_KEY is set
 * - OpenAI (fallback): Uses dall-e-3 if OPENAI_API_KEY is set
 */

import type { PrismaClient } from '@deep-sci-fi/db';
import { sendStateChange } from '../websocket/manager';

// ============================================================================
// Types
// ============================================================================

export type ImageProvider = 'openai' | 'google';

export interface ImageGeneratorParams {
  prompt: string;
  provider?: ImageProvider;
  size?: '1024x1024' | '1792x1024' | '1024x1792' | '512x512' | '256x256';
  quality?: 'standard' | 'hd';
  style?: 'vivid' | 'natural';
  model?: string;
  save_as_asset?: boolean;
  world_id?: string;
  story_id?: string;
  asset_description?: string;
  category?: 'character' | 'background' | 'ui' | 'other';
}

export interface ImageGeneratorResult {
  success: boolean;
  message: string;
  imageUrl?: string;
  revisedPrompt?: string;
  asset?: {
    id: string;
    url: string;
    storagePath: string;
  };
}

// ============================================================================
// Configuration
// ============================================================================

function getDefaultProvider(): ImageProvider {
  const googleKey = process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY;
  const openaiKey = process.env.OPENAI_API_KEY;

  if (googleKey) {
    return 'google';
  } else if (openaiKey) {
    return 'openai';
  }

  return 'openai';
}

// ============================================================================
// Main Entry Point
// ============================================================================

export async function image_generator(
  params: ImageGeneratorParams,
  context: { userId: string; db: PrismaClient }
): Promise<ImageGeneratorResult> {
  try {
    console.log(
      `[image_generator] Generating image with prompt: ${params.prompt.substring(0, 50)}...`
    );

    if (!params.prompt) {
      return {
        success: false,
        message: 'prompt is required',
      };
    }

    // Validate API keys
    const googleKey = process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY;
    const openaiKey = process.env.OPENAI_API_KEY;

    if (!googleKey && !openaiKey) {
      return {
        success: false,
        message:
          'No image generation API keys configured. Set either GOOGLE_API_KEY or OPENAI_API_KEY.',
      };
    }

    const provider = params.provider || getDefaultProvider();

    // Notify frontend that image generation is starting
    if (params.world_id) {
      sendStateChange('image_generating', {
        worldId: params.world_id,
        storyId: params.story_id,
      });
    }

    // Generate image based on provider
    let imageUrl: string;
    let revisedPrompt: string | undefined;

    switch (provider) {
      case 'openai':
        ({ imageUrl, revisedPrompt } = await generateWithOpenAI(params));
        break;
      case 'google':
        ({ imageUrl } = await generateWithGoogle(params));
        break;
      default:
        return {
          success: false,
          message: `Unknown provider: ${provider}. Valid providers: openai, google`,
        };
    }

    let message = `Image generated successfully!\nProvider: ${provider}\nPrompt: ${params.prompt}`;
    if (revisedPrompt) {
      message += `\nRevised prompt: ${revisedPrompt}`;
    }

    // Optionally save as asset to S3
    let asset: ImageGeneratorResult['asset'];
    if (params.save_as_asset) {
      const saveResult = await saveAsAsset(imageUrl, params, context);
      asset = {
        id: saveResult.id,
        url: saveResult.url,
        storagePath: saveResult.storagePath,
      };
      message += `\n\nSaved as asset: ${asset.id}\nURL: ${asset.url}`;

      // Explicitly warn if S3 upload failed (image is stored as data URL instead)
      if (saveResult.s3UploadFailed) {
        message += `\n\n⚠️ WARNING: S3 upload failed - image stored as data URL only.`;
        message += `\nError: ${saveResult.s3UploadError}`;
        message += `\nThis image is NOT persisted to cloud storage. It may be lost on server restart.`;
      } else if (!process.env.AWS_S3_BUCKET) {
        message += `\n\nNote: AWS_S3_BUCKET not configured - image stored as data URL only.`;
      }
    }

    // Broadcast state change for reactive UI
    sendStateChange('image_generated', {
      assetId: asset?.id,
      assetUrl: asset?.url,
      storyId: params.story_id,
      worldId: params.world_id,
    });

    return {
      success: true,
      message,
      imageUrl,
      revisedPrompt,
      asset,
    };
  } catch (error) {
    console.error('[image_generator] Error:', error);
    return {
      success: false,
      message: `Error generating image: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// OpenAI Generation
// ============================================================================

async function generateWithOpenAI(
  params: ImageGeneratorParams
): Promise<{ imageUrl: string; revisedPrompt?: string }> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error('OPENAI_API_KEY environment variable not set');
  }

  const size = params.size || '1024x1024';
  const model = params.model || 'dall-e-3';

  const requestBody: Record<string, any> = {
    model,
    prompt: params.prompt,
    n: 1,
    size,
    response_format: 'b64_json',
  };

  if (model === 'dall-e-3') {
    requestBody.quality = params.quality || 'standard';
    requestBody.style = params.style || 'vivid';
  }

  const response = await fetch('https://api.openai.com/v1/images/generations', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenAI API error (${response.status}): ${error}`);
  }

  const data = (await response.json()) as {
    data: Array<{
      b64_json?: string;
      url?: string;
      revised_prompt?: string;
    }>;
  };

  if (!data.data || data.data.length === 0) {
    throw new Error('No image returned from OpenAI');
  }

  const imageData = data.data[0];
  if (!imageData) {
    throw new Error('No image data returned from OpenAI');
  }

  let imageUrl: string;
  if (imageData.b64_json) {
    imageUrl = `data:image/png;base64,${imageData.b64_json}`;
  } else if (imageData.url) {
    const imgResponse = await fetch(imageData.url);
    const imgBuffer = await imgResponse.arrayBuffer();
    const base64 = Buffer.from(imgBuffer).toString('base64');
    imageUrl = `data:image/png;base64,${base64}`;
  } else {
    throw new Error('No image data in response');
  }

  return {
    imageUrl,
    revisedPrompt: imageData.revised_prompt,
  };
}

// ============================================================================
// Google Gemini Generation
// ============================================================================

async function generateWithGoogle(
  params: ImageGeneratorParams
): Promise<{ imageUrl: string }> {
  const apiKey = process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error('GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set');
  }

  // Use Gemini 2.0 Flash for image generation
  const modelName = params.model || 'gemini-2.0-flash-exp';

  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${modelName}:generateContent?key=${apiKey}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contents: [
          {
            parts: [
              {
                text: params.prompt,
              },
            ],
          },
        ],
        generationConfig: {
          responseModalities: ['TEXT', 'IMAGE'],
        },
      }),
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Google API error (${response.status}): ${error}`);
  }

  const data = await response.json();

  if (!data.candidates || data.candidates.length === 0) {
    throw new Error('No image generated by Google');
  }

  const candidate = data.candidates[0];
  if (
    !candidate ||
    !candidate.content ||
    !candidate.content.parts ||
    candidate.content.parts.length === 0
  ) {
    throw new Error('No image data in response');
  }

  // Find the inline data part with image
  const imagePart = candidate.content.parts.find(
    (part: any) => part.inlineData?.mimeType?.startsWith('image/')
  );

  if (!imagePart || !imagePart.inlineData) {
    throw new Error('No image data found in response');
  }

  const base64Data = imagePart.inlineData.data;
  const mimeType = imagePart.inlineData.mimeType || 'image/png';

  return {
    imageUrl: `data:${mimeType};base64,${base64Data}`,
  };
}

// ============================================================================
// Save as Asset (S3)
// ============================================================================

async function saveAsAsset(
  imageUrl: string,
  params: ImageGeneratorParams,
  context: { userId: string; db: PrismaClient }
): Promise<{
  id: string;
  url: string;
  storagePath: string;
  s3UploadFailed: boolean;
  s3UploadError?: string;
}> {
  // Extract base64 data
  let base64Data: string;
  let mimeType = 'image/png';

  if (imageUrl.startsWith('data:')) {
    const match = imageUrl.match(/^data:([^;]+);base64,(.+)$/);
    if (match) {
      mimeType = match[1];
      base64Data = match[2];
    } else {
      throw new Error('Invalid data URL format');
    }
  } else {
    // Fetch and convert to base64
    const response = await fetch(imageUrl);
    const buffer = await response.arrayBuffer();
    base64Data = Buffer.from(buffer).toString('base64');
  }

  // Generate unique storage path
  const timestamp = Date.now();
  const randomId = Math.random().toString(36).substring(2, 9);
  const extension = mimeType === 'image/png' ? 'png' : 'jpg';
  const fileName = `img_${timestamp}_${randomId}.${extension}`;

  let storagePath: string;
  if (params.story_id) {
    storagePath = `stories/${params.story_id}/${fileName}`;
  } else if (params.world_id) {
    storagePath = `worlds/${params.world_id}/${fileName}`;
  } else {
    storagePath = `generated/${context.userId}/${fileName}`;
  }

  // Upload to S3 if configured
  let assetUrl = imageUrl; // Fallback to data URL
  let s3UploadFailed = false;
  let s3UploadError: string | undefined;
  const s3Bucket = process.env.AWS_S3_BUCKET;
  const awsRegion = process.env.AWS_REGION || 'us-east-1';

  if (s3Bucket) {
    try {
      // Dynamic import to avoid issues when AWS SDK isn't needed
      const { S3Client, PutObjectCommand } = await import('@aws-sdk/client-s3');

      const s3Client = new S3Client({ region: awsRegion });

      const buffer = Buffer.from(base64Data, 'base64');

      await s3Client.send(
        new PutObjectCommand({
          Bucket: s3Bucket,
          Key: storagePath,
          Body: buffer,
          ContentType: mimeType,
          CacheControl: 'max-age=31536000', // 1 year cache
        })
      );

      // Use CloudFront URL if available, otherwise S3 URL
      const cloudfrontDomain = process.env.CLOUDFRONT_DOMAIN;
      if (cloudfrontDomain) {
        assetUrl = `https://${cloudfrontDomain}/${storagePath}`;
      } else {
        assetUrl = `https://${s3Bucket}.s3.${awsRegion}.amazonaws.com/${storagePath}`;
      }

      console.log(`[image_generator] Uploaded to S3: ${storagePath}`);
    } catch (error) {
      console.error('[image_generator] S3 upload failed:', error);
      s3UploadFailed = true;
      s3UploadError = error instanceof Error ? error.message : String(error);
      // Continue with data URL fallback but track the failure
    }
  } else {
    console.warn('[image_generator] AWS_S3_BUCKET not configured, using data URL');
  }

  // Create asset record in database
  const asset = await context.db.asset.create({
    data: {
      type: 'image',
      category: params.category || 'other',
      storagePath,
      url: assetUrl,
      description: params.asset_description || `Generated: ${params.prompt.substring(0, 100)}`,
      generated: true,
      prompt: params.prompt,
      worldId: params.world_id || null,
      storyId: params.story_id || null,
    },
    select: {
      id: true,
      url: true,
      storagePath: true,
    },
  });

  console.log(`[image_generator] Asset created: ${asset.id}`);

  return {
    id: asset.id,
    url: asset.url || assetUrl,
    storagePath: asset.storagePath,
    s3UploadFailed,
    s3UploadError,
  };
}

// ============================================================================
// Tool Definition for Letta SDK
// ============================================================================

export const imageGeneratorTool = {
  name: 'image_generator',
  description:
    'Generate images using AI (Google Gemini or OpenAI DALL-E). Can save images as assets to S3.',
  parameters: {
    type: 'object',
    properties: {
      prompt: {
        type: 'string',
        description: 'Text prompt describing the image to generate',
      },
      provider: {
        type: 'string',
        enum: ['openai', 'google'],
        description: 'Image generation provider (default: auto-detect based on available API keys)',
      },
      size: {
        type: 'string',
        enum: ['1024x1024', '1792x1024', '1024x1792', '512x512', '256x256'],
        description: 'Image size (default: 1024x1024)',
      },
      quality: {
        type: 'string',
        enum: ['standard', 'hd'],
        description: 'Image quality for DALL-E (default: standard)',
      },
      style: {
        type: 'string',
        enum: ['vivid', 'natural'],
        description: 'Image style for DALL-E (default: vivid)',
      },
      save_as_asset: {
        type: 'boolean',
        description: 'Save generated image as an asset in S3 (default: false)',
      },
      world_id: {
        type: 'string',
        description: 'World ID to associate the asset with',
      },
      story_id: {
        type: 'string',
        description: 'Story ID to associate the asset with',
      },
      asset_description: {
        type: 'string',
        description: 'Description for the saved asset',
      },
      category: {
        type: 'string',
        enum: ['character', 'background', 'ui', 'other'],
        description: 'Asset category (default: other)',
      },
    },
    required: ['prompt'],
  },
};
