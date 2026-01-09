/**
 * Script Toolbar Component
 *
 * Toolbar with actions for script management
 */

import React, { useState } from "react";
import { ScriptStyle } from "@/api/scripts";
import "./script-editor.css";

interface ScriptToolbarProps {
  onRegenerate: (
    style?: ScriptStyle,
    slideIndices?: number[],
    targetMinutes?: number,
  ) => void;
  onExportPDF: () => void;
  onExportDocx: () => void;
  onToggleTimePanel: () => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  regenerating: boolean;
  saving: boolean;
}

const ScriptToolbar: React.FC<ScriptToolbarProps> = ({
  onRegenerate,
  onExportPDF,
  onExportDocx,
  onToggleTimePanel,
  onExpandAll,
  onCollapseAll,
  regenerating,
  saving,
}) => {
  const [showStyleMenu, setShowStyleMenu] = useState(false);

  const handleStyleSelect = (style: ScriptStyle) => {
    setShowStyleMenu(false);
    onRegenerate(style);
  };

  return (
    <div className="script-toolbar">
      {/* Left Section: View Controls */}
      <div className="script-toolbar__section">
        <button
          className="script-toolbar__btn"
          onClick={onExpandAll}
          title="展開全部"
        >
          📂 展開全部
        </button>
        <button
          className="script-toolbar__btn"
          onClick={onCollapseAll}
          title="收合全部"
        >
          📁 收合全部
        </button>
      </div>

      {/* Center Section: Actions */}
      <div className="script-toolbar__section">
        <div className="script-toolbar__dropdown">
          <button
            className="script-toolbar__btn script-toolbar__btn--primary"
            onClick={() => setShowStyleMenu(!showStyleMenu)}
            disabled={regenerating}
            title="重新生成腳本"
          >
            {regenerating ? "🔄 生成中..." : "🔄 重新生成"}
          </button>
          {showStyleMenu && (
            <div className="script-toolbar__dropdown-menu">
              <button onClick={() => handleStyleSelect("conversational")}>
                💬 口語化風格
              </button>
              <button onClick={() => handleStyleSelect("formal")}>
                📚 正式風格
              </button>
              <button onClick={() => handleStyleSelect("casual")}>
                😊 輕鬆風格
              </button>
            </div>
          )}
        </div>

        <button
          className="script-toolbar__btn"
          onClick={onToggleTimePanel}
          title="調整時間配置"
        >
          ⏱️ 時間配置
        </button>
      </div>

      {/* Right Section: Export */}
      <div className="script-toolbar__section">
        <button
          className="script-toolbar__btn script-toolbar__btn--export"
          onClick={onExportPDF}
          disabled={saving}
          title="匯出為 PDF"
        >
          📄 匯出 PDF
        </button>
        <button
          className="script-toolbar__btn script-toolbar__btn--export"
          onClick={onExportDocx}
          disabled={saving}
          title="匯出為 Word"
        >
          📝 匯出 Word
        </button>
      </div>
    </div>
  );
};

export default ScriptToolbar;
