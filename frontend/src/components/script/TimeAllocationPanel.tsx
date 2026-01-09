/**
 * Time Allocation Panel Component
 *
 * Panel for adjusting time allocation across slides
 */

import React, { useState } from "react";
import { PresentationScript } from "@/api/scripts";
import scriptsAPI from "@/api/scripts";
import "./script-editor.css";

interface TimeAllocationPanelProps {
  script: PresentationScript;
  onAdjust: (targetTotal?: number, slideTimes?: number[]) => void;
  onClose: () => void;
}

const TimeAllocationPanel: React.FC<TimeAllocationPanelProps> = ({
  script,
  onAdjust,
  onClose,
}) => {
  const [mode, setMode] = useState<"total" | "individual">("total");
  const [targetTotal, setTargetTotal] = useState(
    Math.round(script.total_minutes),
  );
  const [slideTimes, setSlideTimes] = useState<number[]>(
    script.scripts.map((s) => s.estimated_minutes),
  );

  const handleSlideTimeChange = (index: number, value: number) => {
    const newTimes = [...slideTimes];
    newTimes[index] = Math.max(0.5, Math.min(30, value));
    setSlideTimes(newTimes);
  };

  const handleApply = () => {
    if (mode === "total") {
      onAdjust(targetTotal, undefined);
    } else {
      onAdjust(undefined, slideTimes);
    }
    onClose();
  };

  const calculatedTotal = slideTimes.reduce((sum, t) => sum + t, 0);

  return (
    <div className="time-panel">
      <div className="time-panel__header">
        <h3>⏱️ 時間配置</h3>
        <button className="time-panel__close" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="time-panel__content">
        {/* Mode Selection */}
        <div className="time-panel__mode">
          <label>
            <input
              type="radio"
              name="mode"
              checked={mode === "total"}
              onChange={() => setMode("total")}
            />
            按總時長調整
          </label>
          <label>
            <input
              type="radio"
              name="mode"
              checked={mode === "individual"}
              onChange={() => setMode("individual")}
            />
            個別調整每張投影片
          </label>
        </div>

        {/* Total Time Mode */}
        {mode === "total" && (
          <div className="time-panel__total">
            <label>目標總時長 (分鐘):</label>
            <input
              type="number"
              value={targetTotal}
              onChange={(e) => setTargetTotal(parseInt(e.target.value) || 0)}
              min={5}
              max={180}
              step={5}
            />
            <p className="time-panel__hint">
              目前總時長：{scriptsAPI.formatTotalTime(script.total_minutes)}
              <br />
              系統會按比例調整各投影片時間
            </p>
          </div>
        )}

        {/* Individual Mode */}
        {mode === "individual" && (
          <div className="time-panel__individual">
            <div className="time-panel__slides-header">
              <span>投影片</span>
              <span>時間 (分鐘)</span>
            </div>
            <div className="time-panel__slides-list">
              {script.scripts.map((s, i) => (
                <div key={i} className="time-panel__slide-row">
                  <span className="time-panel__slide-title">
                    {i + 1}. {s.slide_title || `投影片 ${i + 1}`}
                  </span>
                  <input
                    type="number"
                    value={slideTimes[i]}
                    onChange={(e) =>
                      handleSlideTimeChange(i, parseFloat(e.target.value) || 0)
                    }
                    min={0.5}
                    max={30}
                    step={0.5}
                  />
                </div>
              ))}
            </div>
            <p className="time-panel__calculated">
              調整後總時長：{scriptsAPI.formatTotalTime(calculatedTotal)}
            </p>
          </div>
        )}
      </div>

      <div className="time-panel__footer">
        <button
          className="time-panel__btn time-panel__btn--cancel"
          onClick={onClose}
        >
          取消
        </button>
        <button
          className="time-panel__btn time-panel__btn--apply"
          onClick={handleApply}
        >
          套用
        </button>
      </div>
    </div>
  );
};

export default TimeAllocationPanel;
