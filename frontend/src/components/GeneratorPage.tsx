import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { templateAPI } from "@/api/client";
import { useSSE } from "@/hooks/useSSE";
import type { GenerationRequest, Template } from "@/types/api";
import MarkdownEditor from "./input/MarkdownEditor";
import TemplateGallery from "./template/TemplateGallery";
import GenerationControl from "./generation/GenerationControl";
import ProgressMonitor from "./generation/ProgressMonitor";
import { ResultTabs } from "./result";

export default function GeneratorPage() {
  const [markdown, setMarkdown] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(
    null,
  );
  const [generationOptions, setGenerationOptions] = useState({
    title: "",
    author: "",
    audience: "",
    tone: "professional",
    slideCount: "",
  });

  const sseState = useSSE();

  // Fetch templates
  const { data: templatesData, isLoading: templatesLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: () => templateAPI.list(),
  });

  const handleGenerate = () => {
    const request: GenerationRequest = {
      markdown_content: markdown,
      title: generationOptions.title || undefined,
      author: generationOptions.author || undefined,
      template: selectedTemplate?.id || "default",
      audience: generationOptions.audience || undefined,
      tone: generationOptions.tone || undefined,
      slide_count: generationOptions.slideCount
        ? parseInt(generationOptions.slideCount, 10)
        : undefined,
    };

    sseState.startGeneration(request);
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-10">
        <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg"></div>
              <h1 className="text-xl font-bold text-slate-900 dark:text-white">
                TeacherAssist
              </h1>
              <span className="px-2 py-1 text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">
                Beta
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-slate-600 dark:text-slate-400">
                AI 簡報生成器
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column - Editor & Generation Controls */}
          <div className="space-y-6">
            <MarkdownEditor
              value={markdown}
              onChange={setMarkdown}
              disabled={sseState.isGenerating}
            />

            {/* Generation Controls - moved below Markdown Editor */}
            <GenerationControl
              options={generationOptions}
              onOptionsChange={setGenerationOptions}
              onGenerate={handleGenerate}
              disabled={!markdown.trim() || sseState.isGenerating}
              isGenerating={sseState.isGenerating}
            />
          </div>

          {/* Right Column - Templates & Progress */}
          <div className="space-y-6">
            {/* Template Gallery */}
            <TemplateGallery
              templates={templatesData?.templates || []}
              selectedTemplate={selectedTemplate}
              onSelectTemplate={setSelectedTemplate}
              loading={templatesLoading}
            />

            {/* Progress Monitor */}
            {(sseState.isGenerating || sseState.progress) &&
              !sseState.result && (
                <ProgressMonitor
                  progress={sseState.progress}
                  result={sseState.result}
                  error={sseState.error}
                  isGenerating={sseState.isGenerating}
                  onReset={sseState.reset}
                  onStop={sseState.stopGeneration}
                />
              )}
          </div>
        </div>

        {/* Result Tabs - Full Width Below */}
        {sseState.result && (
          <ResultTabs result={sseState.result} onReset={sseState.reset} />
        )}
      </main>
    </div>
  );
}
