export type UserRole = "CUSTOMER" | "AGENT" | "ADMIN" | "RISK_ANALYST";

export interface UserProfile {
  id: string;
  phone: string;
  email: string;
  role: UserRole;
  status: string;
  is_frozen: boolean;
  profile?: {
    full_name?: string;
    profession?: string;
    location?: string;
    wallet_balance?: number;
    grace_balance?: number;
    reliability_score?: number;
    agent_code?: string;
    store_name?: string;
    cash_balance?: number;
    float_balance?: number;
    is_factory_zone?: boolean;
  };
}

export interface TransactionItem {
  id: string;
  transaction_reference: string;
  sender_phone?: string;
  receiver_phone?: string;
  amount: number;
  fee: number;
  transaction_type: string;
  status: string;
  category?: string;
  description?: string;
  is_flagged_fraud: boolean;
  created_at: string;
}

export interface CashFlowPoint {
  date: string;
  day_of_month: number;
  inflow_forecast: number;
  outflow_forecast: number;
  projected_balance: number;
  deficit_warning: boolean;
}

export interface CashFlowTrajectory {
  current_balance: number;
  start_date: string;
  has_deficit_alert: boolean;
  deficit_alert?: {
    alert_level: string;
    days_until_deficit: number;
    deficit_date: string;
    projected_shortfall: number;
    recommended_action: string;
  };
  projected_30d_end_balance: number;
  lowest_projected_balance: number;
  highest_projected_balance: number;
  daily_forecast: CashFlowPoint[];
}

export interface GraceEligibility {
  eligible: boolean;
  credit_score: number;
  approved_limit: number;
  current_grace_balance: number;
  repayment_likelihood_pct: number;
  positive_factors: string[];
  risk_factors: string[];
  decision: string;
  message: string;
}

export interface FDROption {
  term_days: number;
  interest_rate_pct: number;
  projected_profit: number;
  total_maturity_amount: number;
}

export interface FDRRecommendation {
  idle_balance_detected: number;
  recommended_deposit: number;
  minimum_threshold: number;
  is_eligible: boolean;
  options: FDROption[];
  message: string;
}

export interface FDRAccount {
  id: string;
  customer_id: string;
  principal_amount: number;
  term_days: number;
  interest_rate_pct: number;
  start_date: string;
  maturity_date: string;
  status: string;
  projected_profit: number;
  total_at_maturity: number;
}

export interface VoiceCoachMessage {
  id: string;
  sender: "user" | "coach";
  text: string;
  intent?: string;
  latency_ms?: number;
  timestamp: string;
}

export interface AgentLiquidityPoint {
  date: string;
  day_of_week: string;
  predicted_cash_out: number;
  recommended_float: number;
  surge_flag: boolean;
  surge_reason?: string;
}

export interface AgentLiquidityForecast {
  agent_code: string;
  store_name: string;
  location_cluster: string;
  is_factory_zone: boolean;
  current_cash_balance: number;
  current_float_balance: number;
  total_7d_predicted_cash_out: number;
  stockout_risk: string;
  days_until_stockout?: number;
  rebalance_suggestion: {
    action: string;
    recommended_amount: number;
    reason: string;
  };
  daily_forecast: AgentLiquidityPoint[];
}

export interface GraphNode {
  id: string;
  label: string;
  node_type: string;
  risk_score: number;
  in_degree: number;
  out_degree: number;
  total_sent: number;
  total_received: number;
  pagerank: number;
  cluster_id?: string;
  is_agent: boolean;
  is_frozen: boolean;
  reasons: string[];
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  amount: number;
  tx_count: number;
  is_cash_out: boolean;
  cluster_id?: string;
}

export interface GraphTopology {
  nodes: GraphNode[];
  edges: GraphEdge[];
  clusters: {
    cluster_id: string;
    size: number;
    total_volume: number;
    nodes: string[];
  }[];
  summary: {
    total_nodes: number;
    total_edges: number;
    mule_nodes_detected: number;
    clusters_detected: number;
  };
}

export interface ScamReportItem {
  id: string;
  reporter_id: string;
  reported_account: string;
  transaction_id?: string;
  reason: string;
  status: "SUBMITTED" | "ANALYZING" | "CONFIRMED_FRAUD" | "DISMISSED";
  cluster_id?: string;
  investigation_notes?: string;
  created_at: string;
}

export interface AppealItem {
  id: string;
  user_id: string;
  user_phone?: string;
  user_email?: string;
  category: string;
  status: "PENDING" | "UNDER_REVIEW" | "APPROVED" | "REJECTED";
  explanation: string;
  transaction_reference?: string;
  supporting_document_ref?: string;
  reviewed_by_id?: string;
  reviewer_email?: string;
  review_action?: string;
  review_notes?: string;
  created_at?: string;
  resolved_at?: string;
}
