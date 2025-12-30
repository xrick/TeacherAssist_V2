interface GenerationOptions {
  title: string
  author: string
  audience: string
  tone: string
}

interface GenerationControlProps {
  options: GenerationOptions
  onOptionsChange: (options: GenerationOptions) => void
  onGenerate: () => void
  disabled?: boolean
  isGenerating?: boolean
}

export default function GenerationControl({
  options,
  onOptionsChange,
  onGenerate,
  disabled,
  isGenerating,
}: GenerationControlProps) {
  const handleChange = (field: keyof GenerationOptions, value: string) => {
    onOptionsChange({ ...options, [field]: value })
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 px-4 py-3">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">生成設定</h3>
      </div>

      {/* Form */}
      <div className="p-4 space-y-4">
        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            簡報標題 <span className="text-slate-400">(可選)</span>
          </label>
          <input
            type="text"
            value={options.title}
            onChange={(e) => handleChange('title', e.target.value)}
            placeholder="自動從內容提取"
            disabled={isGenerating}
            className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {/* Author */}
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            作者 <span className="text-slate-400">(可選)</span>
          </label>
          <input
            type="text"
            value={options.author}
            onChange={(e) => handleChange('author', e.target.value)}
            placeholder="您的名字"
            disabled={isGenerating}
            className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {/* Audience */}
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            目標受眾 <span className="text-slate-400">(可選)</span>
          </label>
          <select
            value={options.audience}
            onChange={(e) => handleChange('audience', e.target.value)}
            disabled={isGenerating}
            className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="">一般受眾</option>
            <option value="students">學生</option>
            <option value="professionals">專業人士</option>
            <option value="executives">高階主管</option>
            <option value="technical">技術人員</option>
            <option value="general">一般大眾</option>
          </select>
        </div>

        {/* Tone */}
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            語氣風格
          </label>
          <select
            value={options.tone}
            onChange={(e) => handleChange('tone', e.target.value)}
            disabled={isGenerating}
            className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="professional">專業正式</option>
            <option value="casual">輕鬆親切</option>
            <option value="academic">學術嚴謹</option>
            <option value="creative">創意活潑</option>
          </select>
        </div>

        {/* Generate Button */}
        <button
          onClick={onGenerate}
          disabled={disabled || isGenerating}
          className="w-full px-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-lg shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center space-x-2"
        >
          {isGenerating ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>生成中...</span>
            </>
          ) : (
            <>
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
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
              <span>生成簡報</span>
            </>
          )}
        </button>
      </div>
    </div>
  )
}
