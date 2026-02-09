"use client";

import { Transcript, TranscriptSegmentData, Summary } from '@/types';
import { TranscriptView } from '@/components/TranscriptView';
import { VirtualizedTranscriptView } from '@/components/VirtualizedTranscriptView';
import { TranscriptButtonGroup } from './TranscriptButtonGroup';
import { useMemo } from 'react';
import { IncrementalSummaryPanel } from '@/app/_components/IncrementalSummaryPanel';

interface TranscriptPanelProps {
  transcripts: Transcript[];
  customPrompt: string;
  onPromptChange: (value: string) => void;
  onCopyTranscript: () => void;
  onOpenMeetingFolder: () => Promise<void>;
  isRecording: boolean;
  disableAutoScroll?: boolean;
  aiSummary?: Summary | null;

  // Optional pagination props (when using virtualization)
  usePagination?: boolean;
  segments?: TranscriptSegmentData[];
  hasMore?: boolean;
  isLoadingMore?: boolean;
  totalCount?: number;
  loadedCount?: number;
  onLoadMore?: () => void;
}

export function TranscriptPanel({
  transcripts,
  customPrompt,
  onPromptChange,
  onCopyTranscript,
  onOpenMeetingFolder,
  isRecording,
  disableAutoScroll = false,
  aiSummary,
  usePagination = false,
  segments,
  hasMore,
  isLoadingMore,
  totalCount,
  loadedCount,
  onLoadMore,
}: TranscriptPanelProps) {
  // Convert transcripts to segments if pagination is not used but we want virtualization
  const convertedSegments = useMemo(() => {
    if (usePagination && segments) {
      return segments;
    }
    // Convert transcripts to segments for virtualization
    return transcripts.map(t => ({
      id: t.id,
      timestamp: t.audio_start_time ?? 0,
      endTime: t.audio_end_time,
      text: t.text,
      confidence: t.confidence,
    }));
  }, [transcripts, usePagination, segments]);

  return (
    <div className="hidden md:flex md:w-1/4 lg:w-1/3 min-w-0 border-r border-gray-200 bg-white flex-col relative shrink-0">
      {/* Title area */}
      <div className="p-4 border-b border-gray-200">
        <TranscriptButtonGroup
          transcriptCount={usePagination ? (totalCount ?? convertedSegments.length) : (transcripts?.length || 0)}
          onCopyTranscript={onCopyTranscript}
          onOpenMeetingFolder={onOpenMeetingFolder}
        />
      </div>

      {/* Transcript content - use virtualized view for better performance */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden pb-4">
        <div className={!isRecording && aiSummary ? "h-1/2 border-b border-gray-100 overflow-hidden" : "flex-1 overflow-hidden"}>
          <VirtualizedTranscriptView
            segments={convertedSegments}
            isRecording={isRecording}
            isPaused={false}
            isProcessing={false}
            isStopping={false}
            enableStreaming={false}
            showConfidence={true}
            disableAutoScroll={disableAutoScroll}
            hasMore={hasMore}
            isLoadingMore={isLoadingMore}
                      totalCount={totalCount}
                      loadedCount={loadedCount}
                      onLoadMore={onLoadMore}
                      className="scrollbar-hide"
                    />        </div>

        {/* Saved Summary content below transcript */}
        {!isRecording && aiSummary && (
          <div className="flex-1 overflow-y-auto p-4 bg-gray-50 scrollbar-hide">
            <h3 className="text-sm font-semibold text-gray-500 mb-4 uppercase tracking-wider">实时总结回顾</h3>
            <IncrementalSummaryPanel summary={aiSummary as any} />
          </div>
        )}
      </div>

    </div>
  );
}
