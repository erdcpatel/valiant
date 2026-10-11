import React, { useState, useRef, useEffect } from 'react';
import { EnvironmentInfo } from '../types';
import { ChevronDown, Check, ShieldAlert, Database, Server } from 'lucide-react';

interface EnvironmentSelectorProps {
  environments: EnvironmentInfo[];
  activeEnvironment: string;
  onSelectEnvironment: (envId: string) => void;
}

export const EnvironmentSelector: React.FC<EnvironmentSelectorProps> = ({
  environments,
  activeEnvironment,
  onSelectEnvironment,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentEnv =
    environments.find((e) => e.id === activeEnvironment) ||
    environments[0] || {
      id: 'dev',
      label: 'Development',
      badge: 'DEV',
      color: 'emerald',
      description: 'Local sandbox',
      is_prod: false,
      requires_confirmation: false,
    };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getEnvBadgeClasses = (color: string, isProd: boolean) => {
    if (isProd) {
      return 'bg-rose-500/10 text-rose-400 border-rose-500/30 hover:bg-rose-500/20';
    }
    if (color === 'amber') {
      return 'bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20';
    }
    return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20';
  };

  const getDotClasses = (color: string, isProd: boolean) => {
    if (isProd) return 'bg-rose-400 shadow-rose-500/50';
    if (color === 'amber') return 'bg-amber-400 shadow-amber-500/50';
    return 'bg-emerald-400 shadow-emerald-500/50';
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`inline-flex items-center space-x-2 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all duration-200 active:scale-95 shadow-sm ${getEnvBadgeClasses(
          currentEnv.color,
          currentEnv.is_prod
        )}`}
        title={`Active Environment: ${currentEnv.label}`}
      >
        <span
          className={`h-2 w-2 rounded-full shadow-sm animate-pulse ${getDotClasses(
            currentEnv.color,
            currentEnv.is_prod
          )}`}
        />
        <span className="font-mono tracking-wider">{currentEnv.badge}</span>
        {currentEnv.is_prod && <ShieldAlert className="h-3 w-3 text-rose-400" />}
        <ChevronDown
          className={`h-3 w-3 text-slate-400 transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl z-50 p-2 space-y-1 animate-fadeIn">
          <div className="px-3 py-2 border-b border-slate-800/80">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono uppercase text-slate-400 font-semibold flex items-center space-x-1.5">
                <Server className="h-3 w-3 text-sky-400" />
                <span>Execution Target</span>
              </span>
              <span className="text-[10px] text-slate-500 flex items-center space-x-1">
                <Database className="h-3 w-3 text-slate-400" />
                <span>Isolated DB</span>
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Switching changes workflow history & data storage
            </p>
          </div>

          <div className="pt-1 space-y-1">
            {environments.map((env) => {
              const isSelected = env.id === activeEnvironment;
              return (
                <button
                  key={env.id}
                  type="button"
                  onClick={() => {
                    onSelectEnvironment(env.id);
                    setIsOpen(false);
                  }}
                  className={`w-full text-left p-2.5 rounded-xl transition-all flex items-start justify-between group ${
                    isSelected
                      ? 'bg-slate-800/90 border border-slate-700/80'
                      : 'hover:bg-slate-800/50 border border-transparent'
                  }`}
                >
                  <div className="flex items-start space-x-2.5">
                    <span
                      className={`mt-1 h-2 w-2 rounded-full flex-shrink-0 ${getDotClasses(
                        env.color,
                        env.is_prod
                      )}`}
                    />
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-semibold text-slate-200 group-hover:text-white">
                          {env.label}
                        </span>
                        <span
                          className={`text-[9px] font-mono px-1.5 py-0.2 rounded border ${getEnvBadgeClasses(
                            env.color,
                            env.is_prod
                          )}`}
                        >
                          {env.badge}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                        {env.description}
                      </p>
                      <p className="text-[10px] font-mono text-slate-500 mt-1 flex items-center space-x-1">
                        <Database className="h-2.5 w-2.5" />
                        <span>valiant_{env.id}.db</span>
                      </p>
                    </div>
                  </div>

                  {isSelected && (
                    <div className="p-1 rounded-md bg-sky-500/10 text-sky-400 flex-shrink-0 mt-0.5">
                      <Check className="h-3.5 w-3.5" />
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {currentEnv.is_prod && (
            <div className="mt-2 p-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-300 flex items-center space-x-2">
              <ShieldAlert className="h-4 w-4 text-rose-400 flex-shrink-0" />
              <span>Production guardrails active. Confirmations required for live runs.</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
