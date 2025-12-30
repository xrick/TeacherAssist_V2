/**
 * API Type Definitions
 */

export interface Template {
  id: string
  name: string
  description: string
  category: string
  preview_image: string | null
  tags: string[]
  created_at: string
}

export interface TemplateListResponse {
  templates: Template[]
  total: number
  categories: string[]
}

export interface GenerationRequest {
  markdown_content: string
  title?: string
  author?: string
  template?: string
  audience?: string
  tone?: string
}

export interface GenerationResponse {
  success: boolean
  message: string
  presentation_id: string
  slide_count: number
  download_url: string
  metadata: Record<string, any>
}

export interface ProgressUpdate {
  stage: string
  progress: number
  message: string
}

export interface SSEMessage {
  event: 'progress' | 'complete' | 'error'
  data: ProgressUpdate | GenerationResponse | { error: string }
}

export interface PresentationMetadata {
  id: string
  title: string
  author: string
  template: string
  slide_count: number
  created_at: string
  file_path: string
  file_size: number
}
