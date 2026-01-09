/**
 * ImagePicker Component
 *
 * Displays a grid of Pexels images for selection.
 * Supports search, pagination, and image preview.
 */

import React, { useState, useCallback } from "react";
import type { PexelsImage, ImageSearchResponse } from "@/types/api";
import { pexelsAPI } from "@/api/pexels";

interface ImagePickerProps {
  /** Initial search keyword */
  initialKeyword?: string;
  /** Callback when an image is selected */
  onSelect: (image: PexelsImage) => void;
  /** Currently selected image ID */
  selectedId?: number;
  /** Optional callback when picker is closed */
  onClose?: () => void;
  /** Number of images per page */
  perPage?: number;
}

export const ImagePicker: React.FC<ImagePickerProps> = ({
  initialKeyword = "",
  onSelect,
  selectedId,
  onClose,
  perPage = 9,
}) => {
  const [keyword, setKeyword] = useState(initialKeyword);
  const [searchInput, setSearchInput] = useState(initialKeyword);
  const [images, setImages] = useState<PexelsImage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalResults, setTotalResults] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [previewImage, setPreviewImage] = useState<PexelsImage | null>(null);

  // Search for images
  const searchImages = useCallback(
    async (searchKeyword: string, pageNum: number = 1) => {
      if (!searchKeyword.trim()) {
        setError("Please enter a search keyword");
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response: ImageSearchResponse = await pexelsAPI.search(
          searchKeyword,
          {
            per_page: perPage,
            page: pageNum,
            orientation: "landscape",
          },
        );

        setImages(response.photos);
        setTotalResults(response.total_results);
        setHasNext(response.has_next);
        setPage(pageNum);
        setKeyword(searchKeyword);
      } catch (err) {
        console.error("Image search failed:", err);
        setError("Failed to search images. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [perPage],
  );

  // Handle search form submission
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    searchImages(searchInput, 1);
  };

  // Handle pagination
  const handlePrevPage = () => {
    if (page > 1) {
      searchImages(keyword, page - 1);
    }
  };

  const handleNextPage = () => {
    if (hasNext) {
      searchImages(keyword, page + 1);
    }
  };

  // Handle image selection
  const handleImageClick = (image: PexelsImage) => {
    onSelect(image);
  };

  // Handle image preview
  const handlePreviewClick = (e: React.MouseEvent, image: PexelsImage) => {
    e.stopPropagation();
    setPreviewImage(image);
  };

  // Initial search on mount if keyword provided
  React.useEffect(() => {
    if (initialKeyword) {
      searchImages(initialKeyword, 1);
    }
  }, [initialKeyword, searchImages]);

  return (
    <div className="image-picker">
      {/* Search Form */}
      <form onSubmit={handleSearch} className="image-picker-search">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search for images..."
          className="image-picker-input"
        />
        <button
          type="submit"
          disabled={loading}
          className="image-picker-search-btn"
        >
          {loading ? "Searching..." : "Search"}
        </button>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="image-picker-close-btn"
          >
            Close
          </button>
        )}
      </form>

      {/* Error Message */}
      {error && <div className="image-picker-error">{error}</div>}

      {/* Results Info */}
      {totalResults > 0 && (
        <div className="image-picker-info">
          Found {totalResults.toLocaleString()} images for "{keyword}"
        </div>
      )}

      {/* Image Grid */}
      <div className="image-picker-grid">
        {images.map((image) => (
          <div
            key={image.id}
            className={`image-picker-item ${
              selectedId === image.id ? "selected" : ""
            }`}
            onClick={() => handleImageClick(image)}
          >
            <img
              src={pexelsAPI.getThumbnailUrl(image)}
              alt={image.alt || "Pexels image"}
              loading="lazy"
            />
            <div className="image-picker-item-overlay">
              <span className="image-picker-photographer">
                Photo by {image.photographer}
              </span>
              <button
                className="image-picker-preview-btn"
                onClick={(e) => handlePreviewClick(e, image)}
              >
                Preview
              </button>
            </div>
            {selectedId === image.id && (
              <div className="image-picker-selected-badge">Selected</div>
            )}
          </div>
        ))}
      </div>

      {/* Empty State */}
      {!loading && images.length === 0 && keyword && (
        <div className="image-picker-empty">
          No images found for "{keyword}". Try a different search term.
        </div>
      )}

      {/* Pagination */}
      {images.length > 0 && (
        <div className="image-picker-pagination">
          <button onClick={handlePrevPage} disabled={page <= 1 || loading}>
            Previous
          </button>
          <span>Page {page}</span>
          <button onClick={handleNextPage} disabled={!hasNext || loading}>
            Next
          </button>
        </div>
      )}

      {/* Image Preview Modal */}
      {previewImage && (
        <div
          className="image-picker-modal"
          onClick={() => setPreviewImage(null)}
        >
          <div
            className="image-picker-modal-content"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={pexelsAPI.getPreviewUrl(previewImage)}
              alt={previewImage.alt || "Preview"}
            />
            <div className="image-picker-modal-info">
              <p>
                <strong>Photographer:</strong> {previewImage.photographer}
              </p>
              <p>
                <strong>Size:</strong> {previewImage.width} x{" "}
                {previewImage.height}
              </p>
              <p>
                <strong>Description:</strong>{" "}
                {previewImage.alt || "No description"}
              </p>
            </div>
            <div className="image-picker-modal-actions">
              <button onClick={() => handleImageClick(previewImage)}>
                Select This Image
              </button>
              <button onClick={() => setPreviewImage(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImagePicker;
