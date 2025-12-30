import type { GenerationResponse } from '@/types/api'

interface ResultPreviewProps {
  result: GenerationResponse
  onDownload: () => void
  onReset: () => void
}

export default function ResultPreview({ result, onDownload, onReset }: ResultPreviewProps) {
  return (
    <div className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-lg border-2 border-green-200 dark:border-green-800 overflow-hidden">
      {/* Header */}
      <div className="bg-green-100 dark:bg-green-900/30 border-b border-green-200 dark:border-green-800 px-4 py-3">
        <div className="flex items-center space-x-2">
          <svg
            className="w-5 h-5 text-green-600 dark:text-green-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <h3 className="text-sm font-semibold text-green-900 dark:text-green-200">
            簡報生成成功！
          </h3>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-white dark:bg-slate-800 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">投影片數量</span>
              <span className="text-2xl font-bold text-slate-900 dark:text-white">
                {result.slide_count}
              </span>
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">模板</span>
              <span className="text-sm font-medium text-slate-900 dark:text-white truncate ml-2">
                {result.metadata?.template || 'default'}
              </span>
            </div>
          </div>
        </div>

        {/* Metadata */}
        {result.metadata && (
          <div className="mb-6 p-4 bg-white dark:bg-slate-800 rounded-lg">
            <h4 className="text-sm font-medium text-slate-900 dark:text-white mb-3">
              簡報資訊
            </h4>
            <dl className="space-y-2">
              {result.metadata.title && (
                <div className="flex justify-between text-sm">
                  <dt className="text-slate-600 dark:text-slate-400">標題:</dt>
                  <dd className="text-slate-900 dark:text-white font-medium">
                    {result.metadata.title}
                  </dd>
                </div>
              )}
              {result.metadata.author && (
                <div className="flex justify-between text-sm">
                  <dt className="text-slate-600 dark:text-slate-400">作者:</dt>
                  <dd className="text-slate-900 dark:text-white font-medium">
                    {result.metadata.author}
                  </dd>
                </div>
              )}
              <div className="flex justify-between text-sm">
                <dt className="text-slate-600 dark:text-slate-400">ID:</dt>
                <dd className="text-slate-900 dark:text-white font-mono text-xs">
                  {result.presentation_id}
                </dd>
              </div>
            </dl>
          </div>
        )}

        {/* Actions */}
        <div className="flex space-x-3">
          <button
            onClick={onDownload}
            className="flex-1 px-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-medium rounded-lg shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all flex items-center justify-center space-x-2"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            <span>下載簡報</span>
          </button>

          <button
            onClick={onReset}
            className="px-4 py-3 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 font-medium rounded-lg transition-colors flex items-center justify-center"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
