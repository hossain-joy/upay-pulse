import React, { useState, useEffect, useRef } from "react";
import {
  Wallet,
  Send,
  ShieldAlert,
  ShieldCheck,
  Mic,
  MicOff,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  Lock,
  Unlock,
  Clock,
  ArrowUpRight,
  ArrowDownLeft,
  CheckCircle2,
  Volume2,
  RefreshCw,
  Coins,
  ChevronRight,
  CreditCard,
  Flag,
  X,
  FileText,
  BadgeCheck,
  Building2,
  Receipt
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from "recharts";
import { apiRequest } from "../api/client";
import {
  UserProfile,
  CashFlowTrajectory,
  GraceEligibility,
  FDRRecommendation,
  FDRAccount,
  VoiceCoachMessage,
  TransactionItem
} from "../types";

interface CustomerPortalProps {
  user?: UserProfile;
  onRefreshUser?: () => void;
  onNotify?: (msg: string, type: 'success' | 'error' | 'info') => void;
}

const defaultUser: UserProfile = {
  id: "usr-demo-001",
  phone: "+8801700000001",
  email: "customer@example.com",
  role: "CUSTOMER",
  status: "ACTIVE",
  is_frozen: false,
  profile: {
    full_name: "Tariqul Islam (Garment Worker)",
    profession: "Senior Sewing Operator",
    location: "Savar, Dhaka",
    wallet_balance: 500.0,
    grace_balance: 0.0,
    reliability_score: 88.5,
  }
};

export const CustomerPortal: React.FC<CustomerPortalProps> = ({ user: propUser, onRefreshUser, onNotify }) => {
  const [currentUser, setCurrentUser] = useState<UserProfile>(propUser || defaultUser);

  const refreshCurrentUser = async () => {
    try {
      const res = await apiRequest<UserProfile>('/auth/me');
      if (res && res.id) {
        setCurrentUser(res);
      }
    } catch {}
  };

  useEffect(() => {
    if (propUser) {
      setCurrentUser(propUser);
    } else {
      refreshCurrentUser();
    }
  }, [propUser]);

  const user = currentUser;

  // Tabs
  const [activeTab, setActiveTab] = useState<"overview" | "coach" | "cashflow" | "grace" | "fdr" | "history">("overview");
  const [transferMode, setTransferMode] = useState<"send" | "cashout">("send");

  // Telemetry data
  const [trajectory, setTrajectory] = useState<CashFlowTrajectory | null>(null);
  const [graceEligibility, setGraceEligibility] = useState<GraceEligibility | null>(null);
  const [fdrRec, setFdrRec] = useState<FDRRecommendation | null>(null);
  const [fdrAccounts, setFdrAccounts] = useState<FDRAccount[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Send Money Form
  const [sendRecipient, setSendRecipient] = useState("+8801700000002");
  const [sendAmount, setSendAmount] = useState("50");
  const [sendCategory, setSendCategory] = useState("PeerTransfer");
  const [applyGraceIfNeeded, setApplyGraceIfNeeded] = useState(true);
  const [sendSuccessMsg, setSendSuccessMsg] = useState<string | null>(null);
  const [sendErrorMsg, setSendErrorMsg] = useState<string | null>(null);

  // Cash Out Form
  const [cashOutAgent, setCashOutAgent] = useState("AGT-1001");
  const [cashOutAmount, setCashOutAmount] = useState("100");
  const [cashOutSuccessMsg, setCashOutSuccessMsg] = useState<string | null>(null);
  const [cashOutErrorMsg, setCashOutErrorMsg] = useState<string | null>(null);
  const [isCashOutLoading, setIsCashOutLoading] = useState(false);

  // Dynamic Badge Modal & Nonce Countdown
  const [activeBadge, setActiveBadge] = useState<any | null>(null);
  const [badgeCountdown, setBadgeCountdown] = useState<number>(60);

  // Master Freeze Modal
  const [isFreezeModalOpen, setIsFreezeModalOpen] = useState(false);
  const [freezePin, setFreezePin] = useState("");
  const [freezeResult, setFreezeResult] = useState<any | null>(null);
  const [freezeError, setFreezeError] = useState<string | null>(null);

  // Unfreeze Modal
  const [isUnfreezeModalOpen, setIsUnfreezeModalOpen] = useState(false);
  const [unfreezeCode, setUnfreezeCode] = useState("123456");
  const [unfreezeError, setUnfreezeError] = useState<string | null>(null);
  const [unfreezeSuccess, setUnfreezeSuccess] = useState<string | null>(null);
  const [isUnfreezing, setIsUnfreezing] = useState(false);

  // Citizen Scam Report Modal
  const [isScamModalOpen, setIsScamModalOpen] = useState(false);
  const [scamReportedAccount, setScamReportedAccount] = useState("");
  const [scamReason, setScamReason] = useState("Lottery / Prize Fake Agent");
  const [scamTxnId, setScamTxnId] = useState("");
  const [scamNotes, setScamNotes] = useState("");
  const [isSubmittingScam, setIsSubmittingScam] = useState(false);
  const [scamSuccessMsg, setScamSuccessMsg] = useState<string | null>(null);

  // Grace Request Modal
  const [isGraceModalOpen, setIsGraceModalOpen] = useState(false);
  const [graceAmountInput, setGraceAmountInput] = useState("20");
  const [graceStatusMsg, setGraceStatusMsg] = useState<string | null>(null);

  // FDR Deposit & Liquidation
  const [fdrDepositInput, setFdrDepositInput] = useState("200");
  const [selectedTerm, setSelectedTerm] = useState(30);
  const [fdrSuccessMsg, setFdrSuccessMsg] = useState<string | null>(null);
  const [liquidatingFdrId, setLiquidatingFdrId] = useState<string | null>(null);

  // Voice Coach
  const [voiceMessages, setVoiceMessages] = useState<VoiceCoachMessage[]>([
    {
      id: "welcome",
      sender: "coach",
      text: "নমস্কার! আমি উপায় পালস এআই আর্থিক পরামর্শক (Google Gemini 2.5 Flash চালিত)। আপনার ব্যালেন্স, গ্রেস লোন বা আসন্ন বিল সম্পর্কে যেকোনো প্রশ্ন করুন।",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [voiceInput, setVoiceInput] = useState("");
  const [isCoachThinking, setIsCoachThinking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Fetch initial CustomerAI data
  useEffect(() => {
    fetchCustomerAIData();
    fetchTransactionHistory();
  }, [user.id]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [voiceMessages, isCoachThinking]);

  // Dynamic Badge 60-Second Countdown & Auto-Refresh
  useEffect(() => {
    if (!activeBadge) {
      setBadgeCountdown(60);
      return;
    }

    const timer = setInterval(async () => {
      setBadgeCountdown((prev) => {
        if (prev <= 1) {
          // Re-fetch rotated badge from backend
          if (activeBadge.transaction_reference) {
            apiRequest(`/badge/generate/${activeBadge.transaction_reference}`)
              .then((newBadge) => {
                if (newBadge) setActiveBadge(newBadge);
              })
              .catch(() => {});
          }
          return 60;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [activeBadge]);

  const fetchCustomerAIData = async () => {
    setIsLoading(true);
    try {
      const [traj, grace, rec, accounts] = await Promise.all([
        apiRequest<CashFlowTrajectory>("/customer-ai/trajectory").catch(() => null),
        apiRequest<GraceEligibility>("/customer-ai/grace/eligibility").catch(() => null),
        apiRequest<FDRRecommendation>("/customer-ai/fdr/recommendation").catch(() => null),
        apiRequest<FDRAccount[]>("/customer-ai/fdr/accounts").catch(() => []),
      ]);

      if (traj) setTrajectory(traj);
      if (grace) setGraceEligibility(grace);
      if (rec) setFdrRec(rec);
      if (accounts) setFdrAccounts(accounts);
    } catch (err) {
      console.error("Error loading CustomerAI data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchTransactionHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const data = await apiRequest<any>("/transactions/history?page=1&page_size=20");
      if (data && data.items) {
        setTransactions(data.items);
      }
    } catch (err) {
      console.warn("Could not load transaction history:", err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Handle Send Money
  const handleSendMoney = async (e: React.FormEvent) => {
    e.preventDefault();
    setSendSuccessMsg(null);
    setSendErrorMsg(null);

    try {
      const res = await apiRequest("/transactions/send", {
        method: "POST",
        body: JSON.stringify({
          receiver_identifier: sendRecipient,
          amount: parseFloat(sendAmount),
          category: sendCategory,
          description: "Customer App Transfer",
          apply_grace_if_needed: applyGraceIfNeeded,
          idempotency_key: `KEY-${Date.now()}`
        })
      });

      setSendSuccessMsg(`টাকা পাঠানো সফল হয়েছে! রেফারেন্স: ${res.transaction_reference} (৳${res.amount})`);
      onNotify?.(`টাকা পাঠানো সফল! ৳${res.amount} sent to ${sendRecipient}`, 'success');
      refreshCurrentUser();
      onRefreshUser?.();
      fetchCustomerAIData();
      fetchTransactionHistory();

      // Fetch dynamic badge for this transfer
      const badgeRes = await apiRequest(`/badge/generate/${res.transaction_reference}`).catch(() => null);
      if (badgeRes) setActiveBadge(badgeRes);
    } catch (err: any) {
      setSendErrorMsg(err.message || "লেনদেন সম্পন্ন হতে ব্যর্থ হয়েছে।");
      onNotify?.(err.message || "লেনদেন ব্যর্থ হয়েছে", 'error');
    }
  };

  // Handle Cash-Out at Agent Counter
  const handleCashOut = async (e: React.FormEvent) => {
    e.preventDefault();
    setCashOutSuccessMsg(null);
    setCashOutErrorMsg(null);
    setIsCashOutLoading(true);

    try {
      const res = await apiRequest("/transactions/cash-out", {
        method: "POST",
        body: JSON.stringify({
          agent_identifier: cashOutAgent,
          amount: parseFloat(cashOutAmount),
          idempotency_key: `CASHOUT-${Date.now()}`
        })
      });

      setCashOutSuccessMsg(`টাকা উত্তোলন সফল হয়েছে! এজেন্ট: ${res.agent_code || cashOutAgent}, পরিমাণ: ৳${res.amount} (ফি: ৳${res.fee})`);
      onNotify?.(`Cash-out successful! ৳${res.amount} withdrawn from agent counter.`, 'success');
      refreshCurrentUser();
      onRefreshUser?.();
      fetchCustomerAIData();
      fetchTransactionHistory();

      // Fetch dynamic badge for this cash out receipt
      const badgeRes = await apiRequest(`/badge/generate/${res.transaction_reference}`).catch(() => null);
      if (badgeRes) setActiveBadge(badgeRes);
    } catch (err: any) {
      setCashOutErrorMsg(err.message || "টাকা উত্তোলন সম্পন্ন হতে ব্যর্থ হয়েছে।");
      onNotify?.(err.message || "টাকা উত্তোলন ব্যর্থ", 'error');
    } finally {
      setIsCashOutLoading(false);
    }
  };

  // Handle Voice Coach Query
  const handleSendVoiceQuery = async (queryText: string) => {
    if (!queryText.trim()) return;

    const userMsg: VoiceCoachMessage = {
      id: `u-${Date.now()}`,
      sender: "user",
      text: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setVoiceMessages((prev) => [...prev, userMsg]);
    setVoiceInput("");
    setIsCoachThinking(true);

    try {
      const res = await apiRequest("/customer-ai/voice-coach/chat", {
        method: "POST",
        body: JSON.stringify({
          query: queryText,
          language: "bn"
        })
      });

      const coachMsg: VoiceCoachMessage = {
        id: res.session_id,
        sender: "coach",
        text: res.response_bangla,
        intent: res.intent,
        latency_ms: res.latency_ms,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setVoiceMessages((prev) => [...prev, coachMsg]);
    } catch (err: any) {
      const errMsg: VoiceCoachMessage = {
        id: `err-${Date.now()}`,
        sender: "coach",
        text: "দুঃখিত, সংযোগে সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setVoiceMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsCoachThinking(false);
    }
  };

  // Voice speech synthesis in Bengali
  const speakBengali = (text: string) => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "bn-BD";
      utterance.rate = 0.95;
      window.speechSynthesis.speak(utterance);
    }
  };

  // Web Speech API Voice Recognition
  const toggleSpeechRecognition = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice recognition is not supported in this browser. Please type your query in Bengali or English.");
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = "bn-BD";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          handleSendVoiceQuery(transcript);
        }
      };

      recognition.start();
    } catch (e) {
      setIsListening(false);
    }
  };

  // Master Freeze Trigger
  const handleExecuteFreeze = async (e: React.FormEvent) => {
    e.preventDefault();
    setFreezeError(null);
    try {
      const res = await apiRequest("/freeze/trigger", {
        method: "POST",
        body: JSON.stringify({
          freeze_pin: freezePin,
          reason: "Emergency Customer Self-Lockdown initiated from app"
        })
      });
      setFreezeResult(res);
      setCurrentUser(prev => ({ ...prev, is_frozen: true }));
      onNotify?.("Emergency Master Freeze executed in <300ms!", 'error');
      refreshCurrentUser();
      onRefreshUser?.();
    } catch (err: any) {
      setFreezeError(err.message || "Master Freeze execution failed.");
    }
  };

  // Unfreeze Trigger
  const handleExecuteUnfreeze = async (e: React.FormEvent) => {
    e.preventDefault();
    setUnfreezeError(null);
    setUnfreezeSuccess(null);
    setIsUnfreezing(true);

    try {
      const res = await apiRequest("/freeze/unfreeze", {
        method: "POST",
        body: JSON.stringify({
          verification_code: unfreezeCode.trim()
        })
      });

      setUnfreezeSuccess(res.message || "Account successfully unfrozen and operational.");
      setCurrentUser(prev => ({ ...prev, is_frozen: false }));
      onNotify?.("Account security lockdown successfully lifted!", 'success');
      refreshCurrentUser();
      onRefreshUser?.();
      setTimeout(() => {
        setIsUnfreezeModalOpen(false);
        setUnfreezeSuccess(null);
      }, 1500);
    } catch (err: any) {
      setUnfreezeError(err.message || "Unfreeze verification failed. Please verify OTP code (Default: 123456).");
    } finally {
      setIsUnfreezing(false);
    }
  };

  // Submit Citizen Scam Report
  const handleSubmitScamReport = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingScam(true);
    setScamSuccessMsg(null);

    try {
      const res = await apiRequest("/scams/report", {
        method: "POST",
        body: JSON.stringify({
          reported_account: scamReportedAccount.trim(),
          reason: scamReason,
          transaction_id: scamTxnId.trim() || undefined,
          investigation_notes: scamNotes.trim() || undefined
        })
      });

      setScamSuccessMsg(`স্ক্যাম অভিযোগ সফলভাবে জমা হয়েছে! রিপোর্ট আইডি: ${res.id}. SecurityAI ও অ্যানালিস্ট টিম তদন্ত শুরু করেছে।`);
      onNotify?.(`Scam report submitted against ${scamReportedAccount}. SecurityAI syndicate tracing activated.`, 'info');
      setTimeout(() => {
        setIsScamModalOpen(false);
        setScamSuccessMsg(null);
        setScamReportedAccount("");
        setScamNotes("");
        setScamTxnId("");
      }, 2500);
    } catch (err: any) {
      alert(err.message || "অভিযোগ জমা দিতে ব্যর্থ হয়েছে।");
    } finally {
      setIsSubmittingScam(false);
    }
  };

  // Open scam report with prefilled account/txn
  const handleOpenScamReport = (account?: string, txnId?: string) => {
    if (account) setScamReportedAccount(account);
    if (txnId) setScamTxnId(txnId);
    setIsScamModalOpen(true);
  };

  // Grace Advance Request
  const handleClaimGrace = async () => {
    setGraceStatusMsg(null);
    try {
      await apiRequest("/customer-ai/grace/request", {
        method: "POST",
        body: JSON.stringify({
          requested_amount: parseFloat(graceAmountInput)
        })
      });
      setGraceStatusMsg(`৳${graceAmountInput} উপায় গ্রেস সফলভাবে ওয়ালেটে যুক্ত হয়েছে!`);
      onNotify?.(`৳${graceAmountInput} upay Grace overdraft credited instantly!`, 'success');
      refreshCurrentUser();
      onRefreshUser?.();
      fetchCustomerAIData();
      setTimeout(() => setIsGraceModalOpen(false), 1800);
    } catch (err: any) {
      setGraceStatusMsg(err.message || "গ্রেস লোন গ্রহণ ব্যর্থ হয়েছে।");
    }
  };

  // Create Micro-FDR
  const handleCreateFDR = async () => {
    setFdrSuccessMsg(null);
    const amount = parseFloat(fdrDepositInput);
    if (isNaN(amount) || amount < 200) {
      alert("Micro-FDR এর জন্য সর্বনিম্ন ৳২০০ জমা করা আবশ্যক।");
      return;
    }

    try {
      const res = await apiRequest("/customer-ai/fdr/create", {
        method: "POST",
        body: JSON.stringify({
          principal_amount: amount,
          term_days: selectedTerm
        })
      });
      setFdrSuccessMsg(`৳${res.principal_amount} সফলভাবে ${res.term_days} দিনের Micro-FDR এ জমা হয়েছে! মেয়াদ শেষে প্রদেয়: ৳${res.total_at_maturity}`);
      onNotify?.(`Micro-FDR created: ৳${res.principal_amount} locked at 8.50%+ yield.`, 'success');
      refreshCurrentUser();
      onRefreshUser?.();
      fetchCustomerAIData();
    } catch (err: any) {
      alert(err.message || "Micro-FDR তৈরিতে ব্যর্থ হয়েছে।");
    }
  };

  // Liquidate / Withdraw Micro-FDR
  const handleLiquidateFDR = async (fdrId: string) => {
    if (!window.confirm("আপনি কি নিশ্চিতভাবে এই Micro-FDR টি ভাঙিয়ে আসল ও মুনাফা আপনার ওয়ালেটে ফেরত নিতে চান?")) {
      return;
    }

    setLiquidatingFdrId(fdrId);
    try {
      const res = await apiRequest(`/customer-ai/fdr/${fdrId}/liquidate`, {
        method: "POST"
      });

      onNotify?.(`FDR liquidated! ৳${res.refund_amount} refunded to wallet (Principal: ৳${res.principal}, Profit: ৳${res.profit})`, 'success');
      refreshCurrentUser();
      onRefreshUser?.();
      fetchCustomerAIData();
    } catch (err: any) {
      alert(err.message || "Micro-FDR ভাঙাতে সমস্যা হয়েছে।");
    } finally {
      setLiquidatingFdrId(null);
    }
  };

  // Open dynamic badge by transaction reference
  const handleViewReceiptBadge = async (ref: string) => {
    try {
      const badge = await apiRequest(`/badge/generate/${ref}`);
      if (badge) setActiveBadge(badge);
    } catch (err: any) {
      onNotify?.("Failed to generate dynamic badge: " + err.message, 'error');
    }
  };

  const walletBalance = user.profile?.wallet_balance ?? 0.0;
  const graceBalance = user.profile?.grace_balance ?? 0.0;

  // Real-time FDR profit calculation for custom deposit input
  const currentInterestRate = selectedTerm === 90 ? 9.5 : selectedTerm === 60 ? 9.0 : 8.5;
  const previewDeposit = parseFloat(fdrDepositInput) || 0;
  const previewProfit = previewDeposit > 0 ? (previewDeposit * (currentInterestRate / 100) * (selectedTerm / 365)) : 0;
  const previewTotal = previewDeposit + previewProfit;

  return (
    <div className="w-full space-y-4 sm:space-y-6">
      {/* Frozen Alert Banner */}
      {user.is_frozen && (
        <div className="bg-red-950/80 border-2 border-red-500 rounded-2xl p-4 sm:p-5 text-red-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-2xl animate-pulse">
          <div className="flex items-start sm:items-center space-x-3 sm:space-x-4">
            <div className="p-2.5 sm:p-3 bg-red-600 rounded-xl text-white shrink-0 mt-0.5 sm:mt-0">
              <ShieldAlert className="w-6 h-6 sm:w-8 sm:h-8" />
            </div>
            <div>
              <h3 className="text-base sm:text-xl font-bold text-white tracking-wide">ACCOUNT UNDER MASTER FREEZE LOCKDOWN</h3>
              <p className="text-xs sm:text-sm text-red-300">
                All outgoing transfers and cash-outs are strictly blocked by SecurityAI. Active sessions invalidated.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto shrink-0">
            <button
              onClick={() => setIsUnfreezeModalOpen(true)}
              className="flex-1 sm:flex-none px-4 sm:px-5 py-2 sm:py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-bold text-xs sm:text-sm shadow-lg transition flex items-center justify-center space-x-1.5"
            >
              <Unlock className="w-4 h-4" />
              <span>Unfreeze Account (OTP)</span>
            </button>
            <button
              onClick={() => setIsFreezeModalOpen(true)}
              className="flex-1 sm:flex-none px-3.5 sm:px-4 py-2 sm:py-2.5 bg-red-900/80 hover:bg-red-800 text-red-200 border border-red-500/40 rounded-xl font-semibold text-xs sm:text-sm transition text-center"
            >
              Lockdown Info
            </button>
          </div>
        </div>
      )}

      {/* Hero Wallet Card & Quick Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Main Wallet Card */}
        <div className="lg:col-span-2 relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gradient-to-br from-emerald-600 via-teal-700 to-slate-900 p-5 sm:p-7 text-white shadow-2xl border border-emerald-400/20">
          <div className="relative z-10 flex flex-col justify-between h-full space-y-4 sm:space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start gap-3 sm:gap-0">
              <div>
                <span className="text-[10px] sm:text-xs uppercase tracking-widest font-semibold px-2.5 sm:px-3 py-0.5 sm:py-1 rounded-full bg-white/20 backdrop-blur-md">
                  upay Pulse Smart Wallet
                </span>
                <h2 className="text-xl sm:text-2xl font-bold mt-2">{user.profile?.full_name || "Customer User"}</h2>
                <p className="text-emerald-100 text-xs sm:text-sm">{user.phone} • {user.profile?.profession || "MFS Customer"}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleOpenScamReport()}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-400/30 text-amber-200 text-xs font-semibold transition"
                >
                  <Flag className="w-3.5 h-3.5 text-amber-400" />
                  <span>Report Scam</span>
                </button>
                {user.is_frozen ? (
                  <button
                    onClick={() => setIsUnfreezeModalOpen(true)}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-400/30 text-emerald-200 text-xs font-semibold transition"
                  >
                    <Unlock className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Unfreeze</span>
                  </button>
                ) : (
                  <button
                    onClick={() => setIsFreezeModalOpen(true)}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-red-500/20 hover:bg-red-500/30 border border-red-400/30 text-red-200 text-xs font-semibold transition"
                  >
                    <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                    <span>Emergency Freeze</span>
                  </button>
                )}
              </div>
            </div>

            <div>
              <p className="text-emerald-200 text-[10px] sm:text-xs font-medium uppercase tracking-wider">Available Balance</p>
              <div className="flex items-baseline space-x-2">
                <span className="text-3xl sm:text-5xl font-extrabold tracking-tight">৳{walletBalance.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
                <span className="text-emerald-200 text-xs sm:text-sm font-semibold">BDT</span>
              </div>
            </div>

            {/* Sub-strip: Grace & Reliability */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3 pt-3 border-t border-white/10 text-xs">
              <div className="bg-black/20 p-2 sm:p-2.5 rounded-xl backdrop-blur-sm">
                <p className="text-emerald-200 text-[11px] sm:text-xs">upay Grace Balance</p>
                <p className={`font-bold text-xs sm:text-sm ${graceBalance > 0 ? "text-amber-300" : "text-white"}`}>
                  ৳{graceBalance.toFixed(2)}
                </p>
              </div>
              <div className="bg-black/20 p-2 sm:p-2.5 rounded-xl backdrop-blur-sm">
                <p className="text-emerald-200 text-[11px] sm:text-xs">Reliability Rating</p>
                <p className="font-bold text-xs sm:text-sm text-emerald-300">
                  {((user.profile?.reliability_score ?? 0.92) * 100).toFixed(0)}% (Trust)
                </p>
              </div>
              <div className="bg-black/20 p-2 sm:p-2.5 rounded-xl backdrop-blur-sm col-span-2 sm:col-span-1">
                <p className="text-emerald-200 text-[11px] sm:text-xs">Active Micro-FDRs</p>
                <p className="font-bold text-xs sm:text-sm text-cyan-300">
                  {fdrAccounts.length} Active Accounts
                </p>
              </div>
            </div>
          </div>

          {/* Background decoration */}
          <div className="absolute -right-10 -bottom-10 w-64 h-64 bg-emerald-400/10 rounded-full blur-3xl pointer-events-none" />
        </div>

        {/* Quick Actions Card */}
        <div className="rounded-2xl sm:rounded-3xl bg-slate-900 border border-slate-800 p-4 sm:p-6 flex flex-col justify-between shadow-xl space-y-4">
          <h3 className="text-slate-200 font-semibold text-sm sm:text-base flex items-center space-x-2">
            <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400" />
            <span>AI Actions & Financial Hub</span>
          </h3>

          <div className="grid grid-cols-2 gap-2 sm:gap-3">
            <button
              onClick={() => setActiveTab("coach")}
              className="p-2.5 sm:p-3.5 rounded-xl sm:rounded-2xl bg-emerald-950/40 hover:bg-emerald-900/50 border border-emerald-500/20 text-left transition group"
            >
              <div className="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-emerald-500/10 text-emerald-400 w-fit group-hover:scale-110 transition">
                <Mic className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <p className="font-bold text-white text-xs sm:text-sm mt-2">Voice Coach</p>
              <p className="text-[10px] sm:text-xs text-slate-400">Gemini 2.5 বাংলা</p>
            </button>

            <button
              onClick={() => setActiveTab("grace")}
              className="p-2.5 sm:p-3.5 rounded-xl sm:rounded-2xl bg-indigo-950/40 hover:bg-indigo-900/50 border border-indigo-500/20 text-left transition group"
            >
              <div className="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-indigo-500/10 text-indigo-400 w-fit group-hover:scale-110 transition">
                <Coins className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <p className="font-bold text-white text-xs sm:text-sm mt-2">upay Grace</p>
              <p className="text-[10px] sm:text-xs text-slate-400">৳50 Overdraft</p>
            </button>

            <button
              onClick={() => setActiveTab("cashflow")}
              className="p-2.5 sm:p-3.5 rounded-xl sm:rounded-2xl bg-teal-950/40 hover:bg-teal-900/50 border border-teal-500/20 text-left transition group"
            >
              <div className="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-teal-500/10 text-teal-400 w-fit group-hover:scale-110 transition">
                <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <p className="font-bold text-white text-xs sm:text-sm mt-2">Cash Flow</p>
              <p className="text-[10px] sm:text-xs text-slate-400">30-Day Deficit</p>
            </button>

            <button
              onClick={() => setActiveTab("fdr")}
              className="p-2.5 sm:p-3.5 rounded-xl sm:rounded-2xl bg-cyan-950/40 hover:bg-cyan-900/50 border border-cyan-500/20 text-left transition group"
            >
              <div className="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-cyan-500/10 text-cyan-400 w-fit group-hover:scale-110 transition">
                <CreditCard className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <p className="font-bold text-white text-xs sm:text-sm mt-2">Micro-FDR</p>
              <p className="text-[10px] sm:text-xs text-slate-400">8.50% Yield</p>
            </button>
          </div>

          <div className="p-2.5 sm:p-3 rounded-xl sm:rounded-2xl bg-slate-800/60 border border-slate-700/60 flex items-center justify-between text-xs text-slate-300">
            <span>Security Engine</span>
            <span className="flex items-center text-emerald-400 font-medium text-[11px] sm:text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping mr-1.5" />
              LightGBM Active
            </span>
          </div>
        </div>
      </div>

      {/* Navigation Pills */}
      <div className="flex space-x-1.5 sm:space-x-2 border-b border-slate-800 pb-2 sm:pb-3 overflow-x-auto scrollbar-none touch-pan-x -mx-1 px-1 sm:mx-0 sm:px-0">
        {[
          { id: "overview", label: "Overview & Transfers", icon: Send },
          { id: "coach", label: "Bangla Voice Coach", icon: Mic },
          { id: "cashflow", label: "30-Day Cash-Flow", icon: TrendingUp },
          { id: "grace", label: "upay Grace Overdraft", icon: Coins },
          { id: "fdr", label: "Micro-FDR High-Yield", icon: CreditCard },
          { id: "history", label: "Transaction Ledger", icon: Clock }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-1.5 sm:space-x-2 px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl font-medium text-xs sm:text-sm transition whitespace-nowrap shrink-0 ${
                isActive
                  ? "bg-emerald-500 text-white shadow-lg shadow-emerald-500/20"
                  : "bg-slate-900/70 text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW & TRANSFERS */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          {/* Transfer & Cash-out Form */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl sm:rounded-3xl p-4 sm:p-6 shadow-xl space-y-4 sm:space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 sm:pb-4">
              {/* Segmented Transfer Mode Switcher */}
              <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800">
                <button
                  type="button"
                  onClick={() => setTransferMode("send")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 ${
                    transferMode === "send"
                      ? "bg-emerald-500 text-white shadow-md shadow-emerald-500/20"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Send Money</span>
                </button>
                <button
                  type="button"
                  onClick={() => setTransferMode("cashout")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 ${
                    transferMode === "cashout"
                      ? "bg-cyan-600 text-white shadow-md shadow-cyan-600/20"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <Building2 className="w-3.5 h-3.5" />
                  <span>Cash Out at Agent</span>
                </button>
              </div>

              <span className="text-[11px] sm:text-xs text-slate-400">
                {transferMode === "send" ? "Zero Transfer Fee" : "৳15.00 Flat Agent Fee"}
              </span>
            </div>

            {/* SEND MONEY VIEW */}
            {transferMode === "send" && (
              <>
                {sendSuccessMsg && (
                  <div className="p-4 rounded-2xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 text-sm flex items-start space-x-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="font-semibold">{sendSuccessMsg}</p>
                      {activeBadge && (
                        <button
                          onClick={() => setActiveBadge(activeBadge)}
                          className="mt-2 text-xs font-bold text-emerald-300 underline hover:text-emerald-100 block"
                        >
                          View Live Anti-Screenshot Dynamic Nonce Badge →
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {sendErrorMsg && (
                  <div className="p-4 rounded-2xl bg-red-950/60 border border-red-500/40 text-red-200 text-sm flex items-center space-x-3">
                    <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
                    <span>{sendErrorMsg}</span>
                  </div>
                )}

                <form onSubmit={handleSendMoney} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1">
                      Recipient Account (Mobile / Email)
                    </label>
                    <input
                      type="text"
                      value={sendRecipient}
                      onChange={(e) => setSendRecipient(e.target.value)}
                      placeholder="+8801700000002"
                      className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-400 mb-1">Amount (BDT)</label>
                      <div className="relative">
                        <span className="absolute left-3.5 top-3.5 text-slate-400 font-bold">৳</span>
                        <input
                          type="number"
                          step="0.01"
                          min="1.0"
                          value={sendAmount}
                          onChange={(e) => setSendAmount(e.target.value)}
                          className="w-full bg-slate-800/80 border border-slate-700 rounded-xl pl-8 pr-4 py-3 text-white font-bold placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                          required
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-400 mb-1">Category</label>
                      <select
                        value={sendCategory}
                        onChange={(e) => setSendCategory(e.target.value)}
                        className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500"
                      >
                        <option value="PeerTransfer">Peer Transfer</option>
                        <option value="FamilySupport">Family Support</option>
                        <option value="UtilityBill">Utility Bill</option>
                        <option value="MerchantPayment">Merchant Pay</option>
                      </select>
                    </div>
                  </div>

                  {/* Grace Overdraft Checkbox */}
                  <div className="p-3.5 rounded-xl bg-indigo-950/30 border border-indigo-500/20 flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-indigo-200">Auto-Apply upay Grace Overdraft</p>
                      <p className="text-xs text-indigo-400/80">Cover up to ৳50 shortfall automatically if wallet balance is low</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={applyGraceIfNeeded}
                      onChange={(e) => setApplyGraceIfNeeded(e.target.checked)}
                      className="w-5 h-5 accent-emerald-500 rounded cursor-pointer"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={user.is_frozen}
                    className="w-full py-3.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold tracking-wide shadow-lg shadow-emerald-500/25 transition disabled:opacity-50"
                  >
                    Send Money (নিশ্চিত করুন)
                  </button>
                </form>
              </>
            )}

            {/* CASH OUT VIEW */}
            {transferMode === "cashout" && (
              <>
                {cashOutSuccessMsg && (
                  <div className="p-4 rounded-2xl bg-cyan-950/60 border border-cyan-500/40 text-cyan-200 text-sm flex items-start space-x-3">
                    <CheckCircle2 className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="font-semibold">{cashOutSuccessMsg}</p>
                      {activeBadge && (
                        <button
                          onClick={() => setActiveBadge(activeBadge)}
                          className="mt-2 text-xs font-bold text-cyan-300 underline hover:text-cyan-100 block"
                        >
                          Show Live Cash-Out Verification Badge to Agent →
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {cashOutErrorMsg && (
                  <div className="p-4 rounded-2xl bg-red-950/60 border border-red-500/40 text-red-200 text-sm flex items-center space-x-3">
                    <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
                    <span>{cashOutErrorMsg}</span>
                  </div>
                )}

                <form onSubmit={handleCashOut} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1">
                      Agent Identifier (Agent Code or Agent Phone Number)
                    </label>
                    <input
                      type="text"
                      value={cashOutAgent}
                      onChange={(e) => setCashOutAgent(e.target.value)}
                      placeholder="e.g. AGT-1001 or +8801800000001"
                      className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1">Withdrawal Amount (BDT)</label>
                    <div className="relative">
                      <span className="absolute left-3.5 top-3.5 text-slate-400 font-bold">৳</span>
                      <input
                        type="number"
                        step="1"
                        min="10"
                        value={cashOutAmount}
                        onChange={(e) => setCashOutAmount(e.target.value)}
                        className="w-full bg-slate-800/80 border border-slate-700 rounded-xl pl-8 pr-4 py-3 text-white font-bold placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                        required
                      />
                    </div>
                  </div>

                  {/* Fee Calculation Breakdown */}
                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5 text-xs">
                    <div className="flex justify-between text-slate-400">
                      <span>Requested Withdrawal:</span>
                      <span className="font-mono text-white">৳{(parseFloat(cashOutAmount) || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Standard Cash-Out Fee:</span>
                      <span className="font-mono text-cyan-400">৳15.00</span>
                    </div>
                    <div className="pt-1.5 border-t border-slate-800 flex justify-between font-bold text-slate-200">
                      <span>Total Deduction:</span>
                      <span className="font-mono text-emerald-400">৳{((parseFloat(cashOutAmount) || 0) + 15).toFixed(2)}</span>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={user.is_frozen || isCashOutLoading}
                    className="w-full py-3.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold tracking-wide shadow-lg shadow-cyan-600/25 transition disabled:opacity-50 flex items-center justify-center space-x-2"
                  >
                    {isCashOutLoading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Processing Cash-Out...</span>
                      </>
                    ) : (
                      <span>Confirm Cash-Out (উত্তোলন নিশ্চিত করুন)</span>
                    )}
                  </button>
                </form>
              </>
            )}
          </div>

          {/* Deficit Alert & Smart Summary */}
          <div className="space-y-6">
            {/* Deficit Alert Warning Box */}
            {trajectory?.has_deficit_alert && trajectory.deficit_alert && (
              <div className="bg-amber-950/40 border border-amber-500/40 rounded-3xl p-6 shadow-xl space-y-3">
                <div className="flex items-center space-x-3 text-amber-300">
                  <AlertTriangle className="w-6 h-6 text-amber-400" />
                  <h4 className="font-bold text-base">CustomerAI Deficit Warning (আসন্ন ঘাটতি সতর্কতা)</h4>
                </div>
                <p className="text-sm text-amber-200/90 leading-relaxed">
                  {trajectory.deficit_alert.recommended_action}
                </p>
                <div className="flex items-center justify-between pt-2 text-xs text-amber-300/80">
                  <span>Deficit Date: {trajectory.deficit_alert.deficit_date}</span>
                  <button
                    onClick={() => setIsGraceModalOpen(true)}
                    className="px-3.5 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold transition"
                  >
                    Activate Grace Advance →
                  </button>
                </div>
              </div>
            )}

            {/* Active Micro-FDRs Preview */}
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
              <div className="flex justify-between items-center">
                <h4 className="font-bold text-white flex items-center space-x-2">
                  <CreditCard className="w-5 h-5 text-cyan-400" />
                  <span>My Active Micro-FDRs</span>
                </h4>
                <button onClick={() => setActiveTab("fdr")} className="text-xs text-cyan-400 font-semibold hover:underline">
                  New Deposit +
                </button>
              </div>

              {fdrAccounts.length === 0 ? (
                <div className="text-center py-6 text-slate-400 text-sm">
                  <p>No active Micro-FDR deposits found.</p>
                  <p className="text-xs text-slate-500 mt-1">Earn 8.50% profit by depositing surplus balance.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {fdrAccounts.slice(0, 3).map((f) => (
                    <div key={f.id} className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60 flex items-center justify-between text-xs">
                      <div>
                        <p className="font-bold text-white text-sm">৳{f.principal_amount.toFixed(2)} ({f.term_days} Days)</p>
                        <p className="text-slate-400">Maturity: {f.maturity_date} • {f.interest_rate_pct}% Yield</p>
                      </div>
                      <div className="text-right flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-semibold">
                          +৳{f.projected_profit.toFixed(2)}
                        </span>
                        <button
                          onClick={() => handleLiquidateFDR(f.id)}
                          disabled={liquidatingFdrId === f.id}
                          className="px-2.5 py-1 rounded-lg bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-300 border border-cyan-500/30 text-[11px] font-semibold transition"
                        >
                          {liquidatingFdrId === f.id ? "Liquidating..." : "Withdraw"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: BANGLA VOICE COACH (GEMINI 2.5) */}
      {activeTab === "coach" && (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col h-[650px]">
          {/* Header */}
          <div className="p-5 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 font-bold shadow-lg shadow-emerald-500/20">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">upay Voice Financial Coach</h3>
                <p className="text-xs text-emerald-400 flex items-center">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block mr-1.5 animate-pulse" />
                  Live Google AI Studio Gemini 2.5 Flash
                </p>
              </div>
            </div>
            <div className="text-right text-xs text-slate-400">
              <span>Context: ৳{walletBalance.toFixed(2)} Wallet</span>
            </div>
          </div>

          {/* Quick Query Pills */}
          <div className="p-3 bg-slate-950/40 border-b border-slate-800/80 flex space-x-2 overflow-x-auto scrollbar-none">
            {[
              "আমার অ্যাকাউন্টে কত টাকা ব্যালেন্স আছে?",
              "আমার কি কোনো বিল বাকি বা ঘাটতি আছে?",
              "আমি কি জরুরি গ্রেস লোন নিতে পারব?",
              "আমার অলস টাকার জন্য কোনো ডিপিএস বা এফডিআর সুবিধা আছে কি?",
              "আমার টাকা কোথায় বেশি খরচ হয়েছে?"
            ].map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSendVoiceQuery(q)}
                className="px-3.5 py-1.5 rounded-full bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 hover:text-white transition whitespace-nowrap border border-slate-700"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Chat Messages */}
          <div className="flex-1 p-5 overflow-y-auto space-y-4">
            {voiceMessages.map((msg) => {
              const isCoach = msg.sender === "coach";
              return (
                <div key={msg.id} className={`flex ${isCoach ? "justify-start" : "justify-end"}`}>
                  <div
                    className={`max-w-[80%] rounded-2xl p-4 text-sm leading-relaxed space-y-2 ${
                      isCoach
                        ? "bg-slate-800 text-slate-100 border border-slate-700/60 shadow-lg"
                        : "bg-emerald-600 text-white shadow-lg shadow-emerald-600/20"
                    }`}
                  >
                    <p>{msg.text}</p>
                    <div className="flex items-center justify-between text-[11px] opacity-70 pt-1">
                      <span>{msg.timestamp}</span>
                      {isCoach && (
                        <div className="flex items-center space-x-2">
                          {msg.latency_ms && (
                            <span className="text-[10px] bg-emerald-950/80 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/30">
                              {msg.latency_ms.toFixed(0)} ms
                            </span>
                          )}
                          <button
                            onClick={() => speakBengali(msg.text)}
                            title="Listen in Bengali"
                            className="hover:text-emerald-300 p-0.5"
                          >
                            <Volume2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {isCoachThinking && (
              <div className="flex justify-start">
                <div className="bg-slate-800 text-slate-300 rounded-2xl p-4 text-sm border border-slate-700/60 flex items-center space-x-3">
                  <div className="flex space-x-1.5">
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce" />
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.2s]" />
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.4s]" />
                  </div>
                  <span className="text-xs text-emerald-400">Gemini 2.5 Flash আর্থিক বিশ্লেষণ করছে...</span>
                </div>
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Input Bar */}
          <div className="p-4 border-t border-slate-800 bg-slate-950/80 flex items-center space-x-3">
            <button
              onClick={toggleSpeechRecognition}
              className={`p-3 rounded-2xl transition shadow-lg ${
                isListening
                  ? "bg-red-500 text-white animate-pulse"
                  : "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30"
              }`}
              title={isListening ? "Listening... Click to stop" : "Click to speak Bengali"}
            >
              {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>

            <input
              type="text"
              value={voiceInput}
              onChange={(e) => setVoiceInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSendVoiceQuery(voiceInput)}
              placeholder="বাংলায় বা ইংরেজিতে যেকোনো প্রশ্ন লিখুন (যেমন: আমার ব্যালেন্স কত?)"
              className="flex-1 bg-slate-800/80 border border-slate-700 rounded-2xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />

            <button
              onClick={() => handleSendVoiceQuery(voiceInput)}
              disabled={!voiceInput.trim() || isCoachThinking}
              className="px-5 py-3 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm transition shadow-lg disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </div>
      )}

      {/* TAB 3: CASH-FLOW TRAJECTORY */}
      {activeTab === "cashflow" && trajectory && (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-6">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
            <div>
              <h3 className="text-xl font-bold text-white flex items-center space-x-2">
                <TrendingUp className="w-6 h-6 text-teal-400" />
                <span>30-Day Cash-Flow Trajectory (মাসিক আর্থিক গতিধারা)</span>
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Autoregressive model projecting daily balance, salary inflows, and recurrent utility bill peaks
              </p>
            </div>
            <div className="flex items-center space-x-3 text-xs">
              <span className="flex items-center text-emerald-400">
                <span className="w-3 h-3 rounded-sm bg-emerald-500/30 border border-emerald-500 inline-block mr-1.5" />
                Projected Balance
              </span>
              <span className="flex items-center text-red-400">
                <span className="w-3 h-3 rounded-sm bg-red-500/30 border border-red-500 inline-block mr-1.5" />
                Deficit Shortfall
              </span>
            </div>
          </div>

          {/* Recharts Area Chart */}
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trajectory.daily_forecast}>
                <defs>
                  <linearGradient id="balanceGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" stroke="#64748B" fontSize={11} tickFormatter={(val) => val.slice(8, 10)} />
                <YAxis stroke="#64748B" fontSize={11} tickFormatter={(val) => `৳${val}`} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0F172A", borderColor: "#334155", borderRadius: "12px" }}
                  formatter={(val: any) => [`৳${val.toLocaleString()}`, "Projected Balance"]}
                  labelFormatter={(lbl) => `Date: ${lbl}`}
                />
                <ReferenceLine y={0} stroke="#EF4444" strokeDasharray="3 3" />
                <Area type="monotone" dataKey="projected_balance" stroke="#10B981" strokeWidth={2.5} fillOpacity={1} fill="url(#balanceGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Trajectory Insights Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div className="p-3.5 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <p className="text-slate-400">Start Balance</p>
              <p className="text-base font-bold text-white mt-1">৳{trajectory.current_balance.toFixed(2)}</p>
            </div>
            <div className="p-3.5 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <p className="text-slate-400">Lowest Projected</p>
              <p className={`text-base font-bold mt-1 ${trajectory.lowest_projected_balance < 0 ? "text-red-400" : "text-white"}`}>
                ৳{trajectory.lowest_projected_balance.toFixed(2)}
              </p>
            </div>
            <div className="p-3.5 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <p className="text-slate-400">Highest Inflow Peak</p>
              <p className="text-base font-bold text-emerald-400 mt-1">৳{trajectory.highest_projected_balance.toFixed(2)}</p>
            </div>
            <div className="p-3.5 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <p className="text-slate-400">Month-End Estimate</p>
              <p className="text-base font-bold text-white mt-1">৳{trajectory.projected_30d_end_balance.toFixed(2)}</p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: UPAY GRACE OVERDRAFT */}
      {activeTab === "grace" && graceEligibility && (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-6">
          <div className="flex justify-between items-center border-b border-slate-800 pb-4">
            <div>
              <h3 className="text-xl font-bold text-white flex items-center space-x-2">
                <Coins className="w-6 h-6 text-indigo-400" />
                <span>upay Grace (জরুরি মাইক্রো-ওভারড্রাফট)</span>
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Zero-interest instant micro-overdraft (৳20 - ৳50) auto-recovered upon subsequent agent cash-in
              </p>
            </div>
            <button
              onClick={() => setIsGraceModalOpen(true)}
              disabled={!graceEligibility.eligible || graceBalance > 0}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white font-bold text-sm shadow-lg transition disabled:opacity-50"
            >
              {graceBalance > 0 ? "Grace Loan Active" : "Claim Overdraft (৳50)"}
            </button>
          </div>

          {/* Credit Score Gauge */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-slate-950/60 border border-slate-800 rounded-2xl p-5 flex flex-col items-center justify-center text-center">
              <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Alternative MFS Credit Score</p>
              <div className="text-5xl font-black text-indigo-400 my-2">
                {graceEligibility.credit_score}
              </div>
              <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 font-bold text-xs">
                {graceEligibility.credit_score >= 700 ? "EXCELLENT PROFILE" : "SATISFACTORY"}
              </span>
              <p className="text-xs text-slate-500 mt-2">Repayment Probability: {graceEligibility.repayment_likelihood_pct}%</p>
            </div>

            <div className="md:col-span-2 space-y-4">
              <h4 className="text-sm font-bold text-white">Credit Decision Explainability (স্বচ্ছতার কারণসমূহ)</h4>
              <div className="space-y-2">
                {graceEligibility.positive_factors.map((p, idx) => (
                  <div key={idx} className="flex items-center space-x-2 text-xs text-emerald-300">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    <span>{p}</span>
                  </div>
                ))}
                {graceEligibility.risk_factors.map((r, idx) => (
                  <div key={idx} className="flex items-center space-x-2 text-xs text-amber-300">
                    <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <span>{r}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: MICRO-FDR */}
      {activeTab === "fdr" && fdrRec && (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-6">
          <div className="border-b border-slate-800 pb-4">
            <h3 className="text-xl font-bold text-white flex items-center space-x-2">
              <CreditCard className="w-6 h-6 text-cyan-400" />
              <span>upay Micro-FDR (অলস টাকার উচ্চ মুনাফা সঞ্চয়)</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">{fdrRec.message}</p>
          </div>

          {/* Custom Deposit Calculation Bar */}
          <div className="p-4 sm:p-5 rounded-2xl bg-slate-950 border border-slate-800 grid grid-cols-1 sm:grid-cols-3 gap-4 items-center">
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">
                Deposit Amount (BDT, Min ৳200)
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-2.5 text-slate-400 font-bold">৳</span>
                <input
                  type="number"
                  min="200"
                  step="50"
                  value={fdrDepositInput}
                  onChange={(e) => setFdrDepositInput(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-8 pr-3 py-2 text-white font-bold text-base focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">
                Select Maturity Tenure
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[30, 60, 90].map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setSelectedTerm(t)}
                    className={`py-2 rounded-xl text-xs font-bold transition border ${
                      selectedTerm === t
                        ? "bg-cyan-600 text-white border-cyan-400 shadow-md shadow-cyan-600/20"
                        : "bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-600"
                    }`}
                  >
                    {t} Days
                  </button>
                ))}
              </div>
            </div>

            <div className="text-right flex flex-col justify-center">
              <span className="text-xs text-slate-400">Total at Maturity ({selectedTerm} Days @ {currentInterestRate}%):</span>
              <span className="text-xl font-black text-emerald-400 font-mono">
                ৳{previewTotal.toFixed(2)}
              </span>
              <span className="text-[11px] text-cyan-300">
                (Profit: +৳{previewProfit.toFixed(2)})
              </span>
            </div>
          </div>

          {/* FDR Option Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {fdrRec.options.map((opt) => (
              <div
                key={opt.term_days}
                onClick={() => setSelectedTerm(opt.term_days)}
                className={`p-5 rounded-2xl border transition cursor-pointer flex flex-col justify-between ${
                  selectedTerm === opt.term_days
                    ? "bg-cyan-950/40 border-cyan-500 shadow-xl shadow-cyan-500/10"
                    : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider">{opt.term_days} Days Tenure</span>
                    <span className="text-sm font-extrabold text-white">{opt.interest_rate_pct}% p.a.</span>
                  </div>
                  <h4 className="text-2xl font-bold text-white mt-3">৳{fdrDepositInput} Deposit</h4>
                  <p className="text-xs text-slate-400 mt-1">
                    Projected Profit: <span className="text-emerald-400 font-bold">+৳{(parseFloat(fdrDepositInput || "0") * (opt.interest_rate_pct / 100) * (opt.term_days / 365)).toFixed(2)}</span>
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleCreateFDR}
                  disabled={user.is_frozen}
                  className="mt-5 w-full py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition disabled:opacity-50"
                >
                  Lock into Micro-FDR
                </button>
              </div>
            ))}
          </div>

          {fdrSuccessMsg && (
            <div className="p-4 rounded-2xl bg-cyan-950/60 border border-cyan-500/40 text-cyan-200 text-sm flex items-center space-x-3">
              <CheckCircle2 className="w-5 h-5 text-cyan-400 flex-shrink-0" />
              <span>{fdrSuccessMsg}</span>
            </div>
          )}

          {/* Active FDR Accounts with Liquidation Option */}
          <div className="pt-4 border-t border-slate-800">
            <h4 className="text-base font-bold text-white mb-3">All Active & Matured Micro-FDR Accounts</h4>
            {fdrAccounts.length === 0 ? (
              <p className="text-xs text-slate-500">No active FDR accounts registered.</p>
            ) : (
              <div className="space-y-3">
                {fdrAccounts.map((account) => (
                  <div
                    key={account.id}
                    className="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                  >
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-white text-sm">৳{account.principal_amount.toFixed(2)}</span>
                        <span className="px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 font-mono text-[10px]">
                          {account.term_days} Days ({account.interest_rate_pct}%)
                        </span>
                        <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${
                          account.status === 'ACTIVE' ? 'bg-emerald-950 text-emerald-400' : 'bg-slate-800 text-slate-400'
                        }`}>
                          {account.status}
                        </span>
                      </div>
                      <p className="text-slate-400 mt-1">
                        Started: {account.start_date} • Maturity: <strong className="text-slate-200">{account.maturity_date}</strong>
                      </p>
                    </div>

                    <div className="flex items-center justify-between sm:justify-end gap-4">
                      <div className="text-left sm:text-right">
                        <span className="text-[10px] text-slate-500 block">Total at Maturity</span>
                        <span className="font-mono font-bold text-emerald-400 text-sm">৳{account.total_at_maturity.toFixed(2)}</span>
                      </div>

                      {account.status === 'ACTIVE' && (
                        <button
                          onClick={() => handleLiquidateFDR(account.id)}
                          disabled={liquidatingFdrId === account.id || user.is_frozen}
                          className="px-4 py-2 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 font-bold transition disabled:opacity-50"
                        >
                          {liquidatingFdrId === account.id ? "Liquidating..." : "Withdraw / Liquidate"}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 6: TRANSACTION HISTORY & LIVE RECEIPTS */}
      {activeTab === "history" && (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-6">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 border-b border-slate-800 pb-4">
            <div>
              <h3 className="text-xl font-bold text-white flex items-center space-x-2">
                <Clock className="w-6 h-6 text-emerald-400" />
                <span>Transaction Ledger & Cryptographic Receipts</span>
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Zero-trust audit ledger with live dynamic anti-screenshot badge verification.
              </p>
            </div>
            <button
              onClick={fetchTransactionHistory}
              disabled={isLoadingHistory}
              className="p-2 sm:px-3 sm:py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center space-x-1.5 transition self-start sm:self-auto"
            >
              <RefreshCw className={`w-4 h-4 ${isLoadingHistory ? 'animate-spin text-emerald-400' : ''}`} />
              <span>Refresh Ledger</span>
            </button>
          </div>

          {isLoadingHistory ? (
            <div className="py-12 text-center text-slate-400 text-xs">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-400" />
              Loading real-time ledger entries...
            </div>
          ) : transactions.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              No transactions found on this account yet.
            </div>
          ) : (
            <div className="space-y-3">
              {transactions.map((tx) => {
                const isDebit = tx.sender_id === user.id || tx.transaction_type === 'CASH_OUT';
                return (
                  <div
                    key={tx.id}
                    className="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs hover:border-slate-700 transition"
                  >
                    <div className="flex items-start space-x-3">
                      <div className={`p-2.5 rounded-xl shrink-0 ${
                        tx.transaction_type === 'CASH_OUT'
                          ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                          : tx.transaction_type === 'CASH_IN'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                      }`}>
                        {tx.transaction_type === 'CASH_OUT' ? (
                          <Building2 className="w-4 h-4" />
                        ) : tx.transaction_type === 'CASH_IN' ? (
                          <ArrowDownLeft className="w-4 h-4" />
                        ) : (
                          <ArrowUpRight className="w-4 h-4" />
                        )}
                      </div>

                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-bold text-white text-sm">
                            {tx.transaction_type.replace('_', ' ')}
                          </span>
                          <span className="font-mono text-[10px] text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                            {tx.transaction_reference}
                          </span>
                          {tx.is_flagged_fraud && (
                            <span className="text-[10px] bg-red-950 text-red-300 border border-red-500/30 px-2 py-0.5 rounded-full font-bold">
                              Flagged Fraud
                            </span>
                          )}
                        </div>

                        <p className="text-slate-400 text-[11px] mt-1">
                          {tx.created_at ? new Date(tx.created_at).toLocaleString() : 'Recent'} • 
                          {tx.receiver_phone ? ` To: ${tx.receiver_phone}` : ''}
                          {tx.agent_code ? ` Agent: ${tx.agent_code}` : ''}
                          {tx.applied_grace_amount > 0 ? ` (Grace settled: ৳${tx.applied_grace_amount})` : ''}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between sm:justify-end gap-4">
                      <div className="text-left sm:text-right">
                        <span className={`text-base font-black font-mono ${isDebit ? 'text-rose-400' : 'text-emerald-400'}`}>
                          {isDebit ? '-' : '+'}৳{tx.amount.toFixed(2)}
                        </span>
                        {tx.fee > 0 && (
                          <span className="text-[10px] text-slate-500 block">Fee: ৳{tx.fee.toFixed(2)}</span>
                        )}
                      </div>

                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleViewReceiptBadge(tx.transaction_reference)}
                          className="px-2.5 py-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] font-semibold transition flex items-center space-x-1"
                          title="Generate Anti-Screenshot Live Badge"
                        >
                          <BadgeCheck className="w-3.5 h-3.5" />
                          <span>Receipt</span>
                        </button>

                        <button
                          onClick={() => handleOpenScamReport(tx.receiver_phone || tx.agent_code || "", tx.id)}
                          className="px-2 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[11px] font-semibold transition flex items-center space-x-1"
                          title="Report suspicious transaction to SecurityAI"
                        >
                          <Flag className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* DYNAMIC BADGE MODAL (ANTI-SCREENSHOT) */}
      {activeBadge && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-sm w-full p-6 text-center space-y-5 shadow-2xl relative">
            <button
              onClick={() => setActiveBadge(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white"
            >
              ✕
            </button>

            {/* Rotating Cryptographic Badge Visual */}
            <div
              className="w-32 h-32 mx-auto rounded-full flex flex-col items-center justify-center border-4 shadow-2xl transition duration-1000 animate-pulse relative"
              style={{
                borderColor: activeBadge.pulse_color || "#10B981",
                boxShadow: `0 0 30px ${activeBadge.pulse_color || "#10B981"}40`
              }}
            >
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
              <span className="text-xl font-black text-white tracking-widest mt-1">
                {activeBadge.dynamic_nonce}
              </span>
            </div>

            {/* 60-Second Rotating Nonce Countdown */}
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-emerald-400 h-full transition-all duration-1000"
                style={{ width: `${(badgeCountdown / 60) * 100}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
              <span>Cryptographic Nonce Rotates in:</span>
              <span className="text-emerald-400 font-bold">{badgeCountdown}s</span>
            </div>

            <div>
              <h3 className="text-lg font-bold text-white">Live Cryptographic Badge</h3>
              <p className="text-xs text-emerald-400 font-semibold uppercase tracking-wider mt-1">
                Verified Authentic Payment
              </p>
              <p className="text-2xl font-black text-white mt-2">৳{activeBadge.amount.toFixed(2)}</p>
              <p className="text-xs text-slate-400">Ref: {activeBadge.transaction_reference}</p>
            </div>

            <div className="p-3 bg-slate-800/80 rounded-xl text-xs text-slate-300 space-y-1">
              <p className="text-amber-300 font-medium">⚠️ Anti-Screenshot Rotating Nonce</p>
              <p className="text-[11px] text-slate-400">
                Changes every 60s. Static screenshots or screen recordings fail merchant verification scanner.
              </p>
            </div>

            <button
              onClick={() => setActiveBadge(null)}
              className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs"
            >
              Close Badge
            </button>
          </div>
        </div>
      )}

      {/* MASTER FREEZE MODAL */}
      {isFreezeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
          <div className="bg-slate-900 border-2 border-red-500 rounded-3xl max-w-md w-full p-6 text-center space-y-5 shadow-2xl">
            <div className="w-16 h-16 rounded-full bg-red-600/20 text-red-500 flex items-center justify-center mx-auto border border-red-500/40">
              <ShieldAlert className="w-9 h-9" />
            </div>

            <div>
              <h3 className="text-xl font-bold text-white">EMERGENCY MASTER FREEZE</h3>
              <p className="text-xs text-red-300 mt-1">
                Instant lockdown in &lt;300ms SLA. Immediately terminates active JWT sessions and blocks all outgoing transfers.
              </p>
            </div>

            {freezeResult ? (
              <div className="p-4 rounded-xl bg-red-950/60 border border-red-500 text-left space-y-2 text-xs">
                <p className="font-bold text-red-200">✅ FREEZE LOCKDOWN EXECUTED</p>
                <p className="text-slate-300">Execution Response Time: <span className="font-bold text-white">{freezeResult.response_time_ms} ms</span> (&lt;300ms Target Met)</p>
                <p className="text-slate-300">Sessions Revoked: {freezeResult.sessions_revoked}</p>
                <p className="text-slate-300">Pending Transactions Cancelled: {freezeResult.pending_cancelled}</p>
                <div className="flex gap-2 pt-2">
                  <button
                    onClick={() => {
                      setIsFreezeModalOpen(false);
                      setIsUnfreezeModalOpen(true);
                      setFreezeResult(null);
                    }}
                    className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold"
                  >
                    Unfreeze Now (OTP)
                  </button>
                  <button
                    onClick={() => {
                      setIsFreezeModalOpen(false);
                      setFreezeResult(null);
                    }}
                    className="flex-1 py-2 rounded-xl bg-slate-800 text-white font-semibold"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleExecuteFreeze} className="space-y-4 text-left">
                {freezeError && (
                  <div className="p-3 bg-red-950 text-red-300 text-xs rounded-xl border border-red-700">
                    {freezeError}
                  </div>
                )}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Enter Master Freeze PIN (Default: 1234)</label>
                  <input
                    type="password"
                    maxLength={4}
                    value={freezePin}
                    onChange={(e) => setFreezePin(e.target.value)}
                    placeholder="••••"
                    className="w-full bg-slate-800 border border-red-500/50 rounded-xl px-4 py-3 text-center text-2xl font-bold tracking-widest text-white focus:outline-none"
                    required
                  />
                </div>

                <div className="flex space-x-3">
                  <button
                    type="button"
                    onClick={() => setIsFreezeModalOpen(false)}
                    className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold rounded-xl text-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-3 bg-red-600 hover:bg-red-500 text-white font-bold rounded-xl text-xs shadow-lg shadow-red-600/30 transition"
                  >
                    CONFIRM FREEZE
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* UNFREEZE MODAL */}
      {isUnfreezeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
          <div className="bg-slate-900 border-2 border-emerald-500 rounded-3xl max-w-md w-full p-6 text-center space-y-5 shadow-2xl">
            <div className="w-16 h-16 rounded-full bg-emerald-600/20 text-emerald-400 flex items-center justify-center mx-auto border border-emerald-500/40">
              <Unlock className="w-9 h-9" />
            </div>

            <div>
              <h3 className="text-xl font-bold text-white">UNFREEZE ACCOUNT SECURITY</h3>
              <p className="text-xs text-slate-300 mt-1">
                Enter your 6-digit SMS OTP verification code to securely restore all wallet operations.
              </p>
            </div>

            {unfreezeSuccess && (
              <div className="p-3 bg-emerald-950/80 text-emerald-300 text-xs rounded-xl border border-emerald-600 flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                <span>{unfreezeSuccess}</span>
              </div>
            )}

            {unfreezeError && (
              <div className="p-3 bg-red-950 text-red-300 text-xs rounded-xl border border-red-700">
                {unfreezeError}
              </div>
            )}

            <form onSubmit={handleExecuteUnfreeze} className="space-y-4 text-left">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Verification Code (Demo OTP: <strong className="text-emerald-400">123456</strong>)
                </label>
                <input
                  type="text"
                  maxLength={6}
                  value={unfreezeCode}
                  onChange={(e) => setUnfreezeCode(e.target.value)}
                  placeholder="123456"
                  className="w-full bg-slate-800 border border-emerald-500/50 rounded-xl px-4 py-3 text-center text-2xl font-mono font-bold tracking-widest text-white focus:outline-none focus:border-emerald-400"
                  required
                />
              </div>

              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={() => setIsUnfreezeModalOpen(false)}
                  className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold rounded-xl text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUnfreezing}
                  className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs shadow-lg shadow-emerald-600/30 transition disabled:opacity-50 flex items-center justify-center space-x-1.5"
                >
                  {isUnfreezing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Verifying...</span>
                    </>
                  ) : (
                    <span>CONFIRM UNFREEZE</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CITIZEN SCAM REPORT MODAL */}
      {isScamModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
          <div className="bg-slate-900 border border-amber-500 rounded-3xl max-w-lg w-full p-6 space-y-4 shadow-2xl relative">
            <button
              onClick={() => setIsScamModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white"
            >
              ✕
            </button>

            <div className="flex items-center space-x-3">
              <div className="p-3 rounded-2xl bg-amber-500/20 text-amber-400 border border-amber-500/30">
                <Flag className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Citizen Scam & Fraud Reporting</h3>
                <p className="text-xs text-slate-400">
                  Direct feed into SecurityAI Money-Mule Graph Syndicate Tracker
                </p>
              </div>
            </div>

            {scamSuccessMsg ? (
              <div className="p-4 rounded-2xl bg-emerald-950 border border-emerald-500/50 text-emerald-200 text-xs flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>{scamSuccessMsg}</span>
              </div>
            ) : (
              <form onSubmit={handleSubmitScamReport} className="space-y-3.5 text-xs text-slate-300">
                <div>
                  <label className="block font-semibold mb-1">
                    Suspected Fraudster Phone / Account / Agent Code
                  </label>
                  <input
                    type="text"
                    value={scamReportedAccount}
                    onChange={(e) => setScamReportedAccount(e.target.value)}
                    placeholder="e.g. +8801800000001 or AGT-1001"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-amber-500"
                    required
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold mb-1">Fraud Category</label>
                    <select
                      value={scamReason}
                      onChange={(e) => setScamReason(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-white focus:outline-none focus:border-amber-500"
                    >
                      <option value="Lottery / Prize Fake Agent">Lottery / Prize Fake Agent</option>
                      <option value="Customer Support Impersonation (OTP Theft)">Customer Support Impersonation (OTP Theft)</option>
                      <option value="Fake Facebook / Online Seller">Fake Facebook / Online Seller</option>
                      <option value="Extortion / Blackmail">Extortion / Blackmail</option>
                      <option value="Unauthorized Transaction">Unauthorized Transaction</option>
                    </select>
                  </div>

                  <div>
                    <label className="block font-semibold mb-1">Linked Transaction ID (Optional)</label>
                    <input
                      type="text"
                      value={scamTxnId}
                      onChange={(e) => setScamTxnId(e.target.value)}
                      placeholder="e.g. TXN-12345"
                      className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-semibold mb-1">Incident Evidence & Commentary</label>
                  <textarea
                    rows={3}
                    value={scamNotes}
                    onChange={(e) => setScamNotes(e.target.value)}
                    placeholder="Describe how the fraudster contacted you, what instructions were given, etc."
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-amber-500 resize-none"
                  />
                </div>

                <div className="p-3 bg-amber-950/30 rounded-xl border border-amber-500/20 text-[11px] text-amber-200">
                  🔒 Security Notice: Submitting this report automatically tags the target node in the NetworkX graph and alerts the Risk Operations Console for immediate freeze consideration.
                </div>

                <div className="flex space-x-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsScamModalOpen(false)}
                    className="flex-1 py-2.5 bg-slate-800 text-slate-300 font-semibold rounded-xl text-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingScam}
                    className="flex-1 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl text-xs shadow-lg transition disabled:opacity-50"
                  >
                    {isSubmittingScam ? "Submitting Report..." : "Submit Scam Report"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* GRACE CLAIM MODAL */}
      {isGraceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-indigo-500 rounded-3xl max-w-sm w-full p-6 text-center space-y-4 shadow-2xl">
            <Coins className="w-12 h-12 text-indigo-400 mx-auto" />
            <h3 className="text-lg font-bold text-white">Claim upay Grace Overdraft</h3>
            <p className="text-xs text-slate-300">Instant credit to wallet. Settled automatically on next cash-in.</p>

            {graceStatusMsg && (
              <p className="text-xs font-semibold text-indigo-300 bg-indigo-950/60 p-2.5 rounded-xl border border-indigo-500/30">
                {graceStatusMsg}
              </p>
            )}

            <div className="text-left">
              <label className="text-xs text-slate-400 font-medium">Overdraft Amount (Max: ৳50.00)</label>
              <input
                type="number"
                value={graceAmountInput}
                onChange={(e) => setGraceAmountInput(e.target.value)}
                min="10"
                max="50"
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white font-bold mt-1 text-center text-xl"
              />
            </div>

            <div className="flex space-x-3 pt-2">
              <button
                onClick={() => setIsGraceModalOpen(false)}
                className="flex-1 py-2.5 bg-slate-800 text-slate-300 font-semibold rounded-xl text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleClaimGrace}
                className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs shadow-lg transition"
              >
                Disburse ৳{graceAmountInput}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
