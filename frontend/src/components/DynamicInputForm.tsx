import React, { useState, useEffect } from 'react';
import { InputFieldSchema } from '../types';
import {
  Eye,
  EyeOff,
  Play,
  AlertCircle,
  HelpCircle,
  Sliders,
  Sparkles,
  ShieldAlert,
  Server,
  CheckCircle2,
} from 'lucide-react';

interface DynamicInputFormProps {
  fields: InputFieldSchema[];
  profiles?: Record<string, Record<string, any>>;
  activeEnvironment?: string;
  onSubmit: (values: Record<string, any>, meta?: { environment?: string; profile?: string }) => void;
  isLoading?: boolean;
  submitLabel?: string;
}

export const DynamicInputForm: React.FC<DynamicInputFormProps> = ({
  fields,
  profiles = {},
  activeEnvironment = 'dev',
  onSubmit,
  isLoading = false,
  submitLabel = 'Execute Workflow',
}) => {
  const [values, setValues] = useState<Record<string, any>>({});
  const [showPassword, setShowPassword] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [selectedProfile, setSelectedProfile] = useState<string>(activeEnvironment);
  const [prodConfirmed, setProdConfirmed] = useState<boolean>(false);
  const [presetNotice, setPresetNotice] = useState<string | null>(null);

  // The active environment from the top navbar is the single source of truth
  const isProd = activeEnvironment === 'prod';

  // Initialize or re-apply profile preset when environment or schema changes
  useEffect(() => {
    applyProfileValues(activeEnvironment, false);
    setSelectedProfile(activeEnvironment);
    setProdConfirmed(false);
  }, [fields, activeEnvironment]);

  const applyProfileValues = (profileKey: string, showAnimation = true) => {
    const initial: Record<string, any> = {};
    // 1. Defaults from schema
    fields.forEach((f) => {
      initial[f.name] = f.default !== undefined && f.default !== null ? f.default : '';
    });

    // 2. Override with profile values if available
    const profValues = profiles[profileKey];
    if (profValues) {
      Object.entries(profValues).forEach(([k, v]) => {
        initial[k] = v;
      });
      if (showAnimation) {
        setPresetNotice(`Loaded preset for ${profileKey.toUpperCase()}`);
        setTimeout(() => setPresetNotice(null), 3000);
      }
    }

    setValues(initial);
    setErrors({});
  };

  const handleSelectProfile = (pKey: string) => {
    setSelectedProfile(pKey);
    applyProfileValues(pKey, true);
  };

  const handleChange = (name: string, val: any) => {
    setValues((prev) => ({ ...prev, [name]: val }));
    if (errors[name]) {
      setErrors((prev) => {
        const copy = { ...prev };
        delete copy[name];
        return copy;
      });
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    fields.forEach((f) => {
      const val = values[f.name];
      if (f.required && (val === undefined || val === '' || val === null)) {
        newErrors[f.name] = `${f.label || f.name} is required`;
      }
      if (f.type === 'number' && val !== '' && val !== undefined && val !== null) {
        const num = Number(val);
        if (f.min_value !== undefined && f.min_value !== null && num < f.min_value) {
          newErrors[f.name] = `Minimum allowed is ${f.min_value}`;
        }
        if (f.max_value !== undefined && f.max_value !== null && num > f.max_value) {
          newErrors[f.name] = `Maximum allowed is ${f.max_value}`;
        }
      }
    });

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    if (isProd && !prodConfirmed) {
      setErrors({ _form: 'Please check the confirmation box to authorize this production run.' });
      return;
    }

    onSubmit(values, {
      environment: activeEnvironment,
      profile: selectedProfile,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Environment Context Banner */}
      <div className="p-3.5 rounded-2xl bg-slate-950/70 border border-slate-800/80 flex items-center justify-between text-xs">
        <div className="flex items-center space-x-2.5">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              activeEnvironment === 'prod'
                ? 'bg-rose-400 ring-4 ring-rose-500/20'
                : activeEnvironment === 'uat'
                ? 'bg-amber-400 ring-4 ring-amber-500/20'
                : 'bg-emerald-400 ring-4 ring-emerald-500/20'
            }`}
          />
          <div>
            <span className="font-semibold text-slate-200">
              Target Environment: <span className="font-mono uppercase">{activeEnvironment}</span>
            </span>
            <span className="text-slate-500 text-[11px] ml-2 font-mono">
              (valiant_{activeEnvironment}.db)
            </span>
          </div>
        </div>
        {profiles[activeEnvironment] && (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
            ✓ Auto-applied {activeEnvironment.toUpperCase()} defaults
          </span>
        )}
      </div>

      {/* Production Safeguard Warning */}
      {isProd && (
        <div className="p-4 rounded-2xl bg-rose-950/30 border border-rose-500/30 space-y-3 animate-fadeIn">
          <div className="flex items-start space-x-3">
            <ShieldAlert className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-bold text-rose-200">
                Production Guardrails Active
              </h4>
              <p className="text-xs text-rose-300/80 mt-0.5 leading-relaxed">
                This workflow run will execute against live systems and record audit logs into{' '}
                <span className="font-mono text-rose-200 font-semibold">valiant_prod.db</span>.
              </p>
            </div>
          </div>

          <label className="flex items-center space-x-2.5 pt-1 text-xs text-rose-200 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={prodConfirmed}
              onChange={(e) => {
                setProdConfirmed(e.target.checked);
                if (errors._form) {
                  setErrors((prev) => {
                    const copy = { ...prev };
                    delete copy._form;
                    return copy;
                  });
                }
              }}
              className="h-4 w-4 rounded border-rose-500/50 bg-slate-900 text-rose-600 focus:ring-rose-500 focus:ring-offset-slate-900"
            />
            <span className="font-medium">
              I understand and explicitly authorize execution in the PRODUCTION environment.
            </span>
          </label>
        </div>
      )}

      {/* Input Parameters Form Fields */}
      {fields.length === 0 ? (
        <div className="p-6 text-center text-slate-400 bg-slate-900/40 rounded-xl border border-slate-800">
          <p className="text-sm">This workflow requires no additional parameters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {fields.map((field) => {
            const isError = !!errors[field.name];

            return (
              <div
                key={field.name}
                className={`space-y-1.5 ${field.type === 'checkbox' ? 'md:col-span-2' : ''}`}
              >
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center space-x-1">
                    <span>{field.label || field.name}</span>
                    {field.required && <span className="text-rose-400">*</span>}
                  </label>
                  {field.help_text && (
                    <span className="text-[11px] text-slate-500 truncate max-w-[200px]" title={field.help_text}>
                      {field.help_text}
                    </span>
                  )}
                </div>

                {field.type === 'select' ? (
                  <select
                    value={values[field.name] ?? ''}
                    onChange={(e) => handleChange(field.name, e.target.value)}
                    className={`w-full bg-slate-900 border ${
                      isError ? 'border-rose-500' : 'border-slate-800'
                    } rounded-lg px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors`}
                  >
                    {field.options?.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                ) : field.type === 'checkbox' ? (
                  <label className="flex items-center space-x-2.5 pt-2 text-sm text-slate-200 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!!values[field.name]}
                      onChange={(e) => handleChange(field.name, e.target.checked)}
                      className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-sky-500 focus:ring-sky-500 focus:ring-offset-slate-900"
                    />
                    <span>{field.help_text || field.label || field.name}</span>
                  </label>
                ) : field.type === 'password' ? (
                  <div className="relative">
                    <input
                      type={showPassword[field.name] ? 'text' : 'password'}
                      value={values[field.name] ?? ''}
                      onChange={(e) => handleChange(field.name, e.target.value)}
                      placeholder={field.help_text || 'Enter secret...'}
                      className={`w-full bg-slate-900 border ${
                        isError ? 'border-rose-500' : 'border-slate-800'
                      } rounded-lg px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors pr-10`}
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setShowPassword((prev) => ({
                          ...prev,
                          [field.name]: !prev[field.name],
                        }))
                      }
                      className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-300"
                    >
                      {showPassword[field.name] ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                ) : field.type === 'number' ? (
                  <input
                    type="number"
                    value={values[field.name] ?? ''}
                    onChange={(e) =>
                      handleChange(
                        field.name,
                        e.target.value === '' ? '' : Number(e.target.value)
                      )
                    }
                    placeholder={field.help_text || '0'}
                    className={`w-full bg-slate-900 border ${
                      isError ? 'border-rose-500' : 'border-slate-800'
                    } rounded-lg px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors font-mono`}
                  />
                ) : (
                  <input
                    type={field.type === 'email' ? 'email' : 'text'}
                    value={values[field.name] ?? ''}
                    onChange={(e) => handleChange(field.name, e.target.value)}
                    placeholder={field.help_text || `Enter ${field.label || field.name}`}
                    className={`w-full bg-slate-900 border ${
                      isError ? 'border-rose-500' : 'border-slate-800'
                    } rounded-lg px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors`}
                  />
                )}

                {isError && (
                  <p className="text-xs text-rose-400 flex items-center space-x-1 pt-0.5">
                    <AlertCircle className="h-3 w-3" />
                    <span>{errors[field.name]}</span>
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {errors._form && (
        <p className="text-xs text-rose-400 flex items-center space-x-1.5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>{errors._form}</span>
        </p>
      )}

      {/* Submit Execution Button */}
      <div className="pt-2">
        <button
          type="submit"
          disabled={isLoading || (isProd && !prodConfirmed)}
          className={`w-full flex items-center justify-center space-x-2 px-6 py-3.5 rounded-xl text-sm font-semibold text-white transition-all transform active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed ${
            isProd
              ? 'bg-gradient-to-r from-rose-600 to-red-700 hover:from-rose-500 hover:to-red-600 shadow-lg shadow-rose-600/30'
              : 'bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 shadow-lg shadow-sky-600/25'
          }`}
        >
          <Play className="h-4 w-4 fill-white" />
          <span>
            {isLoading
              ? 'Triggering Execution...'
              : isProd
              ? 'Execute in PRODUCTION'
              : `Execute in ${activeEnvironment.toUpperCase()}`}
          </span>
        </button>
      </div>
    </form>
  );
};
