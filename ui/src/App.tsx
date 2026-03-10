import { useState } from "react";
import { WorkflowCanvas } from "./components/workflow/WorkflowCanvas";
import { LogViewer } from "./components/logs/LogViewer";
import { ChatPanel } from "./components/chat/ChatPanel";
import { MemoryPanel } from "./components/memory/MemoryPanel";
import TokenUsagePanel from "./components/token/TokenUsagePanel";
import IntegrationList from "./components/settings/IntegrationList";
import { MessageSquare, Activity, FileText, Database, Bot, BarChart3, Key } from "lucide-react";

type TabType = "chat" | "workflow" | "logs" | "memory" | "token" | "keys";

interface NavItem {
  id: TabType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "workflow", label: "Workflow", icon: Activity },
  { id: "logs", label: "Logs", icon: FileText },
  { id: "memory", label: "Memory", icon: Database },
  { id: "token", label: "Token", icon: BarChart3 },
  { id: "keys", label: "Settings", icon: Key },
];

function App() {
  const [activeTab, setActiveTab] = useState<TabType>("chat");

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-20 bg-white border-r border-gray-200 flex flex-col items-center py-4">
        {/* Logo */}
        <div className="mb-6 p-2">
          <Bot className="w-8 h-8 text-purple-600" />
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-14 h-14 rounded-xl flex items-center justify-center transition-all ${
                  activeTab === item.id
                    ? "bg-purple-100 text-purple-600 shadow-md"
                    : "text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                }`}
                title={item.label}
              >
                <Icon className="w-6 h-6" />
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="pt-4 border-t border-gray-200">
          <div className="text-xs text-gray-400 text-center">
            MUL
            <br />
            Agent
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {/* Header */}
        <div className="h-14 bg-white border-b border-gray-200 flex items-center px-6">
          <h1 className="text-lg font-semibold text-gray-900">
            {navItems.find((item) => item.id === activeTab)?.label}
          </h1>
        </div>

        {/* Content Area */}
        <div className="h-[calc(100vh-8.5rem)] overflow-hidden">
          {/* All tabs are mounted simultaneously to preserve state */}
          <div className={`h-full ${activeTab === "chat" ? "" : "hidden"}`}>
            <ChatPanel />
          </div>
          <div className={`h-full ${activeTab === "workflow" ? "" : "hidden"}`}>
            <WorkflowCanvas />
          </div>
          <div className={`h-full ${activeTab === "logs" ? "" : "hidden"}`}>
            <LogViewer />
          </div>
          <div className={`h-full ${activeTab === "memory" ? "" : "hidden"}`}>
            <MemoryPanel />
          </div>
          <div className={`h-full ${activeTab === "token" ? "" : "hidden"}`}>
            <TokenUsagePanel />
          </div>
          <div className={`h-full ${activeTab === "keys" ? "" : "hidden"}`}>
            <IntegrationList />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
