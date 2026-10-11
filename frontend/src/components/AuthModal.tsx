import React, { useState } from 'react';
import { UserProfile } from '../types';
import { loginUser, logoutUser } from '../api';
import { Lock, User, Key, LogIn, LogOut, AlertCircle, ShieldCheck, X } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: UserProfile | null;
  onAuthChange: (user: UserProfile) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onAuthChange,
}) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const data = await loginUser(username, password);
      onAuthChange({
        authenticated: true,
        username: data.username,
        role: data.role,
        name: data.name,
        email: data.email,
        auth_enabled: true,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    setLoading(true);
    try {
      await logoutUser();
      onAuthChange({
        authenticated: false,
        username: 'anonymous',
        role: 'guest',
        auth_enabled: true,
      });
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const quickSwitch = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400">
              <Lock className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">
                {currentUser?.authenticated ? 'User Profile & Identity' : 'Authenticate Operator'}
              </h3>
              <p className="text-[11px] text-slate-400">Records workflow execution attribution</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {currentUser?.authenticated ? (
            <div className="space-y-5">
              <div className="p-4 rounded-xl bg-slate-950/70 border border-emerald-900/40 space-y-3">
                <div className="flex items-center space-x-2 text-emerald-400 text-xs font-semibold">
                  <ShieldCheck className="h-4 w-4" />
                  <span>Authenticated Session Active</span>
                </div>
                <div className="space-y-1 text-xs">
                  <p className="text-slate-400">
                    Signed in as: <span className="font-semibold text-slate-100">{currentUser.name || currentUser.username}</span>
                  </p>
                  <p className="text-slate-400">
                    Username: <span className="font-mono text-sky-400">{currentUser.username}</span>
                  </p>
                  <p className="text-slate-400">
                    Role: <span className="uppercase text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">{currentUser.role}</span>
                  </p>
                  {currentUser.email && (
                    <p className="text-slate-400">
                      Email: <span className="text-slate-300">{currentUser.email}</span>
                    </p>
                  )}
                </div>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed">
                All subsequent workflow executions and history runs will be recorded under your operator ID.
              </p>

              <button
                type="button"
                onClick={handleLogout}
                disabled={loading}
                className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-rose-300 bg-rose-950/40 hover:bg-rose-900/40 border border-rose-800/60 transition-colors disabled:opacity-50"
              >
                <LogOut className="h-4 w-4" />
                <span>{loading ? 'Logging out...' : 'Sign Out Session'}</span>
              </button>
            </div>
          ) : (
            <form onSubmit={handleLogin} className="space-y-4">
              {error && (
                <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-800/50 text-xs text-rose-300 flex items-center space-x-2">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Username
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. admin or operator"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-sky-500 transition-colors"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Password
                </label>
                <div className="relative">
                  <Key className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-sky-500 transition-colors"
                  />
                </div>
              </div>

              {/* Static Preset Demo Logins */}
              <div className="pt-1">
                <p className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider mb-1.5">
                  Preset Roles (Static Demo / Testing):
                </p>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => quickSwitch('admin', 'admin123')}
                    className="p-1.5 text-center text-[11px] rounded bg-slate-950 border border-slate-800 hover:border-sky-500/50 text-slate-300 transition-colors font-mono"
                  >
                    admin
                  </button>
                  <button
                    type="button"
                    onClick={() => quickSwitch('operator', 'operator123')}
                    className="p-1.5 text-center text-[11px] rounded bg-slate-950 border border-slate-800 hover:border-sky-500/50 text-slate-300 transition-colors font-mono"
                  >
                    operator
                  </button>
                  <button
                    type="button"
                    onClick={() => quickSwitch('viewer', 'viewer123')}
                    className="p-1.5 text-center text-[11px] rounded bg-slate-950 border border-slate-800 hover:border-sky-500/50 text-slate-300 transition-colors font-mono"
                  >
                    viewer
                  </button>
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all disabled:opacity-50"
                >
                  <LogIn className="h-4 w-4" />
                  <span>{loading ? 'Authenticating...' : 'Sign In'}</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
