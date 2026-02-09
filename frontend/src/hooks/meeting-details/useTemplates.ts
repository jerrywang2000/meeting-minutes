import { useState, useEffect, useCallback } from 'react';
import { invoke as invokeTauri } from '@tauri-apps/api/core';
import { toast } from 'sonner';
import Analytics from '@/lib/analytics';

// Translation mapping for template names and descriptions
const TEMPLATE_TRANSLATIONS: Record<string, { name: string; description: string }> = {
  'standard_meeting': {
    name: '标准会议纪要',
    description: '适用于一般会议的通用模板，侧重于关键结果和行动项。'
  },
  'daily_standup': {
    name: '每日站会',
    description: '为工程和产品团队设计的简洁模板，涵盖昨日进展、今日计划和阻碍因素。'
  },
  'project_sync': {
    name: '项目同步',
    description: '侧重于项目进度、里程碑和跨团队协作的模板。'
  },
  'retrospective': {
    name: '回顾会议',
    description: '用于团队总结经验教训、分析优缺点并制定改进计划。'
  },
  'sales_marketing_client_call': {
    name: '销售与客户通话',
    description: '侧重于客户需求、痛点和后续销售机会的模板。'
  },
  'psychatric_session': {
    name: '访谈/会谈',
    description: '适用于一对一会谈或深度访谈的详细记录模板。'
  }
};

export function useTemplates() {
  const [availableTemplates, setAvailableTemplates] = useState<Array<{
    id: string;
    name: string;
    description: string;
  }>>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('standard_meeting');

  // Fetch available templates on mount
  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        const templates = await invokeTauri('api_list_templates') as Array<{
          id: string;
          name: string;
          description: string;
        }>;
        
        // Translate templates
        const translatedTemplates = templates.map(template => {
          const translation = TEMPLATE_TRANSLATIONS[template.id];
          return translation ? {
            ...template,
            name: translation.name,
            description: translation.description
          } : template;
        });

        console.log('Available templates (translated):', translatedTemplates);
        setAvailableTemplates(translatedTemplates);
      } catch (error) {
        console.error('Failed to fetch templates:', error);
      }
    };
    fetchTemplates();
  }, []);

  // Handle template selection
  const handleTemplateSelection = useCallback((templateId: string, templateName: string) => {
    setSelectedTemplate(templateId);
    toast.success('模板已选择', {
      description: `已切换至 "${templateName}" 模板用于生成纪要`,
    });
    Analytics.trackFeatureUsed('template_selected');
  }, []);

  return {
    availableTemplates,
    selectedTemplate,
    handleTemplateSelection,
  };
}
