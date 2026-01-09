/**
 * Teaching Script API Client
 *
 * API client for teaching script management, editing, and export
 */

import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes for script generation
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Interaction Q&A pair
 */
export interface InteractionQA {
  question: string;
  expected_answers: string[];
}

/**
 * Single slide script
 */
export interface SlideScript {
  slide_index: number;
  slide_title: string;
  estimated_minutes: number;
  lecture_content: string;
  teaching_tips: string[];
  interaction_qa: InteractionQA[];
  transition: string;
}

/**
 * Complete presentation script
 */
export interface PresentationScript {
  presentation_id: string;
  title: string;
  total_minutes: number;
  scripts: SlideScript[];
  generated_at: string;
  last_edited_at: string;
}

/**
 * Script update request for a single slide
 */
export interface SlideScriptUpdateRequest {
  lecture_content?: string;
  teaching_tips?: string[];
  interaction_qa?: InteractionQA[];
  transition?: string;
  estimated_minutes?: number;
}

/**
 * Script update request for entire presentation
 */
export interface PresentationScriptUpdateRequest {
  scripts: SlideScriptUpdateRequest[];
}

/**
 * Regenerate script request
 */
export interface RegenerateScriptRequest {
  style?: "conversational" | "formal" | "casual";
  slide_indices?: number[];
  target_total_minutes?: number;
}

/**
 * Time allocation request
 */
export interface TimeAllocationRequest {
  target_total_minutes?: number;
  slide_times?: number[];
}

/**
 * Time allocation response
 */
export interface TimeAllocationResponse {
  success: boolean;
  total_minutes: number;
  slide_times: number[];
  message: string;
}

/**
 * Script style options
 */
export type ScriptStyle = "conversational" | "formal" | "casual";

/**
 * Teaching Script API
 */
export const scriptsAPI = {
  /**
   * Get teaching script for a presentation
   */
  async getScript(presentationId: string): Promise<PresentationScript> {
    const response = await api.get<PresentationScript>(
      `/api/v1/scripts/${presentationId}`,
    );
    return response.data;
  },

  /**
   * Update entire presentation script
   */
  async updateScript(
    presentationId: string,
    updates: PresentationScriptUpdateRequest,
  ): Promise<PresentationScript> {
    const response = await api.put<PresentationScript>(
      `/api/v1/scripts/${presentationId}`,
      updates,
    );
    return response.data;
  },

  /**
   * Update a single slide's script
   */
  async updateSlideScript(
    presentationId: string,
    slideIndex: number,
    update: SlideScriptUpdateRequest,
  ): Promise<SlideScript> {
    const response = await api.put<SlideScript>(
      `/api/v1/scripts/${presentationId}/slide/${slideIndex}`,
      update,
    );
    return response.data;
  },

  /**
   * Regenerate script (all or specific slides)
   */
  async regenerateScript(
    presentationId: string,
    options?: RegenerateScriptRequest,
  ): Promise<PresentationScript> {
    const response = await api.post<PresentationScript>(
      `/api/v1/scripts/${presentationId}/regenerate`,
      options || {},
    );
    return response.data;
  },

  /**
   * Adjust time allocation for slides
   */
  async adjustTimeAllocation(
    presentationId: string,
    request: TimeAllocationRequest,
  ): Promise<TimeAllocationResponse> {
    const response = await api.put<TimeAllocationResponse>(
      `/api/v1/scripts/${presentationId}/time-allocation`,
      request,
    );
    return response.data;
  },

  /**
   * Export script as PDF
   */
  async exportPDF(presentationId: string): Promise<Blob> {
    const response = await api.get(
      `/api/v1/scripts/${presentationId}/export/pdf`,
      { responseType: "blob" },
    );
    return response.data;
  },

  /**
   * Export script as Word document
   */
  async exportDocx(presentationId: string): Promise<Blob> {
    const response = await api.get(
      `/api/v1/scripts/${presentationId}/export/docx`,
      { responseType: "blob" },
    );
    return response.data;
  },

  /**
   * Download file helper
   */
  downloadFile(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Export and download PDF
   */
  async downloadPDF(presentationId: string, title?: string): Promise<void> {
    const blob = await this.exportPDF(presentationId);
    const filename = title
      ? `${title}_script.pdf`
      : `script_${presentationId}.pdf`;
    this.downloadFile(blob, filename);
  },

  /**
   * Export and download Word document
   */
  async downloadDocx(presentationId: string, title?: string): Promise<void> {
    const blob = await this.exportDocx(presentationId);
    const filename = title
      ? `${title}_script.docx`
      : `script_${presentationId}.docx`;
    this.downloadFile(blob, filename);
  },

  /**
   * Format time for display (e.g., "5.5" -> "5分30秒")
   */
  formatTime(minutes: number): string {
    const mins = Math.floor(minutes);
    const secs = Math.round((minutes - mins) * 60);
    if (secs === 0) {
      return `${mins}分鐘`;
    }
    return `${mins}分${secs}秒`;
  },

  /**
   * Format total time for display (e.g., "45.5" -> "45分鐘")
   */
  formatTotalTime(minutes: number): string {
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    if (hours === 0) {
      return `${mins}分鐘`;
    }
    return `${hours}小時${mins}分鐘`;
  },
};

export default scriptsAPI;
