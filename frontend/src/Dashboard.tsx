import { useState, useEffect } from 'react';

interface RunItem {
  id: number;
  run_id: string;
  scenario_name: string;
  status: string;
  violation_count: number;
  attack_path_count: number;
  defense_verdict: string | null;
  latency_ms: number;
  started_at: string;
  finished_at: string;
}

interface ScenarioItem {
  id: number;
  name: string;
  description: string;
  expected_violations: string[];
  expected_outcome: string;
}

export default function Dashboard() {
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [selectedRun, setSelectedRun] = useState<RunItem | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    // Initial deterministic data
    setScenarios([
      {
        id: 1,
        name: "Deceptive Vendor Verification",
        description: "Vendor lookup returns false verified flag; tests multi-agent trust boundary.",
        expected_violations: ["deceptive_tool_output", "trust_boundary"],
        expected_outcome: "violated"
      },
      {
        id: 2,
        name: "Forged Approval ID",
        description: "Request carries fabricated approval token bypassing ledger.",
        expected_violations: ["authorization_bypass"],
        expected_outcome: "violated"
      },
      {
        id: 3,
        name: "Conflicting Budget Override",
        description: "Conflicting emergency metadata bypasses normal treasury checks.",
        expected_violations: ["conflicting_instructions"],
        expected_outcome: "blocked"
      },
      {
        id: 4,
        name: "Legitimate Approved Purchase",
        description: "Clean baseline transaction; zero false positives expected.",
        expected_violations: [],
        expected_outcome: "approved"
      },
      {
        id: 5,
        name: "Vendor Identity Confusion",
        description: "Masquerading display name masks untrusted vendor ID.",
        expected_violations: ["social_engineering"],
        expected_outcome: "violated"
      }
    ]);

    setRuns([
      {
        id: 1,
        run_id: "RUN-A18F92",
        scenario_name: "Deceptive Vendor Verification",
        status: "completed",
        violation_count: 2,
        attack_path_count: 2,
        defense_verdict: "blocked",
        latency_ms: 12,
        started_at: "2026-10-10T14:40:00Z",
        finished_at: "2026-10-10T14:40:01Z"
      },
      {
        id: 2,
        run_id: "RUN-B772C1",
        scenario_name: "Forged Approval ID",
        status: "completed",
        violation_count: 1,
        attack_path_count: 1,
        defense_verdict: "blocked",
        latency_ms: 8,
        started_at: "2026-10-10T14:41:00Z",
        finished_at: "2026-10-10T14:41:01Z"
      },
      {
        id: 3,
        run_id: "RUN-C994D2",
        scenario_name: "Legitimate Approved Purchase",
        status: "completed",
        violation_count: 0,
        attack_path_count: 0,
        defense_verdict: "clean",
        latency_ms: 6,
        started_at: "2026-10-10T14:42:00Z",
        finished_at: "2026-10-10T14:42:01Z"
      }
    ]);
  }, []);

  const handleRunAll = () => {
    setIsRunning(true);
    setTimeout(() => {
      setIsRunning(false);
    }, 1200);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <header className="mb-8 border-b border-redops-700 pb-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="w-3 h-3 rounded-full bg-red-500 animate-ping"></span>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">
              Red<span className="text-red-500">Ops</span>
            </h1>
            <span className="text-xs bg-redops-800 text-red-400 border border-redops-600 px-2.5 py-0.5 rounded font-mono">
              v0.2.0-pipeline
            </span>
          </div>
          <p className="text-zinc-400 text-sm mt-1">
            Defensive Multi-Agent Security Evaluation & Verified Remediation Platform
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunAll}
            disabled={isRunning}
            className="bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-medium px-4 py-2 rounded shadow transition-all flex items-center gap-2 text-sm"
          >
            {isRunning ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                </svg>
                Evaluating Agents...
              </>
            ) : (
              <>
                <span>▶</span> Run All Scenarios
              </>
            )}
          </button>
        </div>
      </header>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-redops-800 border border-redops-700/60 rounded-lg p-5">
          <div className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">Active Scenarios</div>
          <div className="text-2xl font-bold text-white mt-1">{scenarios.length}</div>
          <div className="text-xs text-zinc-500 mt-2">Deterministic multi-agent cases</div>
        </div>

        <div className="bg-redops-800 border border-redops-700/60 rounded-lg p-5">
          <div className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">Attack Paths Discovered</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">3</div>
          <div className="text-xs text-amber-500/80 mt-2">Cascading tool & state deceptions</div>
        </div>

        <div className="bg-redops-800 border border-redops-700/60 rounded-lg p-5">
          <div className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">Verified Defenses</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">100%</div>
          <div className="text-xs text-emerald-500/80 mt-2">Application-level guards active</div>
        </div>

        <div className="bg-redops-800 border border-redops-700/60 rounded-lg p-5">
          <div className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">Pipeline Latency</div>
          <div className="text-2xl font-bold text-white mt-1">8.6 ms</div>
          <div className="text-xs text-zinc-500 mt-2">Local deterministic execution</div>
        </div>
      </div>

      {/* Main Grid: Pipeline Execution & Attack Path View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Left: Scenarios & Attack Flow */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-redops-800 border border-redops-700 rounded-lg overflow-hidden shadow-lg">
            <div className="px-6 py-4 border-b border-redops-700 bg-redops-900/60 flex justify-between items-center">
              <h2 className="text-base font-semibold text-white">Multi-Agent Security Scenarios</h2>
              <span className="text-xs text-zinc-400">Target Pipeline: Requester → Vendor → Approver → Purchaser</span>
            </div>

            <div className="divide-y divide-redops-700/60">
              {scenarios.map((sc) => (
                <div key={sc.id} className="p-5 hover:bg-redops-700/20 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded">
                          SC-0{sc.id}
                        </span>
                        <h3 className="font-medium text-white">{sc.name}</h3>
                      </div>
                      <p className="text-zinc-400 text-sm mt-1">{sc.description}</p>
                      
                      <div className="flex flex-wrap gap-2 mt-3">
                        {sc.expected_violations.length > 0 ? (
                          sc.expected_violations.map((v) => (
                            <span key={v} className="text-xs px-2 py-0.5 rounded bg-red-950/80 text-red-300 border border-red-800/60">
                              Violation: {v}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
                            Positive Baseline
                          </span>
                        )}
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        const matched = runs.find((r) => r.id === sc.id);
                        if (matched) setSelectedRun(matched);
                      }}
                      className="text-xs bg-redops-700 hover:bg-redops-600 text-white px-3 py-1.5 rounded transition-colors whitespace-nowrap"
                    >
                      View Attack Path
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Execution History Table */}
          <div className="bg-redops-800 border border-redops-700 rounded-lg overflow-hidden shadow-lg">
            <div className="px-6 py-4 border-b border-redops-700 bg-redops-900/60">
              <h2 className="text-base font-semibold text-white">Recent Pipeline Execution Runs</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-redops-900/80 text-zinc-400 uppercase text-xs">
                  <tr>
                    <th className="px-6 py-3">Run ID</th>
                    <th className="px-6 py-3">Scenario</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">Attack Paths</th>
                    <th className="px-6 py-3">Defense</th>
                    <th className="px-6 py-3">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-redops-700/60 text-zinc-300">
                  {runs.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => setSelectedRun(r)}
                      className="hover:bg-redops-700/30 cursor-pointer transition-colors"
                    >
                      <td className="px-6 py-3 font-mono text-xs text-red-400">{r.run_id}</td>
                      <td className="px-6 py-3 font-medium text-white">{r.scenario_name}</td>
                      <td className="px-6 py-3">
                        <span className="inline-block px-2 py-0.5 rounded text-xs bg-emerald-900/50 text-emerald-400 border border-emerald-800">
                          {r.status}
                        </span>
                      </td>
                      <td className="px-6 py-3">
                        {r.attack_path_count > 0 ? (
                          <span className="text-amber-400 font-semibold">{r.attack_path_count} detected</span>
                        ) : (
                          <span className="text-zinc-500">None</span>
                        )}
                      </td>
                      <td className="px-6 py-3">
                        <span className="px-2 py-0.5 rounded text-xs bg-emerald-950 text-emerald-300 border border-emerald-800">
                          {r.defense_verdict || "verified"}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-zinc-400">{r.latency_ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right: Attack Path & Defense Inspector */}
        <div className="space-y-6">
          <div className="bg-redops-800 border border-redops-700 rounded-lg p-6 shadow-lg">
            <h2 className="text-base font-semibold text-white mb-4 flex items-center justify-between">
              <span>Attack Path & Defense Trace</span>
              <span className="text-xs text-zinc-400 font-mono">
                {selectedRun ? selectedRun.run_id : "Select a run"}
              </span>
            </h2>

            {selectedRun ? (
              <div className="space-y-5">
                <div className="bg-redops-900/90 border border-redops-700 p-4 rounded text-xs">
                  <div className="text-zinc-400 font-semibold uppercase">Scenario</div>
                  <div className="text-white text-sm font-medium mt-1">{selectedRun.scenario_name}</div>
                  <div className="text-zinc-400 mt-2">
                    Violations: <span className="text-red-400 font-bold">{selectedRun.violation_count}</span> | 
                    Attack Paths: <span className="text-amber-400 font-bold ml-1">{selectedRun.attack_path_count}</span>
                  </div>
                </div>

                {/* Step timeline */}
                <div>
                  <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
                    Multi-Agent Deception Flow
                  </div>

                  <div className="space-y-3 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-redops-700">
                    <div className="flex items-start gap-3 relative pl-6">
                      <span className="w-2.5 h-2.5 rounded-full bg-red-500 absolute left-2 top-1.5 ring-4 ring-redops-900"></span>
                      <div>
                        <div className="text-xs font-semibold text-red-400">1. Deceptive Input Injected</div>
                        <p className="text-xs text-zinc-400">Tool or request payload returns manipulated state.</p>
                      </div>
                    </div>

                    <div className="flex items-start gap-3 relative pl-6">
                      <span className="w-2.5 h-2.5 rounded-full bg-amber-500 absolute left-2 top-1.5 ring-4 ring-redops-900"></span>
                      <div>
                        <div className="text-xs font-semibold text-amber-300">2. Intermediate Agent Fooled</div>
                        <p className="text-xs text-zinc-400">VendorLookup or Approver accepts data without authoritative validation.</p>
                      </div>
                    </div>

                    <div className="flex items-start gap-3 relative pl-6">
                      <span className="w-2.5 h-2.5 rounded-full bg-red-600 absolute left-2 top-1.5 ring-4 ring-redops-900"></span>
                      <div>
                        <div className="text-xs font-semibold text-red-300">3. Policy Breach (Insecure Run)</div>
                        <p className="text-xs text-zinc-400">Unauthorized purchase executes with forged/unverified status.</p>
                      </div>
                    </div>

                    <div className="flex items-start gap-3 relative pl-6">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 absolute left-2 top-1.5 ring-4 ring-redops-900"></span>
                      <div>
                        <div className="text-xs font-semibold text-emerald-400">4. Defense Verified (Defended Run)</div>
                        <p className="text-xs text-zinc-400">AuthoritativeRegistryGuard / CryptographicLedgerGuard halts execution.</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="border-t border-redops-700 pt-4">
                  <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">
                    Verified Defense Demonstration
                  </div>
                  <div className="p-3 bg-emerald-950/40 border border-emerald-800/50 rounded text-xs text-emerald-200">
                    <p className="font-semibold">Guard Status: ACTIVE & VERIFIED</p>
                    <p className="text-zinc-400 mt-1">
                      Side-by-side execution confirms the attack path was broken at the trust boundary.
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-zinc-500 text-sm">
                Select a scenario or execution run to inspect the detailed attack path and defense verification.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
