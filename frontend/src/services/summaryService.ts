/**
 * Summary Service
 *
 * Handles API calls to the Python backend for incremental summarization.
 */

// Define the structure of the summary response based on the Pydantic models in the backend
// This should match the structure of `SummaryResponse` in `incremental_summarizer.py`
export interface SummaryBlock {
  id: string;
  type: 'bullet' | 'heading1' | 'heading2' | 'text';
  content: string;
  color: string;
}

export interface SummarySection {
  title: string;
  blocks: SummaryBlock[];
}

export interface MeetingNotes {
  meeting_name: string;
  sections: SummarySection[];
}

export interface SummaryResponse {
  meeting_name: string | null;
  people: SummarySection;
  session_summary: SummarySection;
  critical_deadlines: SummarySection;
  key_items_decisions: SummarySection;
  immediate_action_items: SummarySection;
  next_steps: SummarySection;
  meeting_notes: MeetingNotes;
}

const API_BASE_URL = 'http://localhost:5167'; // The address of the Python backend

class SummaryService {
  /**
   * Starts a new incremental summarization session.
   * @param meeting_id The ID of the meeting.
   * @param model_provider The LLM provider (e.g., 'ollama').
   * @param model_name The name of the model to use.
   * @param api_key The API key for the model provider.
   */
  async startIncrementalSummary(meeting_id: string, model_provider: string, model_name: string, api_key?: string | null): Promise<Response> {
    return fetch(`${API_BASE_URL}/v2/summarize/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        meeting_id,
        model_provider,
        model_name,
        custom_prompt: "Summarize the meeting.", // Or get from settings
        api_key,
      }),
    });
  }

  /**
   * Adds a transcript chunk to the current summarization session.
   * @param meeting_id The ID of the meeting.
   * @param text_chunk The new piece of transcript text.
   * @returns The updated summary.
   */
  async addIncrementalSummaryChunk(meeting_id: string, text_chunk: string): Promise<SummaryResponse> {
    const response = await fetch(`${API_BASE_URL}/v2/summarize/add_chunk`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        meeting_id,
        text_chunk,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to add summary chunk');
    }

    return response.json();
  }

  /**
   * Ends the incremental summarization session.
   * @param meeting_id The ID of the meeting.
   */
  async endIncrementalSummary(meeting_id: string): Promise<Response> {
    return fetch(`${API_BASE_URL}/v2/summarize/end`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        meeting_id,
      }),
    });
  }
}

// Export singleton instance
export const summaryService = new SummaryService();
