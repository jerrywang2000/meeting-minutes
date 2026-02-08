'use client';

import { SummaryResponse, SummarySection } from '@/services/summaryService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { motion } from 'framer-motion';

interface IncrementalSummaryPanelProps {
  summary: SummaryResponse | null;
}

interface SectionCardProps {
  title: string;
  section: SummarySection | undefined;
  type?: 'bullet' | 'action' | 'default';
}

const SectionCard = ({ title, section, type = 'default' }: SectionCardProps) => {
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
        <CardHeader className="p-4 pb-2">
          <CardTitle className="text-sm font-bold uppercase tracking-wider text-gray-500">{title}</CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0 text-sm">
          {section.blocks.map(block => (
            <div key={block.id} className="flex items-start mb-2 group">
              {type === 'bullet' && (
                <span className="mr-2 mt-1 text-gray-400">•</span>
              )}
              {type === 'action' && (
                <input 
                  type="checkbox" 
                  className="mr-3 mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                  onClick={(e) => e.stopPropagation()}
                />
              )}
              <p className={type === 'action' ? 'text-gray-700' : 'text-gray-600'}>
                {block.content}
              </p>
            </div>
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
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900">{summary.meeting_name || (summary as any).MeetingName || 'Live Meeting Summary'}</h2>
        <div className="h-1 w-12 bg-blue-500 mt-2 rounded-full"></div>
      </div>
      
      <SectionCard title="Action Items" section={sections.immediate_action_items} type="action" />
      <SectionCard title="Key Decisions" section={sections.key_items_decisions} type="bullet" />
      <SectionCard title="Next Steps" section={sections.next_steps} type="action" />
      <SectionCard title="People" section={sections.people} type="bullet" />
      <SectionCard title="Deadlines" section={sections.critical_deadlines} type="bullet" />
      <SectionCard title="General Summary" section={sections.session_summary} type="bullet" />

    </div>
  );
}
