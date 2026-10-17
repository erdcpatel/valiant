import React from 'react';
import { PlayCircle, History, Layers, Zap, Terminal, User, ShieldCheck, Clock } from 'lucide-react';
import { UserProfile, EnvironmentInfo } from '../types';
import { EnvironmentSelector } from './EnvironmentSelector';

interface NavbarProps {
  currentTab: 'workflows' | 'live' | 'history' | 'automation';
  onSelectTab: (tab: 'workflows' | 'live' | 'history' | 'automation') => void;
  activeRunId?: string | null;
  currentUser: UserProfile | null;
  onOpenAuth: () => void;
  environments: EnvironmentInfo[];
  activeEnvironment: string;
  onSelectEnvironment: (env: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  onSelectTab,
  activeRunId,
  currentUser,
  onOpenAuth,
  environments,
  activeEnvironment,
  onSelectEnvironment,
}) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="max-w-[1720px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onSelectTab('workflows')}>
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-sky-600 via-indigo-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <Zap className="h-5 w-5 text-white fill-white" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-sky-400 bg-clip-text text-transparent">
              VALIANTFLOW
            </span>
            <span className="ml-2 px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase bg-sky-500/10 text-sky-400 border border-sky-500/20 rounded-full">
              v0.0.1 Beta
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center space-x-1 sm:space-x-2">
          <button
            onClick={() => onSelectTab('workflows')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
              currentTab === 'workflows'
                ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Layers className="h-4 w-4" />
            <span>Workflows</span>
          </button>

          {activeRunId && (
            <button
              onClick={() => onSelectTab('live')}
              className={`relative flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                currentTab === 'live'
                  ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
              </span>
              <PlayCircle className="h-4 w-4" />
              <span>Live Run</span>
            </button>
          )}

          <button
            onClick={() => onSelectTab('history')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
              currentTab === 'history'
                ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <History className="h-4 w-4" />
            <span>Run History</span>
          </button>

          <button
            onClick={() => onSelectTab('automation')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
              currentTab === 'automation'
                ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Clock className="h-4 w-4" />
            <span>Automation</span>
          </button>
        </nav>

        {/* Status & User Profile Trigger */}
        <div className="flex items-center space-x-2.5">
          {/* Environment Selector Dropdown */}
          <EnvironmentSelector
            environments={environments}
            activeEnvironment={activeEnvironment}
            onSelectEnvironment={onSelectEnvironment}
          />

          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className="hidden md:flex items-center space-x-1.5 px-3 py-1.5 text-xs font-mono font-medium text-slate-400 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors"
          >
            <Terminal className="h-3.5 w-3.5" />
            <span>API Docs</span>
          </a>

          {/* User Sign-In Button / Active Badge */}
          <button
            type="button"
            onClick={onOpenAuth}
            className={`inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              currentUser?.authenticated
                ? 'bg-emerald-950/60 border-emerald-800/80 text-emerald-300 hover:bg-emerald-900/50'
                : 'bg-slate-900 border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
          >
            {currentUser?.authenticated ? (
              <>
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                <span className="font-semibold">{currentUser.username}</span>
                <span className="text-[10px] uppercase font-bold text-emerald-400/80">({currentUser.role})</span>
              </>
            ) : (
              <>
                <User className="h-3.5 w-3.5 text-slate-400" />
                <span>Operator Sign In</span>
              </>
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
