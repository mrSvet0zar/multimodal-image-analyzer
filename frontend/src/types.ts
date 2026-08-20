export interface AnalysisObject {
  name: string;
  confidence: number;
  description?: string | null;
}

export interface Analysis {
  id: string;
  filename: string;
  uploaded_at: string;
  description: string;
  objects: AnalysisObject[];
  sentiment: string;
  tags: string[];
  extracted_text: string;
  processing_time_ms: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  image_url: string;
}

export interface BatchError {
  error: string;
  filename: string;
}

export interface BatchResult {
  total: number;
  successful: number;
  results: (Analysis | BatchError)[];
}

export interface DailyMetric {
  day: string;
  count: number;
  cost_usd: number;
}

export interface Metrics {
  total_analyses: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  avg_processing_time_ms: number;
  model: string;
  by_day: DailyMetric[];
}

export type DetailLevel = 'simple' | 'medium' | 'detailed';
export type ExportFormat = 'json' | 'markdown';

export function isBatchError(r: Analysis | BatchError): r is BatchError {
  return 'error' in r;
}
