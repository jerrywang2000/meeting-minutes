'use client';

import { SummaryResponse, SummarySection } from '@/services/summaryService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { motion } from 'framer-motion';

interface IncrementalSummaryPanelProps {
  summary: SummaryResponse | null;
}

const SectionCard = ({ title, section }: { title: string, section: SummarySection | undefined }) => {
  if (!section || section.blocks.length === 0) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mb-4"
    >
      <Card>
        <CardHeader className="p-4">
          <CardTitle className="text-md font-semibold">{title}</CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0 text-sm">
          {section.blocks.map(block => (
            <p key={block.id} className="mb-1">{block.content}</p>
          ))}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export function IncrementalSummaryPanel({ summary }: IncrementalSummaryPanelProps) {
  // Helper to get section regardless of casing (handles backend alias vs field name)
  const getSection = (key: keyof SummaryResponse): SummarySection | undefined => {
    if (!summary) return undefined;
    
    // Try original key (e.g., session_summary)
    if (summary[key]) return summary[key] as SummarySection;
    
    // Try PascalCase alias (e.g., SessionSummary)
    const pascalKey = key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join('') as any;
    if ((summary as any)[pascalKey]) return (summary as any)[pascalKey];
    
    return undefined;
  };

  if (!summary) {
    return (
      <div className="w-full h-full p-4 bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Live summary will appear here...</p>
      </div>
    );
  }

  const sections = {
    immediate_action_items: getSection('immediate_action_items'),
    key_items_decisions: getSection('key_items_decisions'),
    next_steps: getSection('next_steps'),
    people: getSection('people'),
    critical_deadlines: getSection('critical_deadlines'),
    session_summary: getSection('session_summary'),
  };

  const isSummaryEmpty = 
    !sections.people?.blocks?.length &&
    !sections.session_summary?.blocks?.length &&
    !sections.critical_deadlines?.blocks?.length &&
    !sections.key_items_decisions?.blocks?.length &&
    !sections.immediate_action_items?.blocks?.length &&
    !sections.next_steps?.blocks?.length;

  if (isSummaryEmpty) {
    return (
      <div className="w-full h-full p-4 bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 animate-pulse">Summary is generating...</p>
          <p className="text-xs text-gray-400 mt-2">Continue talking to see updates.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full p-4 bg-gray-50 overflow-y-auto">
      <h2 className="text-lg font-bold mb-4">{summary.meeting_name || (summary as any).MeetingName || 'Live Meeting Summary'}</h2>
      
      <SectionCard title="Action Items" section={sections.immediate_action_items} />
      <SectionCard title="Key Decisions" section={sections.key_items_decisions} />
      <SectionCard title="Next Steps" section={sections.next_steps} />
      <SectionCard title="People" section={sections.people} />
      <SectionCard title="Deadlines" section={sections.critical_deadlines} />
      <SectionCard title="General Summary" section={sections.session_summary} />

    </div>
  );
}
