import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Globe } from 'lucide-react';
import Analytics from '@/lib/analytics';
import { toast } from 'sonner';

export interface Language {
  code: string;
  name: string;
}

// ISO 639-1 language codes supported by Whisper
const LANGUAGES: Language[] = [
  { code: 'auto', name: '自动检测 (原始语言)' },
  { code: 'auto-translate', name: '自动检测 (翻译为英文)' },
  { code: 'en', name: '英语' },
  { code: 'zh', name: '中文' },
  { code: 'de', name: '德语' },
  { code: 'es', name: '西班牙语' },
  { code: 'ru', name: '俄语' },
  { code: 'ko', name: '韩语' },
  { code: 'fr', name: '法语' },
  { code: 'ja', name: '日语' },
  { code: 'pt', name: '葡萄牙语' },
  { code: 'tr', name: '土耳其语' },
  { code: 'pl', name: '波兰语' },
  { code: 'ca', name: '加泰罗尼亚语' },
  { code: 'nl', name: '荷兰语' },
  { code: 'ar', name: '阿拉伯语' },
  { code: 'sv', name: '瑞典语' },
  { code: 'it', name: '意大利语' },
  { code: 'id', name: '印度尼西亚语' },
  { code: 'hi', name: '印地语' },
  { code: 'fi', name: '芬兰语' },
  { code: 'vi', name: '越南语' },
  { code: 'he', name: '希伯来语' },
  { code: 'uk', name: '乌克兰语' },
  { code: 'el', name: '希腊语' },
  { code: 'ms', name: '马来语' },
  { code: 'cs', name: '捷克语' },
  { code: 'ro', name: '罗马尼亚语' },
  { code: 'da', name: '丹麦语' },
  { code: 'hu', name: '匈牙利语' },
  { code: 'ta', name: '泰米尔语' },
  { code: 'no', name: '挪威语' },
  { code: 'th', name: '泰语' },
  { code: 'ur', name: '乌尔都语' },
  { code: 'hr', name: '克罗地亚语' },
  { code: 'bg', name: '保加利亚语' },
  { code: 'lt', name: '立陶宛语' },
  { code: 'la', name: '拉丁语' },
  { code: 'mi', name: '毛利语' },
  { code: 'ml', name: '马拉雅拉姆语' },
  { code: 'cy', name: '威尔士语' },
  { code: 'sk', name: '斯洛伐克语' },
  { code: 'te', name: '泰卢固语' },
  { code: 'fa', name: '波斯语' },
  { code: 'lv', name: '拉脱维亚语' },
  { code: 'bn', name: '孟加拉语' },
  { code: 'sr', name: '塞尔维亚语' },
  { code: 'az', name: '阿塞拜疆语' },
  { code: 'sl', name: '斯洛文尼亚语' },
  { code: 'kn', name: '卡纳达语' },
  { code: 'et', name: '爱沙尼亚语' },
  { code: 'mk', name: '马其顿语' },
  { code: 'br', name: '布列塔尼语' },
  { code: 'eu', name: '巴斯克语' },
  { code: 'is', name: '冰岛语' },
  { code: 'hy', name: '亚美尼亚语' },
  { code: 'ne', name: '尼泊尔语' },
  { code: 'mn', name: '蒙古语' },
  { code: 'bs', name: '波斯尼亚语' },
  { code: 'kk', name: '哈萨克语' },
  { code: 'sq', name: '阿尔巴尼亚语' },
  { code: 'sw', name: '斯瓦希里语' },
  { code: 'gl', name: '加利西亚语' },
  { code: 'mr', name: '马拉地语' },
  { code: 'pa', name: '旁遮普语' },
  { code: 'si', name: '僧伽罗语' },
  { code: 'km', name: '高棉语' },
  { code: 'sn', name: '绍纳语' },
  { code: 'yo', name: '约鲁巴语' },
  { code: 'so', name: '索马里语' },
  { code: 'af', name: '南非语' },
  { code: 'oc', name: '奥克语' },
  { code: 'ka', name: '格鲁吉亚语' },
  { code: 'be', name: '白俄罗斯语' },
  { code: 'tg', name: '塔吉克语' },
  { code: 'sd', name: '信德语' },
  { code: 'gu', name: '古吉拉特语' },
  { code: 'am', name: '阿姆哈拉语' },
  { code: 'yi', name: '意第绪语' },
  { code: 'lo', name: '老挝语' },
  { code: 'uz', name: '乌兹别克语' },
  { code: 'fo', name: '法罗语' },
  { code: 'ht', name: '海地克里奥尔语' },
  { code: 'ps', name: '普什图语' },
  { code: 'tk', name: '土库曼语' },
  { code: 'nn', name: '新挪威语' },
  { code: 'mt', name: '马耳他语' },
  { code: 'sa', name: '梵语' },
  { code: 'lb', name: '卢森堡语' },
  { code: 'my', name: '缅甸语' },
  { code: 'bo', name: '藏语' },
  { code: 'tl', name: '塔加洛语' },
  { code: 'mg', name: '马尔加什语' },
  { code: 'as', name: '阿萨姆语' },
  { code: 'tt', name: '鞑靼语' },
  { code: 'haw', name: '夏威夷语' },
  { code: 'ln', name: '林加拉语' },
  { code: 'ha', name: '豪萨语' },
  { code: 'ba', name: '巴什基尔语' },
  { code: 'jw', name: '爪哇语' },
  { code: 'su', name: '巽他语' },
];

