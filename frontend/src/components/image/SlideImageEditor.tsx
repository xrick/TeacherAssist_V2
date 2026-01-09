/**
 * SlideImageEditor Component
 *
 * Allows editing images for a specific slide.
 * Shows current image and provides option to change it.
 */

import React, { useState } from "react";
import type { PexelsImage } from "@/types/api";
import { ImagePicker } from "./ImagePicker";
import { pexelsAPI } from "@/api/pexels";

interface SlideImageInfo {
  id: number;
  thumbnailUrl: string;
  photographer: string;
  keyword: string;
}

interface SlideImageEditorProps {
  /** Slide index (0-based) */
  slideIndex: number;
  /** Slide title for context */
  slideTitle: string;
  /** Current image on the slide */
  currentImage?: SlideImageInfo;
  /** Suggested search keyword */
  suggestedKeyword?: string;
  /** Callback when image is changed */
  onImageChange: (slideIndex: number, image: PexelsImage) => void;
  /** Optional callback when image is removed */
  onImageRemove?: (slideIndex: number) => void;
}

export const SlideImageEditor: React.FC<SlideImageEditorProps> = ({
  slideIndex,
  slideTitle,
  currentImage,
  suggestedKeyword,
  onImageChange,
  onImageRemove,
}) => {
  const [showPicker, setShowPicker] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Handle image selection from picker
  const handleImageSelect = async (image: PexelsImage) => {
    setIsLoading(true);
    try {
      // Download and cache the image
      await pexelsAPI.download({
        image_id: image.id,
        keyword: suggestedKeyword || slideTitle,
        size: "large",
      });

      // Notify parent of selection
      onImageChange(slideIndex, image);
      setShowPicker(false);
    } catch (error) {
      console.error("Failed to download image:", error);
      alert("Failed to download image. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // Handle image removal
  const handleRemove = () => {
    if (onImageRemove && window.confirm("Remove this image from the slide?")) {
      onImageRemove(slideIndex);
    }
  };

  return (
    <div className="slide-image-editor">
      <div className="slide-image-editor-header">
        <h4>
          Slide {slideIndex + 1}: {slideTitle}
        </h4>
      </div>

      {/* Current Image Display */}
      {currentImage ? (
        <div className="slide-image-editor-current">
          <img
            src={currentImage.thumbnailUrl}
            alt={`Slide ${slideIndex + 1} image`}
            className="slide-image-editor-thumbnail"
          />
          <div className="slide-image-editor-info">
            <p>Photo by {currentImage.photographer}</p>
            <p className="keyword-tag">Keyword: {currentImage.keyword}</p>
          </div>
          <div className="slide-image-editor-actions">
            <button
              onClick={() => setShowPicker(true)}
              disabled={isLoading}
              className="btn-change"
            >
              Change Image
            </button>
            {onImageRemove && (
              <button
                onClick={handleRemove}
                disabled={isLoading}
                className="btn-remove"
              >
                Remove
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="slide-image-editor-empty">
          <p>No image assigned to this slide</p>
          <button
            onClick={() => setShowPicker(true)}
            disabled={isLoading}
            className="btn-add"
          >
            Add Image
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="slide-image-editor-loading">Downloading image...</div>
      )}

      {/* Image Picker Modal */}
      {showPicker && (
        <div className="slide-image-editor-modal">
          <div className="slide-image-editor-modal-content">
            <ImagePicker
              initialKeyword={
                suggestedKeyword || currentImage?.keyword || slideTitle
              }
              onSelect={handleImageSelect}
              selectedId={currentImage?.id}
              onClose={() => setShowPicker(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default SlideImageEditor;
