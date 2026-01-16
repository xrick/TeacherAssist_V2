import type { ProgressUpdate, GenerationResponse } from "@/types/api";

interface ProgressMonitorProps {
  progress: ProgressUpdate | null;
  result: GenerationResponse | null;
  error: string | null;
  isGenerating: boolean;
  onReset: () => void;
  onStop: () => void;
}

/**
 * 新的 4 階段流程：
 * 1. template_analysis - 分析 Template 結構 (0-10%)
 * 2. content_generation - LLM 擴展使用者輸入 (10-50%)
 * 3. content_organization - 組織內容到 Template (50-80%)
 * 4. pptx_building - 建構最終 PPTX (80-100%)
 *
 * 額外階段（後處理）：
 * - adding_images - 自動配圖 (85%)
 * - generating_script - 生成教學稿 (92%)
 * - completed - 完成 (100%)
 */
const stageNames: Record<string, string> = {
  // 4 階段主流程
  template_analysis: "🔍 分析模板",
  content_generation: "✨ 生成內容",
  content_organization: "📋 組織結構",
  pptx_building: "🏗️ 建構簡報",
  // 後處理階段
  adding_images: "🖼️ 自動配圖",
  generating_script: "📝 生成教學稿",
  completed: "✅ 完成",
};

// 主要 4 階段（用於進度指示器）
const mainStages = [
  { key: "template_analysis", name: "分析模板", progressStart: 0 },
  { key: "content_generation", name: "生成內容", progressStart: 10 },
  { key: "content_organization", name: "組織結構", progressStart: 50 },
  { key: "pptx_building", name: "建構簡報", progressStart: 80 },
];

export default function ProgressMonitor({
  progress,
  result,
  error,
  isGenerating,
  onReset,
  onStop,
}: ProgressMonitorProps) {
  const currentProgress = progress?.progress || 0;
  const currentStage = progress?.stage || "";
  const currentMessage = progress?.message || "";

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 rounded-lg border-2 border-red-200 dark:border-red-800 overflow-hidden">
        <div className="p-4">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <svg
                className="w-6 h-6 text-red-600 dark:text-red-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-red-900 dark:text-red-200">
                生成失敗
              </h4>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                {error}
              </p>
              <button
                onClick={onReset}
                className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                重新開始
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (result) {
    return null; // Result will be shown in ResultPreview component
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border-b border-slate-200 dark:border-slate-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
            生成進度
          </h3>
          {isGenerating && (
            <button
              onClick={onStop}
              className="px-3 py-1 text-xs font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors"
            >
              停止
            </button>
          )}
        </div>
      </div>

      {/* Progress */}
      <div className="p-6">
        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-900 dark:text-white">
              {stageNames[currentStage] || currentStage}
            </span>
            <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
              {Math.round(currentProgress)}%
            </span>
          </div>
          <div className="w-full h-3 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-600 to-purple-600 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${currentProgress}%` }}
            >
              {isGenerating && (
                <div className="h-full w-full bg-gradient-to-r from-transparent via-white/30 to-transparent animate-pulse"></div>
              )}
            </div>
          </div>
        </div>

        {/* Current Message */}
        {currentMessage && (
          <div className="mt-4 p-3 bg-slate-50 dark:bg-slate-900 rounded-lg">
            <p className="text-sm text-slate-700 dark:text-slate-300">
              {currentMessage}
            </p>
          </div>
        )}

        {/* Stage Indicators - 新的 4 階段 */}
        <div className="mt-6 grid grid-cols-4 gap-2">
          {mainStages.map((stage, index) => {
            const isActive = currentProgress >= stage.progressStart;
            const isCurrent =
              currentProgress >= stage.progressStart &&
              (index === mainStages.length - 1 ||
                currentProgress < mainStages[index + 1].progressStart);

            return (
              <div
                key={stage.key}
                className={`flex flex-col items-center p-2 rounded-lg transition-all ${
                  isActive
                    ? "bg-blue-50 dark:bg-blue-900/20"
                    : "bg-slate-50 dark:bg-slate-900"
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all ${
                    isActive
                      ? "bg-gradient-to-br from-blue-600 to-purple-600 text-white shadow-lg"
                      : "bg-slate-200 dark:bg-slate-700 text-slate-500"
                  } ${isCurrent ? "animate-pulse" : ""}`}
                >
                  {isActive ? (
                    <svg
                      className="w-4 h-4"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    index + 1
                  )}
                </div>
                <span
                  className={`mt-1 text-xs text-center ${
                    isActive
                      ? "text-blue-700 dark:text-blue-300 font-medium"
                      : "text-slate-500 dark:text-slate-400"
                  }`}
                >
                  {stage.name}
                </span>
              </div>
            );
          })}
        </div>

        {/* 後處理階段提示 */}
        {(currentStage === "adding_images" ||
          currentStage === "generating_script") && (
          <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
            <p className="text-xs text-amber-700 dark:text-amber-300">
              {currentStage === "adding_images"
                ? "🖼️ 正在為投影片自動配置圖片..."
                : "📝 正在生成教學講稿..."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