interface LanguageSelectionProps {
  selectedLanguage: string;
  onLanguageChange: (language: string) => void;
  disabled?: boolean;
  provider?: 'localWhisper' | 'parakeet' | 'deepgram' | 'elevenLabs' | 'groq' | 'openai';
}

export function LanguageSelection({
  selectedLanguage,
  onLanguageChange,
  disabled = false,
  provider = 'localWhisper'
}: LanguageSelectionProps) {
  const [saving, setSaving] = useState(false);

  // Parakeet only supports auto-detection (doesn't support manual language selection)
  const isParakeet = provider === 'parakeet';
  const availableLanguages = isParakeet
    ? LANGUAGES.filter(lang => lang.code === 'auto' || lang.code === 'auto-translate')
    : LANGUAGES;

  const handleLanguageChange = async (languageCode: string) => {
    setSaving(true);
    try {
      // Save language preference to backend
      await invoke('set_language_preference', { language: languageCode });
      onLanguageChange(languageCode);
      console.log('Language preference saved:', languageCode);

      // Track language selection analytics
      const selectedLang = LANGUAGES.find(lang => lang.code === languageCode);
      await Analytics.track('language_selected', {
        language_code: languageCode,
        language_name: selectedLang?.name || 'Unknown',
        is_auto_detect: (languageCode === 'auto').toString(),
        is_auto_translate: (languageCode === 'auto-translate').toString()
      });

      // Show success toast
      const languageName = selectedLang?.name || languageCode;
      toast.success("语言偏好已保存", {
        description: `语音转录语言已设置为 ${languageName}`
      });
    } catch (error) {
      console.error('Failed to save language preference:', error);
      toast.error("保存语言偏好失败", {
        description: error instanceof Error ? error.message : String(error)
      });
    } finally {
      setSaving(false);
    }
  };

  // Find the selected language name for display
  const selectedLanguageName = LANGUAGES.find(
    lang => lang.code === selectedLanguage
  )?.name || '自动检测 (原始语言)';

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe className="h-4 w-4 text-gray-600" />
          <h4 className="text-sm font-medium text-gray-900">转录语言</h4>
        </div>
      </div>

      <div className="space-y-2">
        <select
          value={selectedLanguage}
          onChange={(e) => handleLanguageChange(e.target.value)}
          disabled={disabled || saving}
          className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
        >
          {availableLanguages.map((language) => (
            <option key={language.code} value={language.code}>
              {language.name}
              {language.code !== 'auto' && language.code !== 'auto-translate' && ` (${language.code})`}
            </option>
          ))}
        </select>

        {/* Parakeet language limitation warning */}
        {isParakeet && (
          <div className="p-2 bg-amber-50 border border-amber-200 rounded text-amber-800">
            <p className="font-medium">ℹ️ Parakeet 语言支持</p>
            <p className="mt-1 text-xs">Parakeet 目前仅支持自动语言检测。手动语言选择不可用。如果需要指定特定语言，请使用 Whisper。</p>
          </div>
        )}

        {/* Info text */}
        <div className="text-xs space-y-2 pt-2">
          <p className="text-gray-600">
            <strong>当前设置:</strong> {selectedLanguageName}
          </p>
          {selectedLanguage === 'auto' && (
            <div className="p-2 bg-yellow-50 border border-yellow-200 rounded text-yellow-800">
              <p className="font-medium">⚠️ 自动检测可能会产生不准确的结果</p>
              <p className="mt-1">为了获得最佳准确度，请选择您的特定语言（例如：中文、英语等）</p>
            </div>
          )}
          {selectedLanguage === 'auto-translate' && (
            <div className="p-2 bg-blue-50 border border-blue-200 rounded text-blue-800">
              <p className="font-medium">🌐 翻译模式已启用</p>
              <p className="mt-1">所有音频将自动翻译为英文。最适合您需要英文输出的多语言会议。</p>
            </div>
          )}
          {selectedLanguage !== 'auto' && selectedLanguage !== 'auto-translate' && (
            <p className="text-gray-600">
              转录将针对 <strong>{selectedLanguageName}</strong> 进行优化
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
