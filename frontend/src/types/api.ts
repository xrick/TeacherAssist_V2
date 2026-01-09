/**
 * API Type Definitions
 */

export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  preview_image: string | null;
  tags: string[];
  created_at: string;
}

export interface TemplateListResponse {
  templates: Template[];
  total: number;
  categories: string[];
}

export interface GenerationRequest {
  markdown_content: string;
  title?: string;
  author?: string;
  template?: string;
  audience?: string;
  tone?: string;
  slide_count?: number;
}

export interface GenerationResponse {
  success: boolean;
  message: string;
  presentation_id: string;
  slide_count: number;
  download_url: string;
  metadata: Record<string, any>;
}

export interface ProgressUpdate {
  stage: string;
  progress: number;
  message: string;
}

export interface SSEMessage {
  event: "progress" | "complete" | "error";
  data: ProgressUpdate | GenerationResponse | { error: string };
}

export interface PresentationMetadata {
  id: string;
  title: string;
  author: string;
  template: string;
  slide_count: number;
  created_at: string;
  file_path: string;
  file_size: number;
}

// Pexels API Types
export interface PexelsImageSrc {
  original: string;
  large2x: string;
  large: string;
  medium: string;
  small: string;
  portrait: string;
  landscape: string;
  tiny: string;
}

export interface PexelsImage {
  id: number;
  width: number;
  height: number;
  url: string;
  photographer: string;
  photographer_url: string;
  avg_color: string;
  src: PexelsImageSrc;
  alt: string;
  attribution: string;
}

export interface ImageSearchRequest {
  keyword: string;
  per_page?: number;
  page?: number;
  orientation?: "landscape" | "portrait" | "square";
}

export interface ImageSearchResponse {
  total_results: number;
  page: number;
  per_page: number;
  photos: PexelsImage[];
  has_next: boolean;
}

export interface ImageDownloadRequest {
  image_id: number;
  keyword: string;
  size?: "original" | "large2x" | "large" | "medium" | "small";
}

export interface ImageDownloadResponse {
  success: boolean;
  image_id: number;
  keyword: string;
  file_path: string;
  photographer: string;
  attribution: string;
  cached_at: string;
  expires_at: string;
}

export interface AIKeywordRequest {
  course_title: string;
  slide_title: string;
  slide_content?: string;
  max_keywords?: number;
}

export interface AIKeywordResponse {
  keywords: string[];
  primary_keyword: string;
  language: string;
  generated_at: string;
}

export interface CacheStats {
  total_images: number;
  total_size_bytes: number;
  total_size_mb: number;
  keywords_count: number;
  oldest_image: string | null;
  newest_image: string | null;
}

export interface SlideImageUpdateRequest {
  presentation_id: string;
  slide_index: number;
  image_id: number;
  keyword: string;
  position?:
    | "auto"
    | "left"
    | "right"
    | "top"
    | "bottom"
    | "background"
    | "center";
}

// Teaching Script Types
export interface InteractionQA {
  question: string;
  expected_answers: string[];
}

export interface SlideScript {
  slide_index: number;
  slide_title: string;
  estimated_minutes: number;
  lecture_content: string;
  teaching_tips: string[];
  interaction_qa: InteractionQA[];
  transition: string;
}

export interface PresentationScript {
  presentation_id: string;
  title: string;
  total_minutes: number;
  scripts: SlideScript[];
  generated_at: string;
  last_edited_at: string;
}

export interface SlideScriptUpdateRequest {
  lecture_content?: string;
  teaching_tips?: string[];
  interaction_qa?: InteractionQA[];
  transition?: string;
  estimated_minutes?: number;
}

export interface PresentationScriptUpdateRequest {
  scripts: SlideScriptUpdateRequest[];
}

export interface RegenerateScriptRequest {
  style?: "conversational" | "formal" | "casual";
  slide_indices?: number[];
  target_total_minutes?: number;
}

export interface TimeAllocationRequest {
  target_total_minutes?: number;
  slide_times?: number[];
}

export interface TimeAllocationResponse {
  success: boolean;
  total_minutes: number;
  slide_times: number[];
  message: string;
}

export type ScriptStyle = "conversational" | "formal" | "casual";
