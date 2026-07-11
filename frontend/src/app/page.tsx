"use client";

import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { ChevronDown, ChevronUp, Bot, User, Database, Search } from "lucide-react";

type ToolMetadata = {
  tool: string;
  data: string | any;
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolMetadata?: ToolMetadata[];
};

function Accordion({ title, content, toolType }: { title: string; content: string; toolType: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const Icon = toolType === "search_policies" ? Search : Database;

  return (
    <div className="mt-3 border border-slate-200 rounded-lg overflow-hidden bg-white shadow-sm">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors"
      >
        <div className="flex items-center space-x-2 text-sm font-semibold text-slate-700">
          <Icon className="w-4 h-4 text-indigo-500" />
          <span>{title}</span>
        </div>
        {isOpen ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
      </button>
      {isOpen && (
        <div className="px-4 py-3 bg-white border-t border-slate-200 text-sm overflow-x-auto">
          {toolType === "query_orders" ? (
            <pre className="text-xs text-slate-800 bg-slate-100 p-3 rounded-md"><code>{content}</code></pre>
          ) : (
            <div className="whitespace-pre-wrap text-slate-700 text-xs leading-relaxed">{content}</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsgId = crypto.randomUUID();
    const assistantMsgId = crypto.randomUUID();

    const newMessages: Message[] = [
      ...messages,
      { id: userMsgId, role: "user", content: input.trim() },
      { id: assistantMsgId, role: "assistant", content: "", toolMetadata: [] }
    ];

    setMessages(newMessages);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input.trim() }),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6).trim();
            if (!dataStr) continue;

            try {
              const parsed = JSON.parse(dataStr);
              
              setMessages((prev) => 
                prev.map((msg) => {
                  if (msg.id !== assistantMsgId) return msg;

                  if (parsed.type === "token") {
                    return { ...msg, content: msg.content + parsed.content };
                  } else if (parsed.type === "tool_metadata") {
                    const existingMeta = msg.toolMetadata || [];
                    return { 
                      ...msg, 
                      toolMetadata: [...existingMeta, { tool: parsed.tool, data: parsed.data }] 
                    };
                  } else if (parsed.type === "error") {
                    return { ...msg, content: msg.content + "\n\n**Error:** " + parsed.content };
                  }
                  return msg;
                })
              );
            } catch (err) {
              console.error("Failed to parse SSE data:", err);
            }
          }
        }
      }
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === assistantMsgId 
            ? { ...msg, content: msg.content + "\n\n**Connection Error:** Unable to reach the server." }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-50 text-slate-900 font-sans">
      <header className="bg-white border-b border-slate-200 px-8 py-5 flex items-center shadow-sm z-10">
        <Bot className="w-7 h-7 text-indigo-600 mr-3" />
        <h1 className="text-xl font-bold tracking-tight text-slate-800">Corporate Intelligence System</h1>
      </header>

      <main className="flex-1 overflow-y-auto p-6 md:p-10 w-full max-w-5xl mx-auto space-y-8">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 space-y-4">
            <Bot className="w-16 h-16 text-slate-300" />
            <p className="text-lg font-medium">How can I assist you today?</p>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`flex max-w-[85%] ${m.role === "user" ? "flex-row-reverse" : "flex-row"} items-start gap-4`}>
              <div className={`p-2.5 rounded-full flex-shrink-0 ${
                m.role === "user" 
                  ? "bg-indigo-600 text-white shadow-md" 
                  : "bg-white border border-slate-200 text-indigo-600 shadow-sm"
              }`}>
                {m.role === "user" ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
              </div>
              
              <div className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"} min-w-0`}>
                <div className={`px-6 py-4 rounded-2xl shadow-sm ${
                  m.role === "user" 
                    ? "bg-indigo-600 text-white rounded-tr-none" 
                    : "bg-white border border-slate-200 text-slate-800 rounded-tl-none prose prose-slate prose-sm max-w-none"
                }`}>
                  {m.role === "user" ? (
                    <div className="whitespace-pre-wrap">{m.content}</div>
                  ) : (
                    m.content ? <ReactMarkdown>{m.content}</ReactMarkdown> : <span className="inline-block w-2 h-4 bg-indigo-400 animate-pulse"></span>
                  )}
                </div>

                {m.toolMetadata && m.toolMetadata.length > 0 && (
                  <div className="mt-2 w-full space-y-2 max-w-full">
                    {m.toolMetadata.map((meta, idx) => {
                      if (meta.tool === "search_policies") {
                        return <Accordion key={idx} title="Document Citations" content={meta.data} toolType={meta.tool} />;
                      }
                      if (meta.tool === "query_orders") {
                        return <Accordion key={idx} title="Executed SQL Query" content={meta.data} toolType={meta.tool} />;
                      }
                      return null;
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        {isLoading && messages.length > 0 && messages[messages.length - 1].role === "user" && (
          <div className="flex justify-start">
            <div className="flex items-start gap-4">
              <div className="p-2.5 rounded-full bg-white border border-slate-200 text-indigo-600 shadow-sm">
                <Bot className="w-5 h-5" />
              </div>
              <div className="px-6 py-4 bg-white border border-slate-200 text-slate-500 rounded-2xl rounded-tl-none shadow-sm flex items-center space-x-2">
                <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      <footer className="bg-white border-t border-slate-200 p-6 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] z-10">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            placeholder="Ask about policies, or query your orders..."
            className="w-full pl-6 pr-28 py-4 rounded-xl border border-slate-300 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all shadow-inner text-base"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="absolute right-2 top-2 bottom-2 px-6 bg-indigo-600 text-white rounded-lg font-semibold tracking-wide hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            Send
          </button>
        </form>
      </footer>
    </div>
  );
}
