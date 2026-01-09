/**
 * Script Editor Component
 *
 * Main component for viewing and editing teaching scripts
 */

import React, { useState, useEffect, useCallback } from "react";
import scriptsAPI, {
  PresentationScript,
  SlideScriptUpdateRequest,
  ScriptStyle,
} from "@/api/scripts";
import SlideScriptCard from "./SlideScriptCard";
import ScriptToolbar from "./ScriptToolbar";
import TimeAllocationPanel from "./TimeAllocationPanel";
import "./script-editor.css";

interface ScriptEditorProps {
  presentationId: string;
  presentationTitle?: string;
  onClose?: () => void;
}

const ScriptEditor: React.FC<ScriptEditorProps> = ({
  presentationId,
  presentationTitle,
  onClose,
}) => {
  const [script, setScript] = useState<PresentationScript | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [expandedSlides, setExpandedSlides] = useState<Set<number>>(
    new Set([0]),
  );
  const [showTimePanel, setShowTimePanel] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  // Load script on mount
  useEffect(() => {
    loadScript();
  }, [presentationId]);

  const loadScript = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await scriptsAPI.getScript(presentationId);
      setScript(data);
    } catch (err: any) {
      if (err.response?.status === 404) {
        setError("此簡報尚未生成教學腳本");
      } else {
        setError("載入腳本失敗：" + (err.message || "未知錯誤"));
      }
    } finally {
      setLoading(false);
    }
  };

  // Update single slide script
  const handleSlideUpdate = useCallback(
    async (slideIndex: number, update: SlideScriptUpdateRequest) => {
      if (!script) return;

      try {
        setSaving(true);
        const updatedSlide = await scriptsAPI.updateSlideScript(
          presentationId,
          slideIndex,
          update,
        );

        // Update local state
        setScript((prev) => {
          if (!prev) return prev;
          const newScripts = [...prev.scripts];
          newScripts[slideIndex] = updatedSlide;
          const newScript = { ...prev, scripts: newScripts };
          // Recalculate total time
          newScript.total_minutes = newScripts.reduce(
            (sum, s) => sum + s.estimated_minutes,
            0,
          );
          return newScript;
        });
      } catch (err: any) {
        console.error("Failed to update slide script:", err);
        alert("儲存失敗：" + (err.message || "未知錯誤"));
      } finally {
        setSaving(false);
      }
    },
    [presentationId, script],
  );

  // Regenerate script
  const handleRegenerate = async (
    style?: ScriptStyle,
    slideIndices?: number[],
    targetMinutes?: number,
  ) => {
    try {
      setRegenerating(true);
      const updated = await scriptsAPI.regenerateScript(presentationId, {
        style,
        slide_indices: slideIndices,
        target_total_minutes: targetMinutes,
      });
      setScript(updated);
    } catch (err: any) {
      console.error("Failed to regenerate script:", err);
      alert("重新生成失敗：" + (err.message || "未知錯誤"));
    } finally {
      setRegenerating(false);
    }
  };

  // Adjust time allocation
  const handleTimeAdjust = async (
    targetTotal?: number,
    slideTimes?: number[],
  ) => {
    try {
      setSaving(true);
      const result = await scriptsAPI.adjustTimeAllocation(presentationId, {
        target_total_minutes: targetTotal,
        slide_times: slideTimes,
      });

      // Reload script to get updated times
      await loadScript();
      alert(result.message);
    } catch (err: any) {
      console.error("Failed to adjust time:", err);
      alert("調整時間失敗：" + (err.message || "未知錯誤"));
    } finally {
      setSaving(false);
    }
  };

  // Export functions
  const handleExportPDF = async () => {
    try {
      setSaving(true);
      await scriptsAPI.downloadPDF(presentationId, script?.title);
    } catch (err: any) {
      console.error("Failed to export PDF:", err);
      alert("匯出 PDF 失敗：" + (err.message || "未知錯誤"));
    } finally {
      setSaving(false);
    }
  };

  const handleExportDocx = async () => {
    try {
      setSaving(true);
      await scriptsAPI.downloadDocx(presentationId, script?.title);
    } catch (err: any) {
      console.error("Failed to export DOCX:", err);
      alert("匯出 Word 失敗：" + (err.message || "未知錯誤"));
    } finally {
      setSaving(false);
    }
  };

  // Toggle slide expansion
  const toggleSlide = (index: number) => {
    setExpandedSlides((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  // Expand/collapse all
  const expandAll = () => {
    if (script) {
      setExpandedSlides(new Set(script.scripts.map((_, i) => i)));
    }
  };

  const collapseAll = () => {
    setExpandedSlides(new Set());
  };

  if (loading) {
    return (
      <div className="script-editor script-editor--loading">
        <div className="script-editor__spinner" />
        <p>載入教學腳本中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="script-editor script-editor--error">
        <div className="script-editor__error-icon">⚠️</div>
        <p>{error}</p>
        <button onClick={loadScript} className="script-editor__retry-btn">
          重試
        </button>
        {onClose && (
          <button onClick={onClose} className="script-editor__close-btn">
            關閉
          </button>
        )}
      </div>
    );
  }

  if (!script) {
    return null;
  }

  return (
    <div className="script-editor">
      {/* Header */}
      <header className="script-editor__header">
        <div className="script-editor__title-section">
          <h2 className="script-editor__title">
            📝 {script.title || presentationTitle || "教學腳本"}
          </h2>
          <span className="script-editor__total-time">
            總時長：{scriptsAPI.formatTotalTime(script.total_minutes)}
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="script-editor__close-btn"
            title="關閉"
          >
            ✕
          </button>
        )}
      </header>

      {/* Toolbar */}
      <ScriptToolbar
        onRegenerate={handleRegenerate}
        onExportPDF={handleExportPDF}
        onExportDocx={handleExportDocx}
        onToggleTimePanel={() => setShowTimePanel(!showTimePanel)}
        onExpandAll={expandAll}
        onCollapseAll={collapseAll}
        regenerating={regenerating}
        saving={saving}
      />

      {/* Time Allocation Panel */}
      {showTimePanel && (
        <TimeAllocationPanel
          script={script}
          onAdjust={handleTimeAdjust}
          onClose={() => setShowTimePanel(false)}
        />
      )}

      {/* Slide Scripts */}
      <div className="script-editor__slides">
        {script.scripts.map((slideScript, index) => (
          <SlideScriptCard
            key={index}
            slideScript={slideScript}
            isExpanded={expandedSlides.has(index)}
            onToggle={() => toggleSlide(index)}
            onUpdate={(update) => handleSlideUpdate(index, update)}
            onRegenerate={() => handleRegenerate(undefined, [index])}
            isFirst={index === 0}
            isLast={index === script.scripts.length - 1}
          />
        ))}
      </div>

      {/* Footer Info */}
      <footer className="script-editor__footer">
        <span>
          生成時間：{new Date(script.generated_at).toLocaleString("zh-TW")}
        </span>
        <span>
          最後編輯：{new Date(script.last_edited_at).toLocaleString("zh-TW")}
        </span>
      </footer>
    </div>
  );
};

export default ScriptEditor;
