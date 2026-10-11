import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { WorkflowsPage } from './pages/WorkflowsPage';
import { LiveRunPage } from './pages/LiveRunPage';
import { AutomationPage } from './pages/AutomationPage';
import { RunHistoryTable } from './components/RunHistoryTable';
import { RunDetailModal } from './components/RunDetailModal';
import { RunComparatorModal } from './components/RunComparatorModal';
import { AuthModal } from './components/AuthModal';
import {
  getWorkflows,
  getRuns,
  triggerRun,
  deleteRun,
  getMe,
  resumeRun,
  cleanupRuns,
  clearAllRuns,
  getEnvironments,
  setActiveApiEnvironment,
  getActiveApiEnvironment,
} from './api';
import { WorkflowSchema, WorkflowRun, UserProfile, EnvironmentInfo } from './types';
import { RotateCw } from 'lucide-react';

export function App() {
  const urlParams = new URLSearchParams(window.location.search);
  const initialTab = (urlParams.get('tab') as 'workflows' | 'live' | 'history' | 'automation') || 'workflows';
  const initialRunId = urlParams.get('run_id');
  const initialEnvParam = urlParams.get('env');
  const initialCompareA = urlParams.get('compare_a');
  const initialCompareB = urlParams.get('compare_b');
  const initialEnvA = urlParams.get('env_a') || initialEnvParam || undefined;
  const initialEnvB = urlParams.get('env_b') || initialEnvParam || undefined;

  const [currentTab, setCurrentTab] = useState<'workflows' | 'live' | 'history' | 'automation'>(initialTab);
  const [workflows, setWorkflows] = useState<Record<string, WorkflowSchema>>({});
  const [recentRuns, setRecentRuns] = useState<WorkflowRun[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(initialRunId);
  const [selectedRunModal, setSelectedRunModal] = useState<WorkflowRun | null>(null);
  const [comparatorTarget, setComparatorTarget] = useState<{
    runA: string;
    runB: string;
    envA?: string;
    envB?: string;
  } | null>(
    initialCompareA && initialCompareB
      ? { runA: initialCompareA, runB: initialCompareB, envA: initialEnvA, envB: initialEnvB }
      : null
  );
  const [isLoadingWorkflows, setIsLoadingWorkflows] = useState(true);

  // Environments State
  const [environments, setEnvironments] = useState<EnvironmentInfo[]>([
    {
      id: 'dev',
      label: 'Development',
      badge: 'DEV',
      color: 'emerald',
      description: 'Local sandbox and feature testing',
      is_prod: false,
      requires_confirmation: false,
    },
    {
      id: 'uat',
      label: 'UAT / Staging',
      badge: 'UAT',
      color: 'amber',
      description: 'Integration and pre-release verification',
      is_prod: false,
      requires_confirmation: false,
    },
    {
      id: 'prod',
      label: 'Production',
      badge: 'PROD',
      color: 'rose',
      description: 'Live customer workloads with guardrails',
      is_prod: true,
      requires_confirmation: true,
    },
  ]);
  const [activeEnvironment, setActiveEnvironment] = useState<string>(initialEnvParam || getActiveApiEnvironment());

  // Authentication State
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const handleTabChange = (tab: 'workflows' | 'live' | 'history' | 'automation') => {
    setCurrentTab(tab);
    const params = new URLSearchParams(window.location.search);
    params.set('tab', tab);
    if (tab !== 'live') params.delete('run_id');
    window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
  };

  const handleSelectEnvironment = async (envId: string) => {
    setActiveApiEnvironment(envId);
    setActiveEnvironment(envId);
    try {
      const runsData = await getRuns(50, undefined, undefined, envId);
      setRecentRuns(runsData);
    } catch (e) {
      console.error('Failed to load runs for environment:', envId, e);
    }
  };

  // Initial load
  const loadInitialData = async () => {
    try {
      const [envData, wfData, runsData, userProfile] = await Promise.all([
        getEnvironments().catch(() => null),
        getWorkflows(),
        getRuns(50, undefined, undefined, activeEnvironment),
        getMe().catch(() => ({
          authenticated: false,
          username: 'anonymous',
          role: 'guest',
          auth_enabled: true,
        })),
      ]);
      if (envData && envData.allowed_environments?.length > 0) {
        setEnvironments(envData.allowed_environments);
        if (envData.active_env) {
          const resolvedEnv = initialEnvParam || activeEnvironment || envData.active_env;
          setActiveEnvironment(resolvedEnv);
          setActiveApiEnvironment(resolvedEnv);
        }
      }
      setWorkflows(wfData);
      setRecentRuns(runsData);
      setCurrentUser(userProfile);
    } catch (err) {
      console.error('Failed to load initial platform data:', err);
    } finally {
      setIsLoadingWorkflows(false);
    }
  };

  useEffect(() => {
    loadInitialData();
    const interval = setInterval(async () => {
      try {
        const runsData = await getRuns(50, undefined, undefined, activeEnvironment);
        setRecentRuns(runsData);
      } catch (e) {
        // quiet poll fail
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [activeEnvironment]);

  const handleTriggerRun = async (
    workflowName: string,
    inputs: Record<string, any>,
    meta?: { environment?: string; profile?: string }
  ) => {
    const targetEnv = meta?.environment || activeEnvironment;
    const targetProfile = meta?.profile || targetEnv;
    try {
      const res = await triggerRun(workflowName, inputs, true, targetEnv, targetProfile);
      setActiveRunId(res.run_id);
      handleTabChange('live');
      const params = new URLSearchParams(window.location.search);
      params.set('tab', 'live');
      params.set('run_id', res.run_id);
      window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
      // Refresh runs list for target environment
      getRuns(50, undefined, undefined, targetEnv).then(setRecentRuns);
    } catch (err: any) {
      alert(`Error triggering workflow: ${err.message}`);
    }
  };

  const handleResumeRun = async (runId: string, fromStep?: string) => {
    try {
      const result = await resumeRun(runId, fromStep, undefined, activeEnvironment);
      setActiveRunId(result.run_id);
      setCurrentTab('live');
      const params = new URLSearchParams(window.location.search);
      params.set('tab', 'live');
      params.set('run_id', result.run_id);
      window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
      getRuns(50, undefined, undefined, activeEnvironment).then(setRecentRuns);
    } catch (err: any) {
      alert(`Failed to resume workflow run: ${err.message}`);
    }
  };

  const handlePruneRuns = async (keepCount: number) => {
    try {
      const res = await cleanupRuns(keepCount, activeEnvironment);
      alert(res.message);
      const updated = await getRuns(50, undefined, undefined, activeEnvironment);
      setRecentRuns(updated);
    } catch (err: any) {
      alert(`Failed to prune runs: ${err.message}`);
    }
  };

  const handleClearAllRuns = async () => {
    if (!confirm(`Clear all runs and run vacuum in ${activeEnvironment.toUpperCase()} database?`)) return;
    try {
      await clearAllRuns(activeEnvironment);
      setRecentRuns([]);
      if (activeRunId) {
        setActiveRunId(null);
        handleTabChange('workflows');
      }
    } catch (err: any) {
      alert(`Failed to clear run history: ${err.message}`);
    }
  };

  const handleRerun = (workflowName: string, inputs: Record<string, any>) => {
    handleTriggerRun(workflowName, inputs, { environment: activeEnvironment });
  };

  const handleDeleteRun = async (runId: string) => {
    if (!confirm(`Delete execution record ${runId}?`)) return;
    try {
      await deleteRun(runId, activeEnvironment);
      setRecentRuns((prev) => prev.filter((r) => r.id !== runId));
      if (activeRunId === runId) {
        setActiveRunId(null);
        handleTabChange('workflows');
      }
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleOpenComparator = (runAId: string, runBId?: string, envA?: string, envB?: string) => {
    let resolvedB = runBId;
    let resolvedEnvB = envB;
    if (!resolvedB) {
      const other = recentRuns.find((r) => r.id !== runAId);
      if (other) {
        resolvedB = other.id;
        resolvedEnvB = other.environment || activeEnvironment;
      } else {
        resolvedB = runAId;
        resolvedEnvB = envA || activeEnvironment;
      }
    }
    setComparatorTarget({
      runA: runAId,
      runB: resolvedB,
      envA: envA || activeEnvironment,
      envB: resolvedEnvB || activeEnvironment,
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col font-sans">
      <Navbar
        currentTab={currentTab}
        onSelectTab={handleTabChange}
        activeRunId={activeRunId}
        currentUser={currentUser}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        environments={environments}
        activeEnvironment={activeEnvironment}
        onSelectEnvironment={handleSelectEnvironment}
      />

      <main className="flex-1 w-full max-w-[1920px] 2xl:max-w-none 2xl:px-12 mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {isLoadingWorkflows ? (
          <div className="py-24 flex flex-col items-center justify-center space-y-3 text-slate-400">
            <RotateCw className="h-8 w-8 animate-spin text-sky-500" />
            <p className="text-sm font-medium">Connecting to Valiant Engine...</p>
          </div>
        ) : (
          <>
            {currentTab === 'workflows' && (
              <WorkflowsPage
                workflows={workflows}
                recentRuns={recentRuns}
                onTriggerRun={handleTriggerRun}
                activeEnvironment={activeEnvironment}
              />
            )}

            {currentTab === 'live' && activeRunId && (
              <LiveRunPage
                runId={activeRunId}
                onBackToWorkflows={() => setCurrentTab('workflows')}
              />
            )}

            {currentTab === 'history' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-xl font-bold text-slate-100">
                    Execution History ({activeEnvironment.toUpperCase()})
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Persistent audit trail for isolated database{' '}
                    <span className="font-mono text-slate-300 font-semibold">
                      valiant_{activeEnvironment}.db
                    </span>
                    .
                  </p>
                </div>
                <RunHistoryTable
                  runs={recentRuns}
                  activeEnvironment={activeEnvironment}
                  onSelectRun={setSelectedRunModal}
                  onRerun={handleRerun}
                  onResume={handleResumeRun}
                  onDeleteRun={handleDeleteRun}
                  onPruneRuns={handlePruneRuns}
                  onClearAllRuns={handleClearAllRuns}
                  onCompareRuns={handleOpenComparator}
                />
              </div>
            )}

            {currentTab === 'automation' && (
              <AutomationPage
                workflows={workflows}
                activeEnvironment={activeEnvironment}
                onViewRunDetail={(runId) => handleOpenComparator(runId)}
              />
            )}
          </>
        )}
      </main>

      {/* Modal for Inspecting Any Historical Run */}
      <RunDetailModal
        run={selectedRunModal}
        onClose={() => setSelectedRunModal(null)}
        onResumeRun={handleResumeRun}
        onOpenComparator={(runId, env) => handleOpenComparator(runId, undefined, env)}
      />

      {/* Modal for Side-by-Side Regression and Latency Diffing */}
      {comparatorTarget && (
        <RunComparatorModal
          runAId={comparatorTarget.runA}
          runBId={comparatorTarget.runB}
          envA={comparatorTarget.envA}
          envB={comparatorTarget.envB}
          availableRuns={recentRuns}
          onClose={() => {
            setComparatorTarget(null);
            const params = new URLSearchParams(window.location.search);
            params.delete('compare_a');
            params.delete('compare_b');
            window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
          }}
          onSelectRunDetail={(run) => {
            setComparatorTarget(null);
            setSelectedRunModal(run);
          }}
        />
      )}

      {/* Operator Authentication Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        currentUser={currentUser}
        onAuthChange={(user) => {
          setCurrentUser(user);
          getRuns(50, undefined, undefined, activeEnvironment).then(setRecentRuns);
        }}
      />
    </div>
  );
}

export default App;
