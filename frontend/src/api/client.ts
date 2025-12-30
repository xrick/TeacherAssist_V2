/**
 * API Client
 *
 * Axios-based client for TeacherAssist V2 backend API
 */

import axios from 'axios'
import type {
  Template,
  TemplateListResponse,
  GenerationRequest,
  GenerationResponse,
  PresentationMetadata,
} from '@/types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 10 minutes for generation
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

/**
 * Template API
 */
export const templateAPI = {
  /**
   * List all available templates
   */
  async list(category?: string): Promise<TemplateListResponse> {
    const response = await api.get<TemplateListResponse>('/api/v1/templates', {
      params: { category },
    })
    return response.data
  },

  /**
   * Get specific template
   */
  async get(templateId: string): Promise<Template> {
    const response = await api.get<Template>(`/api/v1/templates/${templateId}`)
    return response.data
  },

  /**
   * Download template file
   */
  getDownloadUrl(templateId: string): string {
    return `${API_BASE_URL}/api/v1/templates/${templateId}/download`
  },
}

/**
 * Presentation Generation API
 */
export const generationAPI = {
  /**
   * Generate presentation (synchronous)
   */
  async generate(request: GenerationRequest): Promise<GenerationResponse> {
    const response = await api.post<GenerationResponse>('/api/v1/generate', request)
    return response.data
  },

  /**
   * Get SSE stream URL for generation
   */
  getStreamUrl(): string {
    return `${API_BASE_URL}/api/v1/generate/stream`
  },
}

/**
 * Presentation Management API
 */
export const presentationAPI = {
  /**
   * Get presentation metadata
   */
  async getMetadata(presentationId: string): Promise<PresentationMetadata> {
    const response = await api.get<PresentationMetadata>(
      `/api/v1/presentations/${presentationId}/metadata`
    )
    return response.data
  },

  /**
   * Get download URL for presentation
   */
  getDownloadUrl(presentationId: string): string {
    return `${API_BASE_URL}/api/v1/presentations/${presentationId}/download`
  },

  /**
   * Delete presentation
   */
  async delete(presentationId: string): Promise<void> {
    await api.delete(`/api/v1/presentations/${presentationId}`)
  },
}

/**
 * Health Check API
 */
export const healthAPI = {
  /**
   * Check API health
   */
  async check(): Promise<{ status: string; llm_available: boolean }> {
    const response = await api.get('/api/v1/health')
    return response.data
  },
}

export default api
