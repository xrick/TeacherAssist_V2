/**
 * Slide Script Card Component
 *
 * Displays and allows editing of a single slide's teaching script
 */

import React, { useState } from "react";
import {
  SlideScript,
  SlideScriptUpdateRequest,
  InteractionQA,
} from "@/api/scripts";
import scriptsAPI from "@/api/scripts";
import "./script-editor.css";

interface SlideScriptCardProps {
  slideScript: SlideScript;
  isExpanded: boolean;
  onToggle: () => void;
  onUpdate: (update: SlideScriptUpdateRequest) => Promise<void>;
  onRegenerate: () => void;
  isFirst?: boolean;
  isLast: boolean;
}

const SlideScriptCard: React.FC<SlideScriptCardProps> = ({
  slideScript,
  isExpanded,
  onToggle,
  onUpdate,
  onRegenerate,
  isLast,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(
    slideScript.lecture_content,
  );
  const [editedTips, setEditedTips] = useState(
    slideScript.teaching_tips.join("\n"),
  );
  const [editedTransition, setEditedTransition] = useState(
    slideScript.transition,
  );
  const [editedTime, setEditedTime] = useState(slideScript.estimated_minutes);
  const [editedQA, setEditedQA] = useState<InteractionQA[]>(
    slideScript.interaction_qa,
  );

  const handleSave = async () => {
    await onUpdate({
      lecture_content: editedContent,
      teaching_tips: editedTips.split("\n").filter((t) => t.trim()),
      transition: editedTransition,
      estimated_minutes: editedTime,
      interaction_qa: editedQA,
    });
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedContent(slideScript.lecture_content);
    setEditedTips(slideScript.teaching_tips.join("\n"));
    setEditedTransition(slideScript.transition);
    setEditedTime(slideScript.estimated_minutes);
    setEditedQA(slideScript.interaction_qa);
    setIsEditing(false);
  };

  const addQA = () => {
    setEditedQA([...editedQA, { question: "", expected_answers: [""] }]);
  };

  const removeQA = (index: number) => {
    setEditedQA(editedQA.filter((_, i) => i !== index));
  };

  const updateQA = (
    index: number,
    field: "question" | "answers",
    value: string,
  ) => {
    const newQA = [...editedQA];
    if (field === "question") {
      newQA[index] = { ...newQA[index], question: value };
    } else {
      newQA[index] = {
        ...newQA[index],
        expected_answers: value.split("\n").filter((a) => a.trim()),
      };
    }
    setEditedQA(newQA);
  };

  return (
    <div
      className={`slide-script-card ${
        isExpanded ? "slide-script-card--expanded" : ""
      }`}
    >
      {/* Header */}
      <div className="slide-script-card__header" onClick={onToggle}>
        <div className="slide-script-card__header-left">
          <span className="slide-script-card__index">
            {slideScript.slide_index + 1}
          </span>
          <h3 className="slide-script-card__title">
            {slideScript.slide_title || `投影片 ${slideScript.slide_index + 1}`}
          </h3>
        </div>
        <div className="slide-script-card__header-right">
          <span className="slide-script-card__time">
            ⏱️ {scriptsAPI.formatTime(slideScript.estimated_minutes)}
          </span>
          <span className="slide-script-card__toggle">
            {isExpanded ? "▼" : "▶"}
          </span>
        </div>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="slide-script-card__content">
          {/* Lecture Content */}
          <section className="slide-script-card__section">
            <h4>📖 講述內容</h4>
            {isEditing ? (
              <textarea
                className="slide-script-card__textarea"
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                rows={6}
                placeholder="輸入講述內容..."
              />
            ) : (
              <p className="slide-script-card__text">
                {slideScript.lecture_content}
              </p>
            )}
          </section>

          {/* Teaching Tips */}
          <section className="slide-script-card__section">
            <h4>💡 教學提示</h4>
            {isEditing ? (
              <textarea
                className="slide-script-card__textarea"
                value={editedTips}
                onChange={(e) => setEditedTips(e.target.value)}
                rows={3}
                placeholder="每行一個教學提示..."
              />
            ) : (
              <ul className="slide-script-card__tips">
                {slideScript.teaching_tips.map((tip, i) => (
                  <li key={i}>{tip}</li>
                ))}
              </ul>
            )}
          </section>

          {/* Interaction Q&A */}
          <section className="slide-script-card__section">
            <h4>❓ 互動問答</h4>
            {isEditing ? (
              <div className="slide-script-card__qa-editor">
                {editedQA.map((qa, i) => (
                  <div key={i} className="slide-script-card__qa-item">
                    <div className="slide-script-card__qa-question">
                      <label>問題 {i + 1}:</label>
                      <input
                        type="text"
                        value={qa.question}
                        onChange={(e) =>
                          updateQA(i, "question", e.target.value)
                        }
                        placeholder="輸入問題..."
                      />
                      <button
                        className="slide-script-card__qa-remove"
                        onClick={() => removeQA(i)}
                        title="移除問題"
                      >
                        ✕
                      </button>
                    </div>
                    <div className="slide-script-card__qa-answers">
                      <label>預期答案 (每行一個):</label>
                      <textarea
                        value={qa.expected_answers.join("\n")}
                        onChange={(e) => updateQA(i, "answers", e.target.value)}
                        rows={2}
                        placeholder="輸入預期答案..."
                      />
                    </div>
                  </div>
                ))}
                <button className="slide-script-card__qa-add" onClick={addQA}>
                  + 新增問答
                </button>
              </div>
            ) : (
              <div className="slide-script-card__qa-list">
                {slideScript.interaction_qa.length === 0 ? (
                  <p className="slide-script-card__empty">無互動問答</p>
                ) : (
                  slideScript.interaction_qa.map((qa, i) => (
                    <div key={i} className="slide-script-card__qa-display">
                      <p className="slide-script-card__qa-q">
                        <strong>Q{i + 1}:</strong> {qa.question}
                      </p>
                      <p className="slide-script-card__qa-a">
                        <strong>預期答案:</strong>{" "}
                        {qa.expected_answers.join(" / ")}
                      </p>
                    </div>
                  ))
                )}
              </div>
            )}
          </section>

          {/* Transition */}
          {!isLast && (
            <section className="slide-script-card__section">
              <h4>🔗 過場銜接</h4>
              {isEditing ? (
                <textarea
                  className="slide-script-card__textarea"
                  value={editedTransition}
                  onChange={(e) => setEditedTransition(e.target.value)}
                  rows={2}
                  placeholder="輸入過場銜接語..."
                />
              ) : (
                <p className="slide-script-card__text">
                  {slideScript.transition || "(無過場銜接)"}
                </p>
              )}
            </section>
          )}

          {/* Time Estimate */}
          {isEditing && (
            <section className="slide-script-card__section">
              <h4>⏱️ 預估時間 (分鐘)</h4>
              <input
                type="number"
                className="slide-script-card__time-input"
                value={editedTime}
                onChange={(e) => setEditedTime(parseFloat(e.target.value) || 0)}
                min={0.5}
                max={30}
                step={0.5}
              />
            </section>
          )}

          {/* Actions */}
          <div className="slide-script-card__actions">
            {isEditing ? (
              <>
                <button
                  className="slide-script-card__btn slide-script-card__btn--save"
                  onClick={handleSave}
                >
                  💾 儲存
                </button>
                <button
                  className="slide-script-card__btn slide-script-card__btn--cancel"
                  onClick={handleCancel}
                >
                  取消
                </button>
              </>
            ) : (
              <>
                <button
                  className="slide-script-card__btn slide-script-card__btn--edit"
                  onClick={() => setIsEditing(true)}
                >
                  ✏️ 編輯
                </button>
                <button
                  className="slide-script-card__btn slide-script-card__btn--regenerate"
                  onClick={onRegenerate}
                >
                  🔄 重新生成
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SlideScriptCard;
