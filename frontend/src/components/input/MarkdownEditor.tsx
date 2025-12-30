import { useState } from 'react'

interface MarkdownEditorProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

export default function MarkdownEditor({ value, onChange, disabled }: MarkdownEditorProps) {
  const [showPreview, setShowPreview] = useState(false)

  const exampleMarkdown = `# 簡報標題

## 第一節：簡介

- 要點 1
- 要點 2
- 要點 3

## 第二節：主要內容

這裡是詳細說明內容。

### 子標題

1. 步驟一
2. 步驟二
3. 步驟三

## 結論

總結要點
`

  const handleInsertExample = () => {
    onChange(exampleMarkdown)
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Toolbar */}
      <div className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Markdown 內容
            </h3>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              ({value.length} 字元)
            </span>
          </div>
          <div className="flex items-center space-x-2">
            {!value.trim() && (
              <button
                onClick={handleInsertExample}
                className="px-3 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md transition-colors"
              >
                插入範例
              </button>
            )}
            <button
              onClick={() => setShowPreview(!showPreview)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                showPreview
                  ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {showPreview ? '編輯' : '預覽'}
            </button>
          </div>
        </div>
      </div>

      {/* Editor/Preview Area */}
      <div className="relative">
        {showPreview ? (
          <div className="p-6 prose dark:prose-invert max-w-none h-[600px] overflow-y-auto">
            {value ? (
              <div dangerouslySetInnerHTML={{ __html: value.replace(/\n/g, '<br />') }} />
            ) : (
              <p className="text-slate-400 dark:text-slate-600 italic">尚無內容...</p>
            )}
          </div>
        ) : (
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            placeholder="在此輸入 Markdown 格式的簡報內容..."
            className="w-full h-[600px] p-6 font-mono text-sm text-slate-900 dark:text-white bg-transparent resize-none focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
            spellCheck={false}
          />
        )}
      </div>

      {/* Footer */}
      <div className="bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700 px-4 py-2">
        <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>支援標準 Markdown 語法</span>
          <span>使用 # 標題來分隔投影片</span>
        </div>
      </div>
    </div>
  )
}
