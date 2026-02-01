"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { ProcessedCallData } from "@/types/analysis";

export default function Ps2AnalysisDetailPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : "";
  const [data, setData] = useState<ProcessedCallData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);

  useEffect(() => {
    if (!id) {
      setLoading(false);
      setError("Missing analysis id");
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    const encoded = encodeURIComponent(id);
    fetch(`/api/ps2-analysis?id=${encoded}`)
      .then((res) => {
        if (!res.ok) throw new Error(res.status === 404 ? "Not found" : res.statusText);
        return res.json();
      })
      .then((json: ProcessedCallData) => {
        if (!cancelled) setData(json);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message ?? "Failed to load");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (!id) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-6 bg-zinc-950">
        <p className="text-zinc-400">Invalid analysis id.</p>
        <Link
          href="/ps2-analysis-results"
          className="mt-4 text-sm hover:underline"
          style={{ color: "#B19EEF" }}
        >
          Back to list
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-zinc-950">
      <header className="w-full border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/ps2-analysis-results"
              className="text-zinc-400 hover:text-zinc-100"
              aria-label="Back to list"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
            </Link>
            <h1 className="text-lg font-semibold text-zinc-100">
              Call analysis
            </h1>
          </div>
          {data && (
            <label className="flex items-center gap-2 text-sm text-zinc-400">
              <input
                type="checkbox"
                checked={showRawJson}
                onChange={(e) => setShowRawJson(e.target.checked)}
                className="rounded border-zinc-600 bg-zinc-800 text-[#B19EEF] focus:ring-[#B19EEF]/50"
              />
              Show raw JSON
            </label>
          )}
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-6">
        {loading && (
          <div className="flex items-center justify-center py-16">
            <p className="text-sm text-zinc-400">
              Loading analysis…
            </p>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {!loading && !error && data && showRawJson && (
          <pre className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 overflow-auto text-xs font-mono text-zinc-200 max-h-[80vh]">
            {JSON.stringify(data, null, 2)}
          </pre>
        )}

        {!loading && !error && data && !showRawJson && (
          <div className="space-y-8">
            {/* Metadata */}
            <section className="rounded-xl border border-zinc-800 bg-zinc-900/95 p-6">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 mb-4">
                Metadata
              </h2>
              <dl className="grid gap-3 sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-zinc-500">Name</dt>
                  <dd className="text-zinc-100">{data.metadata.name}</dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-500">Date</dt>
                  <dd className="text-zinc-100">{data.metadata.date}</dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-500">Issue type</dt>
                  <dd className="text-zinc-100">{data.metadata.issueType}</dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-500">Calling number</dt>
                  <dd className="text-zinc-100">{data.metadata.callingNumber}</dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-500">Call duration</dt>
                  <dd className="text-zinc-100">{data.metadata.callDuration}s</dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-500">Processed at</dt>
                  <dd className="text-zinc-100">{data.metadata.processedAt}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs text-zinc-500">Recording link</dt>
                  <dd>
                    <a
                      href={data.metadata.recordingLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline break-all"
                      style={{ color: "#B19EEF" }}
                    >
                      {data.metadata.recordingLink}
                    </a>
                  </dd>
                </div>
              </dl>
            </section>

            {/* Analysis */}
            <section className="rounded-xl border border-zinc-800 bg-zinc-900/95 p-6">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 mb-4">
                Analysis
              </h2>
              <div className="space-y-4">
                <div>
                  <h3 className="text-xs font-medium text-zinc-500 mb-1">Summary</h3>
                  <p className="text-zinc-100 leading-relaxed">
                    {data.analysis.summary}
                  </p>
                </div>
                <div>
                  <h3 className="text-xs font-medium text-zinc-500 mb-1">Problem faced</h3>
                  <p className="text-zinc-100 leading-relaxed">
                    {data.analysis.problemFaced}
                  </p>
                </div>
                <div>
                  <h3 className="text-xs font-medium text-zinc-500 mb-1">Solution presented</h3>
                  <p className="text-zinc-100 leading-relaxed">
                    {data.analysis.solutionPresented}
                  </p>
                </div>
                <div className="flex flex-wrap gap-4 pt-2">
                  <div className="rounded-lg bg-zinc-800/50 border border-zinc-700 px-3 py-2">
                    <span className="text-xs text-zinc-500">Partner satisfaction</span>
                    <p className="font-medium text-zinc-100">
                      {data.analysis.partnerSatisfactionScore.score} / {data.analysis.partnerSatisfactionScore.maxScore}
                    </p>
                    <p className="text-sm text-zinc-400 mt-1 max-w-xl">
                      {data.analysis.partnerSatisfactionScore.reasoning}
                    </p>
                  </div>
                  <div className="rounded-lg bg-zinc-800/50 border border-zinc-700 px-3 py-2">
                    <span className="text-xs text-zinc-500">Agent sentiment</span>
                    <p className="font-medium text-zinc-100 capitalize">
                      {data.analysis.agentSentiment.overall}
                    </p>
                    <p className="text-xs text-zinc-500">
                      Confidence: {Math.round(data.analysis.agentSentiment.confidence * 100)}%
                    </p>
                    <p className="text-sm text-zinc-400 mt-1 max-w-xl">
                      {data.analysis.agentSentiment.details}
                    </p>
                  </div>
                  <div className="rounded-lg bg-zinc-800/50 border border-zinc-700 px-3 py-2">
                    <span className="text-xs text-zinc-500">Partner sentiment</span>
                    <p className="font-medium text-zinc-100 capitalize">
                      {data.analysis.partnerSentiment.overall}
                    </p>
                    <p className="text-xs text-zinc-500">
                      Confidence: {Math.round(data.analysis.partnerSentiment.confidence * 100)}%
                    </p>
                    <p className="text-sm text-zinc-400 mt-1 max-w-xl">
                      {data.analysis.partnerSentiment.details}
                    </p>
                  </div>
                </div>
              </div>
            </section>

            {/* Transcription */}
            <section className="rounded-xl border border-zinc-800 bg-zinc-900/95 p-6">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 mb-4">
                Transcription
              </h2>
              <div className="grid gap-6 sm:grid-cols-2">
                <div>
                  <h3 className="text-xs font-medium text-zinc-500 mb-2">Agent</h3>
                  <ul className="space-y-2 max-h-64 overflow-y-auto">
                    {data.transcription.agentConversation.map((seg, i) => (
                      <li
                        key={i}
                        className="text-sm text-zinc-300 border-l-2 pl-2"
                        style={{ borderColor: "rgba(177, 158, 239, 0.5)" }}
                      >
                        <span className="text-xs text-zinc-500">
                          {seg.timestamp.toFixed(1)}s
                        </span>{" "}
                        {seg.text}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="text-xs font-medium text-zinc-500 mb-2">Partner</h3>
                  <ul className="space-y-2 max-h-64 overflow-y-auto">
                    {data.transcription.partnerConversation.map((seg, i) => (
                      <li
                        key={i}
                        className="text-sm text-zinc-300 border-l-2 border-amber-500/50 pl-2"
                      >
                        <span className="text-xs text-zinc-500">
                          {seg.timestamp.toFixed(1)}s
                        </span>{" "}
                        {seg.text}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
              <details className="mt-4">
                <summary className="cursor-pointer text-sm font-medium text-zinc-400 hover:text-zinc-100">
                  Full transcript
                </summary>
                <pre className="mt-2 rounded-lg bg-zinc-800 p-4 text-xs font-mono text-zinc-200 whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {data.transcription.fullTranscript}
                </pre>
              </details>
            </section>
          </div>
        )}
      </main>

      <footer className="w-full border-t border-zinc-800 py-4">
        <div className="max-w-4xl mx-auto px-6 flex items-center justify-center">
          <p className="text-xs text-zinc-500">
            Built for Hackathon 2026
          </p>
        </div>
      </footer>
    </div>
  );
}
