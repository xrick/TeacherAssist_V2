/**
 * Result Tabs Component
 *
 * Tab-based result area showing preview, script editor, and download options
 */

import React, { useState } from "react";
import type { GenerationResponse } from "@/types/api";
import { ScriptEditor } from "@/components/script";
import "./result-tabs.css";

type TabType = "preview" | "script" | "download";

interface ResultTabsProps {
  result: GenerationResponse;
  onReset: () => void;
}

const ResultTabs: React.FC<ResultTabsProps> = ({ result, onReset }) => {
  const [activeTab, setActiveTab] = useState<TabType>("preview");

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: "preview", label: "投影片預覽", icon: "📊" },
    { id: "script", label: "逐字稿", icon: "📝" },
    { id: "download", label: "下載", icon: "⬇️" },
  ];

  const handleDownloadPPTX = () => {
    window.open(result.download_url, "_blank");
  };

  return (
    <div className="result-tabs">
      {/* Tab Header */}
      <div className="result-tabs__header">
        <div className="result-tabs__tab-list">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`result-tabs__tab ${
                activeTab === tab.id ? "result-tabs__tab--active" : ""
              }`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="result-tabs__tab-icon">{tab.icon}</span>
              <span className="result-tabs__tab-label">{tab.label}</span>
            </button>
          ))}
        </div>
        <div className="result-tabs__actions">
          <button
            className="result-tabs__reset-btn"
            onClick={onReset}
            title="重新開始"
          >
            🔄 重新開始
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="result-tabs__content">
        {/* Preview Tab */}
        {activeTab === "preview" && (
          <div className="result-tabs__panel result-tabs__panel--preview">
            <div className="preview-container">
              <div className="preview-header">
                <h3>📊 簡報預覽</h3>
                <span className="preview-info">
                  {result.slide_count} 張投影片
                </span>
              </div>
              <div className="preview-placeholder">
                <div className="preview-icon">🎯</div>
                <p>簡報已成功生成！</p>
                <p className="preview-subtitle">
                  標題：{result.metadata?.title || "未命名簡報"}
                </p>
                <div className="preview-stats">
                  <div className="preview-stat">
                    <span className="preview-stat-value">
                      {result.slide_count}
                    </span>
                    <span className="preview-stat-label">投影片</span>
                  </div>
                </div>
                <button
                  className="preview-download-btn"
                  onClick={handleDownloadPPTX}
                >
                  ⬇️ 下載 PPTX 預覽
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Script Tab */}
        {activeTab === "script" && (
          <div className="result-tabs__panel result-tabs__panel--script">
            <ScriptEditor
              presentationId={result.presentation_id}
              presentationTitle={result.metadata?.title}
            />
          </div>
        )}

        {/* Download Tab */}
        {activeTab === "download" && (
          <div className="result-tabs__panel result-tabs__panel--download">
            <div className="download-container">
              <h3>⬇️ 下載選項</h3>
              <p className="download-description">
                選擇您需要的檔案格式進行下載
              </p>

              <div className="download-grid">
                {/* PPTX Download */}
                <div className="download-card">
                  <div className="download-card__icon">📊</div>
                  <div className="download-card__info">
                    <h4>PowerPoint 簡報</h4>
                    <p>下載完整的 PPTX 檔案</p>
                  </div>
                  <button
                    className="download-card__btn download-card__btn--primary"
                    onClick={handleDownloadPPTX}
                  >
                    下載 PPTX
                  </button>
                </div>

                {/* PDF Script Download */}
                <div className="download-card">
                  <div className="download-card__icon">📄</div>
                  <div className="download-card__info">
                    <h4>教學腳本 (PDF)</h4>
                    <p>匯出逐字稿為 PDF 格式</p>
                  </div>
                  <button
                    className="download-card__btn"
                    onClick={() => {
                      window.open(
                        `/api/v1/scripts/${result.presentation_id}/export/pdf`,
                        "_blank",
                      );
                    }}
                  >
                    下載 PDF
                  </button>
                </div>

                {/* Word Script Download */}
                <div className="download-card">
                  <div className="download-card__icon">📝</div>
                  <div className="download-card__info">
                    <h4>教學腳本 (Word)</h4>
                    <p>匯出逐字稿為 Word 格式</p>
                  </div>
                  <button
                    className="download-card__btn"
                    onClick={() => {
                      window.open(
                        `/api/v1/scripts/${result.presentation_id}/export/docx`,
                        "_blank",
                      );
                    }}
                  >
                    下載 DOCX
                  </button>
                </div>
              </div>

              {/* Info */}
              <div className="download-info">
                <p>💡 提示：您可以先在「逐字稿」分頁編輯內容，再匯出最終版本</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultTabs;
