import { useEffect, useRef, useState } from 'react';
import { Command, HelpCircle, List, Terminal, Hash, MessageSquare } from 'lucide-react';

export interface CommandSuggestion {
  command_id: string;
  command_name: string;
  command_description: string;
  command_aliases?: string[];
}

interface CommandAutocompleteProps {
  input: string;
  onSelect: (command: string) => void;
  onClose: () => void;
  hasSuggestions: boolean;
  setHasSuggestions: (has: boolean) => void;
  selectedIndex: number;
}

// Available commands (should match backend commands)
const AVAILABLE_COMMANDS: CommandSuggestion[] = [
  {
    command_id: 'help',
    command_name: 'help',
    command_description: 'Show help information',
    command_aliases: ['h', '?', '援助'],
  },
  {
    command_id: 'status',
    command_name: 'status',
    command_description: 'Show agent status',
    command_aliases: ['st', '状态'],
  },
  {
    command_id: 'list',
    command_name: 'list',
    command_description: 'List items (skills, hooks, commands, etc.)',
    command_aliases: ['ls', '列表'],
  },
  {
    command_id: 'skill',
    command_name: 'skill',
    command_description: 'Manage skills',
    command_aliases: ['sk', '技能'],
  },
  {
    command_id: 'hook',
    command_name: 'hook',
    command_description: 'Manage hooks',
    command_aliases: ['hk', '钩子'],
  },
  {
    command_id: 'memory',
    command_name: 'memory',
    command_description: 'Manage memory',
    command_aliases: ['mem', '记忆'],
  },
  {
    command_id: 'bash',
    command_name: 'bash',
    command_description: 'Execute shell commands',
    command_aliases: ['$', 'sh', '执行'],
  },
];

const COMMAND_ICONS: Record<string, React.ReactNode> = {
  help: <HelpCircle className="w-4 h-4" />,
  status: <Command className="w-4 h-4" />,
  list: <List className="w-4 h-4" />,
  skill: <Hash className="w-4 h-4" />,
  hook: <Hash className="w-4 h-4" />,
  memory: <Hash className="w-4 h-4" />,
  bash: <Terminal className="w-4 h-4" />,
};

export function CommandAutocomplete({ input, onSelect, onClose, hasSuggestions, setHasSuggestions, selectedIndex }: CommandAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<CommandSuggestion[]>([]);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Extract command from input (e.g., "/help" -> "help", "/pla" -> "pla")
  const extractCommandInput = (text: string): string => {
    const match = text.match(/^[/！？.](\S*)/);
    return match ? match[1] : '';
  };

  // Get filtered suggestions based on input
  const getFilteredSuggestions = (cmdInput: string) => {
    return AVAILABLE_COMMANDS.filter((cmd) =>
      cmd.command_name.toLowerCase().startsWith(cmdInput.toLowerCase())
    );
  };

  // Filter commands based on input - only match command names, not aliases
  useEffect(() => {
    const cmdInput = extractCommandInput(input);

    if (!cmdInput && cmdInput !== '') {
      // Show all commands if just "/" is typed
      const all = AVAILABLE_COMMANDS;
      setSuggestions(all);
      setHasSuggestions(true);
      return;
    }

    if (!cmdInput) {
      setSuggestions([]);
      setHasSuggestions(false);
      return;
    }

    const filtered = getFilteredSuggestions(cmdInput);

    setSuggestions(filtered);
    setHasSuggestions(filtered.length > 0);
  }, [input, setHasSuggestions]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  if (suggestions.length === 0) return null;

  return (
    <div
      ref={wrapperRef}
      className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden z-50"
    >
      <div className="max-h-64 overflow-y-auto">
        {suggestions.map((cmd, index) => {
          const isSelected = index === selectedIndex;
          const icon = COMMAND_ICONS[cmd.command_name] || <Command className="w-4 h-4" />;

          return (
            <button
              key={cmd.command_id}
              onClick={() => onSelect(cmd.command_name)}
              className={`w-full px-4 py-3 text-left flex items-start gap-3 transition-colors ${
                isSelected ? 'bg-gray-100' : 'bg-white'
              } hover:bg-gray-100 border-b border-gray-100 last:border-b-0`}
            >
              <div
                className={`flex-shrink-0 mt-0.5 ${
                  isSelected ? 'text-gray-900' : 'text-gray-400'
                }`}
              >
                {icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={`font-medium text-sm ${
                      isSelected ? 'text-gray-900' : 'text-gray-700'
                    }`}
                  >
                    /{cmd.command_name}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5 truncate">{cmd.command_description}</p>
              </div>
            </button>
          );
        })}
      </div>
      {suggestions.length > 1 && (
        <div className="px-4 py-2 bg-white border-t border-gray-100 text-xs text-gray-400 flex justify-between items-center">
          <span>{suggestions.length} commands</span>
          <span>↑↓ to navigate, Enter to select</span>
        </div>
      )}
    </div>
  );
}
