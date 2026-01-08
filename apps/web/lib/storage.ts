/**
 * Storage service for assets (images, audio, etc.)
 * Uses AWS S3 with CloudFront CDN
 */

import {
  S3Client,
  PutObjectCommand,
  DeleteObjectCommand,
  GetObjectCommand,
} from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

// S3 client singleton
let s3Client: S3Client | null = null;

function getS3Client(): S3Client {
  if (!s3Client) {
    s3Client = new S3Client({
      region: process.env.AWS_REGION || 'us-east-1',
    });
  }
  return s3Client;
}

export class StorageService {
  private bucket: string;
  private cloudfrontDomain: string | null;

  constructor() {
    this.bucket = process.env.AWS_S3_BUCKET || '';
    this.cloudfrontDomain = process.env.CLOUDFRONT_DOMAIN || null;
  }

  /**
   * Check if storage is configured
   */
  isConfigured(): boolean {
    return !!this.bucket;
  }

  /**
   * Upload file to S3
   * @returns S3 key and CDN URL
   */
  async uploadFile(
    file: Buffer | Uint8Array,
    key: string,
    contentType: string
  ): Promise<{ key: string; url: string }> {
    if (!this.isConfigured()) {
      console.warn('Storage service not configured - using placeholder');
      return { key, url: `/api/assets/${key}` };
    }

    const s3 = getS3Client();
    await s3.send(
      new PutObjectCommand({
        Bucket: this.bucket,
        Key: key,
        Body: file,
        ContentType: contentType,
        CacheControl: 'public, max-age=31536000',
      })
    );

    return {
      key,
      url: this.getPublicUrl(key),
    };
  }

  /**
   * Generate presigned URL for direct upload from client
   * Valid for 1 hour
   */
  async getPresignedUploadUrl(
    key: string,
    contentType: string
  ): Promise<string> {
    if (!this.isConfigured()) {
      console.warn('Storage service not configured - using placeholder');
      return `/api/upload/${key}`;
    }

    const s3 = getS3Client();
    const command = new PutObjectCommand({
      Bucket: this.bucket,
      Key: key,
      ContentType: contentType,
    });

    return getSignedUrl(s3, command, { expiresIn: 3600 });
  }

  /**
   * Generate presigned URL for reading private assets
   * Valid for 1 hour
   */
  async getPresignedDownloadUrl(key: string): Promise<string> {
    if (!this.isConfigured()) {
      return `/api/assets/${key}`;
    }

    const s3 = getS3Client();
    const command = new GetObjectCommand({
      Bucket: this.bucket,
      Key: key,
    });

    return getSignedUrl(s3, command, { expiresIn: 3600 });
  }

  /**
   * Get public URL for an asset (via CloudFront CDN)
   */
  getPublicUrl(key: string): string {
    if (this.cloudfrontDomain) {
      return `https://${this.cloudfrontDomain}/${key}`;
    }
    // Fallback to S3 URL if CloudFront not configured
    if (this.bucket) {
      return `https://${this.bucket}.s3.amazonaws.com/${key}`;
    }
    // Local dev fallback
    return `/api/assets/${key}`;
  }

  /**
   * Delete file from S3
   */
  async deleteFile(key: string): Promise<void> {
    if (!this.isConfigured()) {
      console.warn('Storage service not configured - skipping deletion');
      return;
    }

    const s3 = getS3Client();
    await s3.send(
      new DeleteObjectCommand({
        Bucket: this.bucket,
        Key: key,
      })
    );
  }

  /**
   * Generate a unique key for an asset
   */
  generateKey(
    category: 'worlds' | 'stories' | 'segments' | 'users',
    entityId: string,
    filename: string
  ): string {
    const timestamp = Date.now();
    const safeFilename = filename.replace(/[^a-zA-Z0-9.-]/g, '_');
    return `${category}/${entityId}/${timestamp}-${safeFilename}`;
  }
}

export const storage = new StorageService();
