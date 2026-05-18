"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Loader2, Key, Settings, History, CheckCircle, FileText, Download, User, Sparkles, Send, Eye, EyeOff, LogOut, LogIn, AlertTriangle, BookOpen, HelpCircle, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

export default function Home() {
  const [topic, setTopic] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("");
  const [result, setResult] = useState<any>(null);
  const [errorText, setErrorText] = useState("");
  const [showDocs, setShowDocs] = useState(false);

  // Settings state
  const [userEmail, setUserEmail] = useState("");
  const [tempEmail, setTempEmail] = useState("");
  const [isClient, setIsClient] = useState(false);
  const [tavilyKey, setTavilyKey] = useState("");
  const [llmProvider, setLlmProvider] = useState("Gemini");
  const [llmKey, setLlmKey] = useState("");
  const [modelName, setModelName] = useState("gemini-2.5-flash");

  const [history, setHistory] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState("new");

  const [showTavilyKey, setShowTavilyKey] = useState(false);
  const [showLlmKey, setShowLlmKey] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://deepak2075-research-agent-api.hf.space";

  useEffect(() => {
    setIsClient(true);
    const savedEmail = localStorage.getItem("user_email");
    if (savedEmail) {
      setUserEmail(savedEmail);
      setTempEmail(savedEmail);
    }

    const savedTavily = sessionStorage.getItem("tavilyKey");
    if (savedTavily) setTavilyKey(savedTavily);

    const savedProvider = sessionStorage.getItem("llmProvider");
    if (savedProvider) setLlmProvider(savedProvider);

    const savedLlmKey = sessionStorage.getItem("llmKey");
    if (savedLlmKey) setLlmKey(savedLlmKey);

    const savedModel = sessionStorage.getItem("modelName");
    if (savedModel) setModelName(savedModel);
  }, []);

  useEffect(() => {
    if (userEmail) {
      fetchHistory(userEmail);
    } else {
      setHistory([]);
    }
  }, [userEmail]);

  const fetchHistory = async (email: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/history?user_email=${email}`);
      const data = await res.json();
      if (data.blogs) {
        setHistory(data.blogs);
      }
    } catch (e) {
      console.error("Failed to fetch history", e);
    }
  };

  const handleSaveSettings = () => {
    try {
      sessionStorage.setItem("tavilyKey", tavilyKey);
      sessionStorage.setItem("llmProvider", llmProvider);
      sessionStorage.setItem("llmKey", llmKey);
      sessionStorage.setItem("modelName", modelName);
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 2000);
    } catch (e) {
      console.error("Session storage error", e);
      alert("Session storage is full or restricted. Please clear your browser data.");
    }
  };

  const startResearch = async () => {
    if (!topic || !tavilyKey || !llmKey) {
      alert("Please enter a topic and provide both API keys.");
      return;
    }

    setIsGenerating(true);
    setProgress(10);
    setStatusText("Initializing Agents...");
    setResult(null);
    setErrorText("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_email: userEmail,
          topic,
          tavily_api_key: tavilyKey,
          llm_provider: llmProvider,
          llm_api_key: llmKey,
          model_name: modelName,
        }),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.substring(6));
              if (data.error) {
                setStatusText(`Error: ${data.error}`);
                setErrorText(data.error);
                setIsGenerating(false);
                return;
              }

              if (data.status) setStatusText(data.status);
              if (data.progress) setProgress(data.progress);

              if (data.done) {
                setResult(data);
                setIsGenerating(false);
                fetchHistory(userEmail);
                break;
              }
            } catch (e) {
              console.error("Error parsing SSE data", e, line);
            }
          }
        }
      }
      setIsGenerating(false);
      setProgress(100);
    } catch (e: any) {
      setStatusText("An error occurred during generation.");
      setErrorText(e.message || "An error occurred during generation.");
      setIsGenerating(false);
      console.error(e);
    }
  };

  const downloadFile = async (format: string) => {
    if (!result) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: result.blog_post,
          format: format,
          topic: topic || "research_blog"
        })
      });

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(topic || "blog").toLowerCase().replace(/ /g, "_")}.${format === "word" ? "docx" : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (e) {
      console.error("Download failed", e);
    }
  };

  return (
    <div className="min-h-screen flex w-full bg-[#0a0a0a] text-slate-100 selection:bg-indigo-500/30 font-sans">

      {/* SIDEBAR */}
      <aside className="w-80 border-r border-white/10 bg-[#121212] hidden md:flex flex-col h-screen sticky top-0 z-20">
        <div className="p-6 border-b border-white/10">
          <h2 className="text-xl font-bold flex items-center gap-2 text-indigo-400 tracking-tight">
            <Settings size={20} className="text-indigo-400" /> Configuration
          </h2>
          <p className="text-xs text-slate-500 mt-2">Manage API keys & settings</p>
        </div>

        <ScrollArea className="flex-1">
          <div className="space-y-6 py-6 px-6">
            <div className="space-y-3 bg-white/5 border border-white/10 rounded-xl p-4 shadow-inner">
              <Label className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider"><User size={14} /> Account</Label>
              {!isClient ? (
                <div className="flex items-center justify-center h-10"><Loader2 className="animate-spin text-slate-500" size={20} /></div>
              ) : userEmail ? (
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center font-bold text-white text-xs shrink-0">
                      {userEmail.charAt(0).toUpperCase() || "U"}
                    </div>
                    <div className="truncate">
                      <p className="text-sm font-bold text-white truncate">{userEmail.split("@")[0]}</p>
                      <p className="text-xs text-slate-400 truncate">{userEmail}</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => {
                    localStorage.removeItem("user_email");
                    setUserEmail("");
                    setTempEmail("");
                  }} className="text-slate-400 hover:text-red-400 hover:bg-red-500/10 shrink-0" title="Sign out">
                    <LogOut size={16} />
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Input
                    type="email"
                    placeholder="Enter email / username"
                    value={tempEmail}
                    onChange={(e) => setTempEmail(e.target.value)}
                    className="bg-white/5 border-white/10 text-white placeholder:text-slate-500 focus-visible:ring-indigo-500 h-9"
                  />
                  <Button onClick={() => {
                    if (tempEmail.trim()) {
                      localStorage.setItem("user_email", tempEmail.trim());
                      setUserEmail(tempEmail.trim());
                    } else {
                      alert("Please enter an email or username");
                    }
                  }} className="w-full bg-white text-black hover:bg-slate-200 font-bold flex items-center justify-center gap-2 h-9">
                    <LogIn size={16} /> Log In
                  </Button>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider"><Key size={14} /> Tavily API Key</Label>
              <div className="relative">
                <Input
                  type={showTavilyKey ? "text" : "password"}
                  value={tavilyKey}
                  onChange={(e) => setTavilyKey(e.target.value)}
                  placeholder="tvly-..."
                  className="bg-white/5 border-white/10 text-white placeholder:text-slate-600 focus-visible:ring-indigo-500 focus-visible:border-indigo-500 h-10 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowTavilyKey(!showTavilyKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
                >
                  {showTavilyKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider"><Settings size={14} /> LLM Provider</Label>
              <Select
                value={llmProvider}
                onValueChange={(val) => {
                  setLlmProvider(val || "Gemini");
                  if (val === "Anthropic") setModelName("claude-3-5-sonnet-20241022");
                  else if (val === "Gemini") setModelName("gemini-2.5-flash");
                  else if (val === "OpenAI") setModelName("gpt-4o-mini");
                }}
              >
                <SelectTrigger className="bg-white/5 border-white/10 text-white focus:ring-indigo-500 focus:border-indigo-500 h-10">
                  <SelectValue placeholder="Select a provider" />
                </SelectTrigger>
                <SelectContent className="bg-[#1a1a1a] border-white/10 text-white">
                  <SelectItem value="Anthropic" className="focus:bg-indigo-500/20 focus:text-white">Anthropic</SelectItem>
                  <SelectItem value="Gemini" className="focus:bg-indigo-500/20 focus:text-white">Gemini</SelectItem>
                  <SelectItem value="OpenAI" className="focus:bg-indigo-500/20 focus:text-white">OpenAI</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider"><Key size={14} /> {llmProvider} API Key</Label>
              <div className="relative">
                <Input
                  type={showLlmKey ? "text" : "password"}
                  value={llmKey}
                  onChange={(e) => setLlmKey(e.target.value)}
                  className="bg-white/5 border-white/10 text-white placeholder:text-slate-600 focus-visible:ring-indigo-500 focus-visible:border-indigo-500 h-10 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowLlmKey(!showLlmKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
                >
                  {showLlmKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider"><Settings size={14} /> Model Name</Label>
              <Input
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                className="bg-white/5 border-white/10 text-white placeholder:text-slate-600 focus-visible:ring-indigo-500 focus-visible:border-indigo-500 h-10"
              />
            </div>

            <Button
              onClick={handleSaveSettings}
              className={`w-full font-bold h-10 transition-all ${isSaved ? 'bg-emerald-500 hover:bg-emerald-600 text-white shadow-[0_0_15px_rgba(16,185,129,0.4)]' : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-[0_0_15px_rgba(79,70,229,0.2)]'}`}
            >
              {isSaved ? <span className="flex items-center gap-2"><CheckCircle size={16} /> Saved!</span> : "Save Settings"}
            </Button>
          </div>
        </ScrollArea>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 flex flex-col h-screen overflow-y-auto overflow-x-hidden relative z-10">

        {/* Documentation Link in Top Right Corner */}
        <div className="absolute top-6 right-6 md:top-8 md:right-8 z-50">
          <Button
            onClick={() => setShowDocs(true)}
            variant="outline"
            className="flex items-center gap-2 border-white/10 bg-[#18181b]/60 backdrop-blur-md text-slate-300 hover:text-white hover:bg-white/10 hover:border-indigo-500/40 rounded-full px-5 py-2 font-bold text-sm transition-all duration-300 shadow-lg hover:shadow-indigo-500/10"
          >
            <BookOpen size={16} className="text-indigo-400" />
            <span>How it Works</span>
          </Button>
        </div>

        {/* Background Gradients */}
        <div className="absolute inset-0 z-0 pointer-events-none opacity-40">
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-600/30 blur-[120px]" />
          <div className="absolute top-[20%] right-[-10%] w-[30%] h-[30%] rounded-full bg-purple-600/20 blur-[100px]" />
        </div>

        <div className="max-w-6xl mx-auto w-full p-6 md:p-10 lg:p-14 flex flex-col gap-10 relative z-10">

          <motion.header
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="flex flex-col items-center text-center mt-10 mb-6"
          >
            <div className="inline-flex items-center justify-center p-3 bg-white/5 rounded-2xl border border-white/10 mb-6 shadow-2xl shadow-indigo-500/10">
              <Sparkles className="text-indigo-400" size={32} />
            </div>
            <h1 className="text-4xl md:text-5xl font-black tracking-tight text-white mb-4">
              Agentic <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">Researcher</span>
            </h1>
            <p className="text-slate-400 text-lg md:text-xl max-w-2xl font-medium">
              Provide a topic and let our autonomous AI agents search the web, read detailed content, and draft a high-quality blog post for you.
            </p>
          </motion.header>

          {/* Centralized Tabs */}
          <div className="flex justify-center mb-8">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-[380px]">
              <TabsList className="grid w-full grid-cols-2 bg-black/40 backdrop-blur-md border border-white/10 p-2 rounded-full shadow-xl !h-auto">
                <TabsTrigger
                  value="new"
                  className={`h-10 w-full rounded-full font-bold text-base transition-all duration-300 ${activeTab === "new" ? "!bg-indigo-600 !text-white !shadow-[0_0_15px_rgba(79,70,229,0.5)]" : "text-slate-400 hover:text-slate-200"}`}
                >
                  <Search size={18} className="mr-2" /> New Research
                </TabsTrigger>
                <TabsTrigger
                  value="history"
                  onClick={() => fetchHistory(userEmail)}
                  className={`h-10 w-full rounded-full font-bold text-base transition-all duration-300 ${activeTab === "history" ? "!bg-indigo-600 !text-white !shadow-[0_0_15px_rgba(79,70,229,0.5)]" : "text-slate-400 hover:text-slate-200"}`}
                >
                  <History size={18} className="mr-2" /> History
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {activeTab === "new" ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col gap-10"
            >
              {/* Massive Search Bar */}
              <div className="relative group mx-auto w-full max-w-3xl">
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-[32px] blur opacity-25 group-hover:opacity-50 transition duration-500"></div>
                <div className="relative flex items-center bg-[#18181b] border border-white/10 rounded-[30px] p-2 shadow-2xl">
                  <div className="pl-6 pr-2">
                    <Search className="text-slate-400" size={24} />
                  </div>
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="Enter any topic (e.g., 'Future of AI agents')..."
                    disabled={isGenerating}
                    onKeyDown={(e) => e.key === "Enter" && startResearch()}
                    className="w-full bg-transparent border-none text-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-0 h-16"
                  />
                  <button
                    onClick={startResearch}
                    disabled={isGenerating || !topic || !userEmail}
                    className="flex items-center justify-center bg-indigo-600 hover:bg-indigo-500 text-white h-14 px-8 rounded-full font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(79,70,229,0.4)] mr-1"
                  >
                    {isGenerating ? <Loader2 className="animate-spin mr-2" size={20} /> : <Send size={18} className="mr-2" />}
                    Research
                  </button>
                </div>
              </div>

              {/* Error Message Alert Card */}
              <AnimatePresence>
                {errorText && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="max-w-3xl mx-auto w-full"
                  >
                    <div className="bg-red-500/10 border border-red-500/20 rounded-3xl p-6 shadow-2xl flex items-start gap-4 backdrop-blur-md relative overflow-hidden">
                      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-500 to-rose-600" />
                      <AlertTriangle className="text-red-400 shrink-0 mt-0.5" size={24} />
                      <div>
                        <h4 className="text-lg font-bold text-white mb-1">Research Generation Failed</h4>
                        <p className="text-slate-300 text-sm leading-relaxed mb-3">
                          The multi-agent system encountered an issue while generating your blog post:
                        </p>
                        <div className="bg-black/30 border border-white/5 rounded-xl p-4 font-mono text-red-300 text-xs break-words leading-relaxed select-all">
                          {errorText}
                        </div>
                        {errorText.includes("RESOURCE_EXHAUSTED") && (
                          <p className="mt-4 text-xs text-slate-400 bg-white/5 border border-white/10 p-3 rounded-lg leading-relaxed">
                            💡 <strong>Tip:</strong> Your Gemini API Key has exceeded its daily free tier quota (rate limit). Please wait for Google to reset the daily limit, link a billing account in Google AI Studio for unlimited requests, or try a different key/provider!
                          </p>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Progress */}
              <AnimatePresence>
                {isGenerating && (
                  <motion.div
                    initial={{ opacity: 0, height: 0, y: -20 }}
                    animate={{ opacity: 1, height: "auto", y: 0 }}
                    exit={{ opacity: 0, height: 0, scale: 0.95 }}
                    className="max-w-3xl mx-auto w-full"
                  >
                    <div className="bg-[#18181b] border border-white/10 rounded-3xl p-8 shadow-xl relative overflow-hidden">
                      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 to-purple-500 animate-pulse" />

                      <div className="flex flex-col gap-6">
                        <div className="flex justify-between items-end">
                          <div>
                            <h3 className="text-xl font-bold text-white flex items-center gap-3">
                              <Loader2 className="animate-spin text-indigo-400" size={24} />
                              Agents Computing...
                            </h3>
                            <div className="mt-3 text-sm font-mono text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-4 py-2 rounded-lg inline-block shadow-inner">
                              {statusText}
                            </div>
                          </div>
                          <span className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-br from-white to-slate-500">
                            {progress}%
                          </span>
                        </div>

                        <div className="w-full bg-black/40 rounded-full h-3 border border-white/5 overflow-hidden">
                          <motion.div
                            className="bg-gradient-to-r from-indigo-500 to-purple-500 h-full rounded-full relative"
                            initial={{ width: 0 }}
                            animate={{ width: `${progress}%` }}
                            transition={{ type: "spring", stiffness: 50 }}
                          >
                            <div className="absolute inset-0 bg-white/20 w-full animate-[shimmer_2s_infinite]" />
                          </motion.div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Results */}
              <AnimatePresence>
                {result && !isGenerating && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="w-full"
                  >
                    <div className="bg-[#121212] border border-white/10 rounded-3xl relative overflow-hidden shadow-2xl">
                      <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-emerald-400 to-teal-500" />

                      <div className="p-8 md:p-12">
                        <div className="flex flex-col sm:flex-row justify-between items-start gap-6 mb-10 border-b border-white/10 pb-8">
                          <div>
                            <div className="inline-flex items-center gap-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-4 text-sm font-semibold py-1.5 px-4 rounded-full">
                              <CheckCircle size={16} /> Quality Score: {result.score}/10
                            </div>
                            <h2 className="text-3xl md:text-5xl font-black text-white leading-tight">{topic}</h2>
                          </div>

                          <div className="flex gap-2 bg-white/5 p-1.5 rounded-2xl border border-white/10">
                            {["md", "html", "pdf", "word"].map((format) => (
                              <button
                                key={format}
                                onClick={() => downloadFile(format)}
                                className="p-3 text-slate-400 hover:text-white hover:bg-white/10 transition-all rounded-xl tooltip flex items-center justify-center"
                                title={`Download ${format.toUpperCase()}`}
                              >
                                <Download size={20} />
                              </button>
                            ))}
                          </div>
                        </div>

                        <div className="prose prose-lg prose-invert max-w-none prose-headings:text-white prose-a:text-indigo-400 hover:prose-a:text-indigo-300 prose-img:rounded-2xl prose-img:shadow-xl">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {result.blog_post}
                          </ReactMarkdown>
                        </div>


                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col gap-4 max-w-4xl mx-auto w-full"
            >
              {history.length === 0 ? (
                <div className="bg-[#121212] border border-white/10 border-dashed rounded-3xl flex flex-col items-center justify-center py-32 text-slate-500">
                  <History size={64} className="mb-6 opacity-20" />
                  <h3 className="text-2xl font-bold mb-2 text-white">No Research History</h3>
                  <p className="text-lg">Start a new research task to see your generated blogs here.</p>
                </div>
              ) : (
                <div className="grid gap-6">
                  {history.map((item: any, i: number) => (
                    <div
                      key={i}
                      className="bg-[#18181b] border border-white/10 rounded-2xl p-6 transition-all hover:bg-[#202024] hover:border-indigo-500/40 cursor-pointer shadow-lg group"
                      onClick={() => {
                        setResult({
                          blog_post: item.blog_post,
                          critique_report: item.critique_report,
                          score: item.score
                        });
                        setTopic(item.topic);
                        setActiveTab("new");
                      }}
                    >
                      <div className="flex justify-between items-start gap-6 mb-4">
                        <h3 className="text-2xl font-bold text-white group-hover:text-indigo-400 transition-colors">{item.topic}</h3>
                        <div className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 whitespace-nowrap font-bold px-3 py-1 rounded-full text-sm">
                          Score: {item.score}/10
                        </div>
                      </div>
                      <p className="text-slate-400 text-base line-clamp-2 leading-relaxed">
                        {item.blog_post
                          .replace(/!\[.*?\]\(.*?\)/g, "") // Remove markdown image links
                          .replace(/[#*`_]/g, "")           // Remove markdown headers/formatting
                          .replace(/\s+/g, " ")             // Normalize spaces and newlines
                          .trim()
                          .substring(0, 200)}...
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </div>
      </main>

      {/* Documentation Modal */}
      <AnimatePresence>
        {showDocs && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
            {/* Modal Container */}
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              transition={{ type: "spring", duration: 0.5 }}
              className="bg-[#0f0f13] border border-white/10 rounded-3xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden relative"
            >
              {/* Top border accent line */}
              <div className="h-1.5 w-full bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500" />

              {/* Close Button */}
              <button
                onClick={() => setShowDocs(false)}
                className="absolute top-6 right-6 p-2 rounded-full border border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20 text-slate-400 hover:text-white transition-all duration-300 z-10"
              >
                <X size={18} />
              </button>

              {/* Modal Header */}
              <div className="p-8 pb-4 border-b border-white/5">
                <div className="flex items-center gap-3 mb-2">
                  <Sparkles className="text-indigo-400 animate-pulse" size={24} />
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full">System Architecture</span>
                </div>
                <h2 className="text-2xl md:text-3xl font-black text-white">How the Multi-Agent Researcher Works</h2>
                <p className="text-slate-400 text-sm mt-1">Our autonomous AI system operates via 4 specialized agents collaborating in a sequential pipelined execution.</p>
              </div>

              {/* Modal Scrollable Body */}
              <ScrollArea className="flex-1 p-8 overflow-y-auto">
                <div className="flex flex-col gap-8 pb-4">
                  
                  {/* Step-by-Step Workflow Pipeline Map */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-black/30 border border-white/5 p-6 rounded-2xl">
                    <div className="flex flex-col items-center text-center p-3">
                      <div className="w-10 h-10 rounded-full bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center font-bold text-indigo-300 mb-3">1</div>
                      <h4 className="text-sm font-bold text-white mb-1">Search Agent</h4>
                      <p className="text-xs text-slate-400">Scours Tavily for top 5 web sources</p>
                    </div>
                    <div className="flex flex-col items-center text-center p-3 relative">
                      <div className="hidden md:block absolute top-[28px] left-[-30px] w-[50px] h-[1px] bg-white/15" />
                      <div className="w-10 h-10 rounded-full bg-purple-500/20 border border-purple-500/40 flex items-center justify-center font-bold text-purple-300 mb-3">2</div>
                      <h4 className="text-sm font-bold text-white mb-1">Extraction Agent</h4>
                      <p className="text-xs text-slate-400">Extracts raw text content via scraping</p>
                    </div>
                    <div className="flex flex-col items-center text-center p-3 relative">
                      <div className="hidden md:block absolute top-[28px] left-[-30px] w-[50px] h-[1px] bg-white/15" />
                      <div className="w-10 h-10 rounded-full bg-pink-500/20 border border-pink-500/40 flex items-center justify-center font-bold text-pink-300 mb-3">3</div>
                      <h4 className="text-sm font-bold text-white mb-1">Writer Agent</h4>
                      <p className="text-xs text-slate-400">Drafts complete structured article</p>
                    </div>
                    <div className="flex flex-col items-center text-center p-3 relative">
                      <div className="hidden md:block absolute top-[28px] left-[-30px] w-[50px] h-[1px] bg-white/15" />
                      <div className="w-10 h-10 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center font-bold text-emerald-300 mb-3">4</div>
                      <h4 className="text-sm font-bold text-white mb-1">Critic Agent</h4>
                      <p className="text-xs text-slate-400">Grades structure and refines output</p>
                    </div>
                  </div>

                  {/* Detailed Agent Breakdown */}
                  <div className="flex flex-col gap-4">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <CheckCircle size={18} className="text-indigo-400" />
                      Detailed Agent Directory
                    </h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Search Agent card */}
                      <div className="bg-white/5 border border-white/5 p-5 rounded-2xl">
                        <div className="flex justify-between items-start mb-3">
                          <h4 className="font-bold text-white text-base">🔍 Agent 1: Search Agent</h4>
                          <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded-full">Tavily Engine</span>
                        </div>
                        <p className="text-slate-300 text-xs leading-relaxed">
                          Takes your research query and uses the high-precision Tavily API to execute multi-dimensional search queries, extracting the top 5 web sources, article headers, and high-relevancy snippets.
                        </p>
                      </div>

                      {/* Content Scraper card */}
                      <div className="bg-white/5 border border-white/5 p-5 rounded-2xl">
                        <div className="flex justify-between items-start mb-3">
                          <h4 className="font-bold text-white text-base">📄 Agent 2: Content Extractor</h4>
                          <span className="text-[10px] uppercase font-bold tracking-wider text-purple-300 bg-purple-500/10 px-2 py-0.5 rounded-full">Scraper Engine</span>
                        </div>
                        <p className="text-slate-300 text-xs leading-relaxed">
                          Crawls the retrieved search result URLs using BeautifulSoup. It sanitizes the raw HTML payload, strips away tracking codes or redundant text, and compiles clean content feeds for the writers.
                        </p>
                      </div>

                      {/* Writer Agent card */}
                      <div className="bg-white/5 border border-white/5 p-5 rounded-2xl">
                        <div className="flex justify-between items-start mb-3">
                          <h4 className="font-bold text-white text-base">✍️ Agent 3: Content Writer</h4>
                          <span className="text-[10px] uppercase font-bold tracking-wider text-pink-300 bg-pink-500/10 px-2 py-0.5 rounded-full">LLM Engine</span>
                        </div>
                        <p className="text-slate-300 text-xs leading-relaxed">
                          Processes the accumulated context and details. Using your designated LLM model, it authors a highly readable, comprehensive blog post complete with title, rich headings, and formatting.
                        </p>
                      </div>

                      {/* Critic Agent card */}
                      <div className="bg-white/5 border border-white/5 p-5 rounded-2xl">
                        <div className="flex justify-between items-start mb-3">
                          <h4 className="font-bold text-white text-base">🛡️ Agent 4: Editor & Critic</h4>
                          <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-300 bg-emerald-500/10 px-2 py-0.5 rounded-full">Evaluation Engine</span>
                        </div>
                        <p className="text-slate-300 text-xs leading-relaxed">
                          Conducts a formal editorial review. Evaluates information depth, structure, and formatting, assigns a score out of 10, and runs a revision pass to refine the article to perfection.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* How to Get Started Configuration */}
                  <div className="bg-indigo-500/5 border border-indigo-500/15 p-6 rounded-2xl">
                    <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
                      <Key size={16} className="text-indigo-400" />
                      Configuration Guide (How to Start)
                    </h3>
                    <ul className="text-xs text-slate-300 space-y-2 list-disc list-inside">
                      <li>Enter a persistent **email address** to sign in and automatically synchronize your blog history.</li>
                      <li>Acquire a Tavily key from <a href="https://tavily.com" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">tavily.com</a> and paste it into the **Tavily API Key** field.</li>
                      <li>Select your LLM provider (e.g. Gemini) and obtain a key from <a href="https://aistudio.google.com" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">Google AI Studio</a>.</li>
                      <li>Paste the keys, click **Save Settings**, enter a research topic, and witness the multi-agent system execute!</li>
                    </ul>
                  </div>

                </div>
              </ScrollArea>

              {/* Modal Footer */}
              <div className="p-6 border-t border-white/5 bg-black/20 flex justify-end">
                <Button
                  onClick={() => setShowDocs(false)}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-6 h-10 rounded-full transition-all shadow-[0_0_15px_rgba(79,70,229,0.3)]"
                >
                  Got it, close Docs
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
