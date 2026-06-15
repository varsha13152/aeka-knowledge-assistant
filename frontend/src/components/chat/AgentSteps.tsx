'use client';

/**
 * Agent activity visualizer — shows multi-agent reasoning steps in real-time.
 *
 * Displays:
 * - Which agent is active (router, researcher, validator, etc.)
 * - Actions taken at each step
 * - Timing and token usage
 */

import type { AgentStep } from '@/stores/chatStore';

interface AgentStepsProps {
  steps: AgentStep[];
}

const NODE_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  input_guardrail: { label: 'Safety Check', icon: '🛡️', color: 'text-yellow-600' },
  router: { label: 'Intent Router', icon: '🔀', color: 'text-blue-600' },
  research: { label: 'Research Agent', icon: '🔍', color: 'text-green-600' },
  validator: { label: 'Validator', icon: '✓', color: 'text-purple-600' },
  escalation: { label: 'HITL Escalation', icon: '⚠️', color: 'text-orange-600' },
  output_guardrail: { label: 'Output Filter', icon: '🛡️', color: 'text-yellow-600' },
  output: { label: 'Response', icon: '💬', color: 'text-gray-600' },
  retrieval: { label: 'Retrieval', icon: '📄', color: 'text-teal-600' },
};

export function AgentSteps({ steps }: AgentStepsProps) {
  if (steps.length === 0) {
    return (
      <div className="p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Agent Activity</h3>
        <p className="text-xs text-gray-400">
          Agent reasoning steps will appear here as your query is processed.
        </p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Agent Activity</h3>
      <div className="space-y-2">
        {steps.map((step, index) => {
          const nodeInfo = NODE_LABELS[step.node] || {
            label: step.node,
            icon: '⚙️',
            color: 'text-gray-600',
          };

          return (
            <div
              key={index}
              className="rounded-lg border border-gray-200 bg-white p-3 text-xs"
            >
              <div className="flex items-center gap-2 mb-1">
                <span>{nodeInfo.icon}</span>
                <span className={`font-medium ${nodeInfo.color}`}>
                  {nodeInfo.label}
                </span>
                {step.timestamp && (
                  <span className="ml-auto text-gray-400">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </div>
              <p className="text-gray-600 pl-6">
                {formatAction(step.action)}
              </p>
              {step.tokens_used && (
                <p className="text-gray-400 pl-6 mt-0.5">
                  {step.tokens_used} tokens
                </p>
              )}
              {step.confidence !== undefined && (
                <div className="mt-1 pl-6">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 flex-1 rounded-full bg-gray-200">
                      <div
                        className={`h-full rounded-full ${
                          step.confidence > 0.7
                            ? 'bg-green-500'
                            : step.confidence > 0.4
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        }`}
                        style={{ width: `${step.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-gray-500">{(step.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function formatAction(action: string): string {
  return action
    .replace(/_/g, ' ')
    .replace(/^./, (c) => c.toUpperCase());
}
