/**
 * Pexels API Client
 *
 * API client for Pexels image search and management
 */

import axios from "axios";
import type {
  ImageSearchResponse,
  ImageDownloadRequest,
  ImageDownloadResponse,
  AIKeywordRequest,
  AIKeywordResponse,
  CacheStats,
  PexelsImage,
} from "@/types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 1 minute for image operations
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Pexels Image API
 */
export const pexelsAPI = {
  /**
   * Search for images on Pexels
   */
  async search(
    keyword: string,
    options?: {
      per_page?: number;
      page?: number;
      orientation?: "landscape" | "portrait" | "square";
    },
  ): Promise<ImageSearchResponse> {
    const params = new URLSearchParams({
      keyword,
      ...(options?.per_page && { per_page: options.per_page.toString() }),
      ...(options?.page && { page: options.page.toString() }),
      ...(options?.orientation && { orientation: options.orientation }),
    });

    const response = await api.get<ImageSearchResponse>(
      `/api/v1/pexels/search?${params}`,
    );
    return response.data;
  },

  /**
   * Download and cache an image
   */
  async download(
    request: ImageDownloadRequest,
  ): Promise<ImageDownloadResponse> {
    const response = await api.post<ImageDownloadResponse>(
      "/api/v1/pexels/download",
      request,
    );
    return response.data;
  },

  /**
   * Generate AI keywords for image search
   */
  async generateKeywords(
    request: AIKeywordRequest,
  ): Promise<AIKeywordResponse> {
    const response = await api.post<AIKeywordResponse>(
      "/api/v1/pexels/ai-keywords",
      request,
    );
    return response.data;
  },

  /**
   * Get cache statistics
   */
  async getCacheStats(): Promise<CacheStats> {
    const response = await api.get<CacheStats>("/api/v1/pexels/cache/stats");
    return response.data;
  },

  /**
   * Get cached images for a keyword
   */
  async getCachedImages(keyword: string): Promise<PexelsImage[]> {
    const response = await api.get<PexelsImage[]>(
      `/api/v1/pexels/cache/keyword/${encodeURIComponent(keyword)}`,
    );
    return response.data;
  },

  /**
   * Clean up expired cache entries
   */
  async cleanupCache(): Promise<{ success: boolean; removed_count: number }> {
    const response = await api.post<{
      success: boolean;
      removed_count: number;
    }>("/api/v1/pexels/cache/cleanup");
    return response.data;
  },

  /**
   * Clear all cached images
   */
  async clearCache(): Promise<{ success: boolean; removed_count: number }> {
    const response = await api.delete<{
      success: boolean;
      removed_count: number;
    }>("/api/v1/pexels/cache/clear");
    return response.data;
  },

  /**
   * Get thumbnail URL for preview (use small size)
   */
  getThumbnailUrl(image: PexelsImage): string {
    return image.src.medium;
  },

  /**
   * Get preview URL (use large size)
   */
  getPreviewUrl(image: PexelsImage): string {
    return image.src.large;
  },
};

export default pexelsAPI;
